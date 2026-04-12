"""
epub_parser.py
Parses an EPUB file: spine order, TOC, per-chapter HTML with base64-embedded images.
Images are embedded verbatim (no recompression) to preserve original quality.
"""

import base64
import posixpath
import re
from typing import List, Dict, Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, Tag


class ChapterInfo:
    """Metadata for a single spine item."""

    def __init__(self, index: int, item: epub.EpubItem, title: str = ""):
        self.index = index
        self.item = item
        self.title = title or f"Chapter {index + 1}"

    def __repr__(self):
        return f"<ChapterInfo {self.index}: {self.title}>"


class TOCEntry:
    """One entry in the table of contents."""

    def __init__(self, title: str, href: str, spine_index: int, depth: int = 0,
                 fragment: Optional[str] = None):
        self.title = title
        self.href = href
        self.spine_index = spine_index
        self.depth = depth
        self.fragment = fragment  # anchor within the spine item

    def __repr__(self):
        return f"<TOCEntry depth={self.depth} '{self.title}' -> {self.spine_index}>"


class EPUBParser:
    """
    Parses an EPUB file and provides chapter-by-chapter HTML access.
    Images are base64-embedded for portability, preserving original bytes.
    """

    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.book: epub.EpubBook = epub.read_epub(epub_path)
        self._spine_items: List[epub.EpubItem] = self._build_spine()
        self._toc_entries: List[TOCEntry] = self._build_toc()
        self._image_cache: Dict[str, str] = {}  # resolved_href -> data URI

    # ------------------------------------------------------------------ #
    #  Spine                                                               #
    # ------------------------------------------------------------------ #

    def _build_spine(self) -> List[epub.EpubItem]:
        items = []
        for item_id, _linear in self.book.spine:
            item = self.book.get_item_with_id(item_id)
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                items.append(item)
        return items

    @property
    def chapter_count(self) -> int:
        return len(self._spine_items)

    def get_chapter_item(self, index: int) -> Optional[epub.EpubItem]:
        if 0 <= index < len(self._spine_items):
            return self._spine_items[index]
        return None

    # ------------------------------------------------------------------ #
    #  TOC                                                                 #
    # ------------------------------------------------------------------ #

    def _build_toc(self) -> List[TOCEntry]:
        entries: List[TOCEntry] = []
        self._flatten_toc(self.book.toc, entries, depth=0)

        # If TOC is empty, synthesise one entry per spine item
        if not entries:
            for i, item in enumerate(self._spine_items):
                entries.append(TOCEntry(
                    title=self._title_from_item(item, i),
                    href=item.get_name(),
                    spine_index=i,
                    depth=0,
                ))
        return entries

    def _flatten_toc(self, items, result: list, depth: int):
        for entry in items:
            if isinstance(entry, epub.Link):
                spine_idx, frag = self._href_to_spine(entry.href)
                result.append(TOCEntry(
                    title=(entry.title or "").strip() or "Untitled",
                    href=entry.href,
                    spine_index=spine_idx,
                    depth=depth,
                    fragment=frag,
                ))
            elif isinstance(entry, tuple) and len(entry) == 2:
                section, children = entry
                if hasattr(section, "title"):
                    spine_idx, frag = self._href_to_spine(
                        getattr(section, "href", ""))
                    result.append(TOCEntry(
                        title=(section.title or "").strip() or "Untitled",
                        href=getattr(section, "href", ""),
                        spine_index=spine_idx,
                        depth=depth,
                        fragment=frag,
                    ))
                self._flatten_toc(children, result, depth + 1)

    def _href_to_spine(self, href: str):
        """Return (spine_index, fragment) for a TOC href."""
        if not href:
            return -1, None
        parts = href.split("#", 1)
        base = parts[0]
        frag = parts[1] if len(parts) > 1 else None
        idx = self._find_spine_index_by_href(base)
        return idx, frag

    def _find_spine_index_by_href(self, base_href: str) -> int:
        base_href = base_href.lstrip("/")
        for i, item in enumerate(self._spine_items):
            name = item.get_name()
            if name == base_href:
                return i
            # Match on filename only (some EPUBs use relative paths in TOC)
            if posixpath.basename(name) == posixpath.basename(base_href):
                return i
        return -1

    @property
    def toc_entries(self) -> List[TOCEntry]:
        return self._toc_entries

    def get_chapter_title(self, index: int) -> str:
        """Best-effort title for a spine index."""
        for entry in self._toc_entries:
            if entry.spine_index == index and entry.depth == 0:
                return entry.title
        # Fallback: first entry with that index (any depth)
        for entry in self._toc_entries:
            if entry.spine_index == index:
                return entry.title
        item = self.get_chapter_item(index)
        return self._title_from_item(item, index) if item else f"Chapter {index + 1}"

    @staticmethod
    def _title_from_item(item: epub.EpubItem, index: int) -> str:
        name = posixpath.basename(item.get_name())
        stem = posixpath.splitext(name)[0]
        # Clean up common patterns like "chapter_01", "ch01", etc.
        stem = re.sub(r"[_\-]+", " ", stem).strip()
        return stem if stem else f"Chapter {index + 1}"

    # ------------------------------------------------------------------ #
    #  HTML access                                                         #
    # ------------------------------------------------------------------ #

    def get_chapter_html(self, index: int) -> str:
        """
        Return processed, self-contained HTML for chapter at *index*.
        All images are embedded as data URIs preserving original bytes.
        """
        item = self.get_chapter_item(index)
        if item is None:
            return "<html><body><p>Chapter not found.</p></body></html>"

        raw = item.get_content()
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("latin-1", errors="replace")

        return self._process_html(html, item)

    def _process_html(self, html: str, item: epub.EpubItem) -> str:
        """Embed images, strip conflicting stylesheets, inject reader CSS."""
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        # Embed images
        for tag in soup.find_all(["img", "image"]):
            # Ensure src is a string (BeautifulSoup can return a list for some attributes)
            raw_src = tag.get("src") or tag.get("xlink:href") or tag.get("href") or ""
            src = " ".join(raw_src) if isinstance(raw_src, list) else str(raw_src)
            if src and not src.startswith("data:"):
                data_uri = self._resolve_image(src.strip(), item)
                if data_uri:
                    # Chuyển thẻ <image> của SVG thành <img> để QTextBrowser có thể hiển thị
                    if tag.name == "image":
                        tag.name = "img"
                    
                    tag["src"] = data_uri
                    # Xóa các thuộc tính cũ không tương thích
                    for attr in ["xlink:href", "href"]:
                        if attr in tag.attrs:
                            del tag[attr]

        # Remove external stylesheet links (they'll 404 in QWebEngineView)
        for link in soup.find_all("link", rel=lambda r: bool(r and "stylesheet" in (r if isinstance(r, str) else " ".join(r)))):
            link.decompose()

        # Inject our reader stylesheet into <head>
        head = soup.find("head")
        if not head:
            head = soup.new_tag("head")
            if soup.html:
                soup.html.insert(0, head)

        style_tag = soup.new_tag("style")
        style_tag.string = READER_CSS
        head.append(style_tag)

        return str(soup)

    # ------------------------------------------------------------------ #
    #  Image helpers                                                       #
    # ------------------------------------------------------------------ #

    def _resolve_image(self, src: str, item: epub.EpubItem) -> Optional[str]:
        """Return data URI for an image referenced from *item*."""
        # Build cache key
        resolved = self._resolve_relative(src, item.get_name())
        if resolved in self._image_cache:
            return self._image_cache[resolved]

        img_item = self._find_item_by_name(resolved)
        if img_item is None:
            # Last resort: match by basename
            bname = posixpath.basename(src)
            img_item = self._find_item_by_basename(bname)

        if img_item is None:
            return None

        data = img_item.get_content()  # raw bytes – not recompressed
        b64 = base64.b64encode(data).decode("ascii")
        media_type = img_item.media_type or "image/jpeg"
        uri = f"data:{media_type};base64,{b64}"
        self._image_cache[resolved] = uri
        return uri

    @staticmethod
    def _resolve_relative(src: str, item_name: str) -> str:
        """Resolve *src* relative to the directory of *item_name*."""
        item_dir = posixpath.dirname(item_name)
        joined = posixpath.join(item_dir, src)
        return posixpath.normpath(joined)

    def _find_item_by_name(self, name: str) -> Optional[epub.EpubItem]:
        for item in self.book.get_items():
            if item.get_name() == name:
                return item
        return None

    def _find_item_by_basename(self, bname: str) -> Optional[epub.EpubItem]:
        for item in self.book.get_items():
            if posixpath.basename(item.get_name()) == bname:
                return item
        return None

    # ------------------------------------------------------------------ #
    #  Book metadata                                                       #
    # ------------------------------------------------------------------ #

    @property
    def title(self) -> str:
        titles = self.book.get_metadata("DC", "title")
        if titles:
            return titles[0][0]
        return posixpath.basename(self.epub_path)

    @property
    def author(self) -> str:
        creators = self.book.get_metadata("DC", "creator")
        if creators:
            return creators[0][0]
        return ""


# ------------------------------------------------------------------ #
#  Injected CSS – dark, editorial reading style                       #
# ------------------------------------------------------------------ #

READER_CSS = """
/* ── Reset & base ─────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html {
    background: #12111a;
    color: #ddd5c8;
    font-family: 'Palatino Linotype', 'Palatino', 'Book Antiqua', Georgia, serif;
    font-size: 19px;
    line-height: 1.85;
    -webkit-font-smoothing: antialiased;
}

body {
    background: #12111a;
    color: #ddd5c8;
    max-width: 720px;
    margin: 0 auto;
    padding: 48px 36px 80px;
    min-height: 100vh;
}

/* ── Headings ──────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Palatino Linotype', Georgia, serif;
    font-weight: 600;
    color: #f0e8d5;
    line-height: 1.3;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
    letter-spacing: 0.01em;
}
h1 { font-size: 1.9em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }

/* ── Paragraphs ────────────────────────────────────────────────── */
p {
    margin-bottom: 1.1em;
    text-align: justify;
    hyphens: auto;
}
p + p { text-indent: 1.5em; }

/* ── Links ─────────────────────────────────────────────────────── */
a { color: #b89e7e; text-decoration: none; border-bottom: 1px solid #5a4d3a; }
a:hover { color: #d4be9a; border-bottom-color: #d4be9a; }

/* ── Images – preserve original dimensions, centred ───────────── */
img, svg {
    display: block;
    max-width: 100%;
    height: auto;
    margin: 1.8em auto;
    border-radius: 4px;
}
/* Cover images (often a full-page child of body) */
body > p > img:only-child,
body > div > img:only-child,
body > img:only-child {
    max-width: min(100%, 600px);
    box-shadow: 0 8px 40px rgba(0,0,0,0.55);
    border-radius: 6px;
}

/* ── Block quotes ──────────────────────────────────────────────── */
blockquote {
    border-left: 3px solid #4a3f2f;
    padding: 0.4em 1.2em;
    margin: 1.4em 0;
    color: #a89880;
    font-style: italic;
}

/* ── Tables ────────────────────────────────────────────────────── */
table { border-collapse: collapse; width: 100%; margin: 1.4em 0; }
th, td { border: 1px solid #2e2b22; padding: 0.5em 0.8em; text-align: left; }
th { background: #1c1a14; color: #d4be9a; }

/* ── Lists ─────────────────────────────────────────────────────── */
ul, ol { padding-left: 1.8em; margin-bottom: 1em; }
li { margin-bottom: 0.35em; }

/* ── Misc ──────────────────────────────────────────────────────── */
hr { border: none; border-top: 1px solid #2e2b22; margin: 2em 0; }
em { color: #cfc0a8; }
strong { color: #f0e8d5; font-weight: 600; }
code, pre { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.88em;
            background: #1c1a14; color: #b8d4a8; border-radius: 4px; }
pre { padding: 1em; overflow-x: auto; }
code { padding: 0.15em 0.4em; }

/* ── Scrollbar ─────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #12111a; }
::-webkit-scrollbar-thumb { background: #3a3428; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #5a4e3a; }
"""