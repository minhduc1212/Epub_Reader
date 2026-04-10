"""
reader_window.py
Main application window.

Layout:
  ┌─────────────────────────────────────────────────┐
  │  Menu bar                                       │
  ├─────────────────────────────────────────────────┤
  │  Title bar  (book title · author)               │
  ├──────────────┬──────────────────────────────────┤
  │              │                                  │
  │   SIDEBAR    │     ContentView (WebEngine)      │
  │   (TOC tab   │                                  │
  │    + info)   │                                  │
  │              │                                  │
  ├──────────────┴──────────────────────────────────┤
  │  Nav bar: ◀  chapter title  (n/N)  ▶           │
  └─────────────────────────────────────────────────┘

The sidebar can be shown/hidden (Toggle key: T or Ctrl+Shift+S).
TOC entries are in a separate tab; clicking one jumps to that chapter
and switches back to the reader.
"""

import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTabWidget, QFileDialog, QAction, QMenuBar, QMenu, QSplitter,
    QFrame, QSizePolicy, QProgressBar, QShortcut, QStackedWidget,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QSize, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QKeySequence, QFont, QColor, QIcon, QPixmap, QDragEnterEvent, QDropEvent, QResizeEvent
from typing import Optional

from .epub_parser import EPUBParser
from .content_view import ContentView
from .toc_panel import TOCPanel


# ──────────────────────────────────────────────────────────────────────── #
#  Background loader thread                                                 #
# ──────────────────────────────────────────────────────────────────────── #

class EPUBLoader(QThread):
    """Load and parse an EPUB file off the GUI thread."""
    finished = pyqtSignal(object)   # EPUBParser instance
    error = pyqtSignal(str)

    def __init__(self, path: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._path = path

    def run(self):
        try:
            parser = EPUBParser(self._path)
            self.finished.emit(parser)
        except Exception as exc:
            self.error.emit(str(exc))


# ──────────────────────────────────────────────────────────────────────── #
#  Main window                                                              #
# ──────────────────────────────────────────────────────────────────────── #

class ReaderWindow(QMainWindow):

    CONTENT_TAB = 0
    TOC_TAB = 1

    def __init__(self):
        super().__init__()
        self._parser: Optional[EPUBParser] = None
        self._current_chapter: int = 0
        self._loader: Optional[EPUBLoader] = None

        # Khai báo các thuộc tính để Pylance không báo lỗi "attribute not declared in __init__"
        self._title_bar: QFrame
        self._sidebar_btn: QPushButton
        self._book_title_lbl: QLabel
        self._author_lbl: QLabel
        self._sidebar: QTabWidget
        self._toc_panel: TOCPanel
        self._splitter: QSplitter
        self._stack: QStackedWidget
        self._welcome_widget: QLabel
        self._content_view: ContentView
        self._prev_btn: QPushButton
        self._chapter_lbl: QLabel
        self._progress_lbl: QLabel
        self._next_btn: QPushButton
        self._progress: QProgressBar

        self._setup_ui()
        self._setup_menu()
        self._setup_shortcuts()
        self._apply_styles()
        self._show_welcome()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        self.setWindowTitle("Lumi Reader")
        self.setMinimumSize(820, 580)
        self.resize(1120, 780)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top title bar ──────────────────────────────────────────── #
        self._title_bar = self._build_title_bar()
        root.addWidget(self._title_bar)

        # ── Main splitter (sidebar | content) ─────────────────────── #
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setObjectName("mainSplitter")
        root.addWidget(self._splitter, 1)

        # Left: tabbed sidebar (TOC + book info)
        self._sidebar = self._build_sidebar()
        self._splitter.addWidget(self._sidebar)

        # Right: stacked (welcome / content+nav)
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self._stack = QStackedWidget()
        right_layout.addWidget(self._stack, 1)

        # Page 0 – welcome
        self._welcome_widget = QLabel()
        self._welcome_widget.setObjectName("welcomePage")
        self._welcome_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._welcome_widget)

        # Page 1 – reader
        reader_page = QWidget()
        reader_layout = QVBoxLayout(reader_page)
        reader_layout.setContentsMargins(0, 0, 0, 0)
        reader_layout.setSpacing(0)

        self._content_view = ContentView()
        self._content_view.next_chapter_requested.connect(self._go_next)
        self._content_view.prev_chapter_requested.connect(self._go_prev)
        reader_layout.addWidget(self._content_view, 1)

        nav = self._build_nav_bar()
        reader_layout.addWidget(nav)

        self._stack.addWidget(reader_page)

        right_layout.addWidget(right_panel)
        self._splitter.addWidget(right_panel)

        # Splitter proportions: sidebar 240px, rest → content
        self._splitter.setSizes([240, 880])
        self._splitter.setCollapsible(0, True)
        self._splitter.setCollapsible(1, False)

        # ── Loading overlay / progress ─────────────────────────────── #
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setFixedHeight(3)
        self._progress.setObjectName("loadingBar")
        self._progress.hide()

    def _build_title_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("titleBar")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # Sidebar toggle button
        self._sidebar_btn = QPushButton("☰")
        self._sidebar_btn.setObjectName("iconBtn")
        self._sidebar_btn.setFixedSize(32, 32)
        self._sidebar_btn.setToolTip("Toggle sidebar (T)")
        self._sidebar_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self._sidebar_btn)

        layout.addSpacing(8)

        self._book_title_lbl = QLabel("Lumi Reader")
        self._book_title_lbl.setObjectName("bookTitleLabel")
        layout.addWidget(self._book_title_lbl)

        layout.addStretch()

        self._author_lbl = QLabel("")
        self._author_lbl.setObjectName("authorLabel")
        layout.addWidget(self._author_lbl)

        # Open button
        open_btn = QPushButton("Open Book")
        open_btn.setObjectName("openBtn")
        open_btn.clicked.connect(self.open_file_dialog)
        layout.addSpacing(12)
        layout.addWidget(open_btn)

        return bar

    def _build_sidebar(self) -> QTabWidget:
        tabs = QTabWidget()
        tabs.setObjectName("sidebarTabs")
        tabs.setFixedWidth(240)
        tabs.setTabPosition(QTabWidget.North)

        # TOC tab
        self._toc_panel = TOCPanel()
        self._toc_panel.chapter_selected.connect(self._on_toc_selected)
        tabs.addTab(self._toc_panel, "Contents")

        return tabs

    def _build_nav_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("navBar")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setObjectName("navArrow")
        self._prev_btn.setFixedSize(38, 38)
        self._prev_btn.setToolTip("Previous chapter  (←)")
        self._prev_btn.clicked.connect(self._go_prev)
        self._prev_btn.setEnabled(False)

        self._chapter_lbl = QLabel("")
        self._chapter_lbl.setObjectName("chapterLbl")
        self._chapter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._progress_lbl = QLabel("")
        self._progress_lbl.setObjectName("progressLbl")
        self._progress_lbl.setAlignment(
            Qt.AlignmentFlag(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        )
        self._progress_lbl.setFixedWidth(64)

        self._next_btn = QPushButton("▶")
        self._next_btn.setObjectName("navArrow")
        self._next_btn.setFixedSize(38, 38)
        self._next_btn.setToolTip("Next chapter  (→)")
        self._next_btn.clicked.connect(self._go_next)
        self._next_btn.setEnabled(False)

        layout.addWidget(self._prev_btn)
        layout.addWidget(self._chapter_lbl, 1)
        layout.addWidget(self._progress_lbl)
        layout.addWidget(self._next_btn)

        return bar

    # ------------------------------------------------------------------ #
    #  Menu & shortcuts                                                    #
    # ------------------------------------------------------------------ #

    def _setup_menu(self):
        mb = self.menuBar()
        if mb is None:
            return
        mb.setObjectName("mainMenu")

        # File
        file_menu = mb.addMenu("File")
        open_act = QAction("Open EPUB…", self)
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self.open_file_dialog)
        if file_menu: file_menu.addAction(open_act)
        if file_menu: file_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut(QKeySequence.Quit)
        quit_act.triggered.connect(self._close_app)
        if file_menu: file_menu.addAction(quit_act)

        # View
        view_menu = mb.addMenu("View")
        toggle_sidebar_act = QAction("Toggle Sidebar", self)
        toggle_sidebar_act.setShortcut("Ctrl+Shift+S")
        toggle_sidebar_act.triggered.connect(self._toggle_sidebar)
        if view_menu: view_menu.addAction(toggle_sidebar_act)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("T"), self, self._toggle_sidebar)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._go_next)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._go_prev)

    def _close_app(self) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    #  Welcome screen                                                      #
    # ------------------------------------------------------------------ #

    def _show_welcome(self):
        self._welcome_widget.setText(
            "<div style='text-align:center; color:#4a4460;'>"
            "<div style='font-size:52px; margin-bottom:18px;'>📚</div>"
            "<div style='font-size:20px; font-weight:500; color:#6e6488; margin-bottom:8px;'>Lumi Reader</div>"
            "<div style='font-size:13px; color:#3e3858;'>File → Open EPUB  or  drag &amp; drop</div>"
            "</div>"
        )
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------ #
    #  File opening                                                        #
    # ------------------------------------------------------------------ #

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open EPUB", "", "EPUB Files (*.epub);;All Files (*)"
        )
        if path:
            self.load_epub(path)

    def load_epub(self, path: str):
        if not os.path.isfile(path):
            return
        self._show_loading(True)
        self._loader = EPUBLoader(path, self)
        self._loader.finished.connect(self._on_epub_loaded)
        self._loader.error.connect(self._on_epub_error)
        self._loader.start()

    def _show_loading(self, show: bool):
        self._progress.setVisible(show)
        if show:
            self._progress.setGeometry(0, 0, self.width(), 3)

    @pyqtSlot(object)
    def _on_epub_loaded(self, parser: EPUBParser):
        self._show_loading(False)
        self._parser = parser
        self._current_chapter = 0

        # Update title bar
        self._book_title_lbl.setText(parser.title)
        self._author_lbl.setText(parser.author)
        self.setWindowTitle(f"{parser.title} — Lumi Reader")

        # Load TOC
        self._toc_panel.load_toc(parser.toc_entries)

        # Show reader
        self._stack.setCurrentIndex(1)

        # Load first chapter
        self._load_chapter(0)

    @pyqtSlot(str)
    def _on_epub_error(self, msg: str):
        self._show_loading(False)
        self._welcome_widget.setText(
            f"<div style='text-align:center; color:#c07070; padding:24px;'>"
            f"<div style='font-size:28px;'>⚠️</div>"
            f"<div style='margin-top:12px; font-size:14px;'>Failed to open book</div>"
            f"<div style='margin-top:8px; font-size:12px; color:#805050;'>{msg}</div>"
            f"</div>"
        )
        self._stack.setCurrentIndex(0)

    # ------------------------------------------------------------------ #
    #  Chapter navigation                                                  #
    # ------------------------------------------------------------------ #

    def _load_chapter(self, index: int):
        if not self._parser:
            return
        count = self._parser.chapter_count
        index = max(0, min(index, count - 1))
        self._current_chapter = index

        html = self._parser.get_chapter_html(index)
        self._content_view.load_chapter_html(html)
        self._toc_panel.highlight_chapter(index)

        title = self._parser.get_chapter_title(index)
        self._chapter_lbl.setText(title)
        self._progress_lbl.setText(f"{index + 1} / {count}")

        self._prev_btn.setEnabled(index > 0)
        self._next_btn.setEnabled(index < count - 1)

    @pyqtSlot()
    def _go_next(self):
        if self._parser and self._current_chapter < self._parser.chapter_count - 1:
            self._load_chapter(self._current_chapter + 1)

    @pyqtSlot()
    def _go_prev(self):
        if self._parser and self._current_chapter > 0:
            self._load_chapter(self._current_chapter - 1)

    @pyqtSlot(int)
    def _on_toc_selected(self, spine_index: int):
        """TOC entry clicked → load chapter and show reading tab."""
        self._load_chapter(spine_index)
        # Sidebar stays visible; content is already in view

    # ------------------------------------------------------------------ #
    #  Sidebar                                                             #
    # ------------------------------------------------------------------ #

    def _toggle_sidebar(self):
        sidebar = self._sidebar
        if sidebar.isVisible():
            sidebar.hide()
            self._splitter.setSizes([0, self.width()])
        else:
            sidebar.show()
            self._splitter.setSizes([240, self.width() - 240])

    # ------------------------------------------------------------------ #
    #  Drag-and-drop                                                       #
    # ------------------------------------------------------------------ #

    def dragEnterEvent(self, event: QDragEnterEvent):
        mime_data = event.mimeData()
        if mime_data is None:
            return
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls and urls[0].toLocalFile().lower().endswith(".epub"):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        mime_data = event.mimeData()
        if mime_data is None:
            return
        urls = mime_data.urls()
        if urls:
            self.load_epub(urls[0].toLocalFile())

    # ------------------------------------------------------------------ #
    #  Resize (keep loading bar full-width)                               #
    # ------------------------------------------------------------------ #

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._progress.setGeometry(0, 0, self.width(), 3)

    # ------------------------------------------------------------------ #
    #  Styles                                                              #
    # ------------------------------------------------------------------ #

    def _apply_styles(self):
        self.setAcceptDrops(True)
        self.setStyleSheet(APP_STYLESHEET)


# ─────────────────────────────────────────────────────────────────────── #
#  Application stylesheet                                                   #
# ─────────────────────────────────────────────────────────────────────── #

APP_STYLESHEET = """
/* ── Global ─────────────────────────────────────────────────────── */
* {
    font-family: 'Segoe UI', 'SF Pro Text', 'Helvetica Neue', sans-serif;
    outline: none;
}
QMainWindow, QWidget { background: #12111a; color: #ccc4b8; }

/* ── Menu bar ────────────────────────────────────────────────────── */
QMenuBar {
    background: #0e0d15;
    color: #8a8295;
    border-bottom: 1px solid #1e1c2a;
    padding: 2px 4px;
    font-size: 12px;
}
QMenuBar::item:selected { background: #1e1c2a; color: #ccc4b8; border-radius: 4px; }
QMenu {
    background: #1a1825;
    color: #ccc4b8;
    border: 1px solid #2a2838;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 20px 6px 12px; border-radius: 4px; }
QMenu::item:selected { background: #2a2838; }
QMenu::separator { height: 1px; background: #2a2838; margin: 4px 8px; }

/* ── Title bar ───────────────────────────────────────────────────── */
#titleBar {
    background: #0e0d15;
    border-bottom: 1px solid #1e1c2a;
}
#bookTitleLabel {
    font-size: 14px;
    font-weight: 600;
    color: #e8dfd0;
    letter-spacing: 0.02em;
}
#authorLabel {
    font-size: 12px;
    color: #5a5468;
}
#iconBtn {
    background: transparent;
    color: #6a6278;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    padding: 0;
}
#iconBtn:hover { background: #1e1c2a; color: #ccc4b8; }

#openBtn {
    background: #2a2040;
    color: #c8b8e8;
    border: 1px solid #3a2e5a;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 500;
}
#openBtn:hover { background: #342850; border-color: #5a4888; }
#openBtn:pressed { background: #1e1630; }

/* ── Sidebar tabs ────────────────────────────────────────────────── */
#sidebarTabs {
    background: #0e0d15;
    border-right: 1px solid #1e1c2a;
}
#sidebarTabs QTabBar::tab {
    background: transparent;
    color: #5a5468;
    padding: 8px 14px;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.04em;
    border: none;
    border-bottom: 2px solid transparent;
}
#sidebarTabs QTabBar::tab:selected {
    color: #c8b8e8;
    border-bottom: 2px solid #7a5eb8;
}
#sidebarTabs QTabBar::tab:hover:!selected {
    color: #9a90b0;
    background: #14121e;
}
QTabWidget::pane { border: none; background: #0e0d15; }

/* ── TOC panel ───────────────────────────────────────────────────── */
#tocHeader { background: #0e0d15; }
#tocHeaderLabel {
    font-size: 11px;
    font-weight: 600;
    color: #4a4460;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
#tocSep { color: #1a1828; }
#tocTree {
    background: #0e0d15;
    color: #9a90a8;
    border: none;
    font-size: 13px;
    padding: 4px 0;
}
#tocTree::item {
    padding: 5px 12px;
    border-radius: 0;
}
#tocTree::item:hover {
    background: #14121e;
    color: #ccc4b8;
}
#tocTree::item:selected {
    background: #1c1830;
    color: #c8b8e8;
    border-left: 3px solid #7a5eb8;
}
QTreeWidget::branch { background: #0e0d15; }
#tocEmpty {
    color: #3a3450;
    font-size: 12px;
    padding: 24px;
}

/* ── Splitter ────────────────────────────────────────────────────── */
QSplitter::handle { background: #1e1c2a; }
QSplitter::handle:hover { background: #2e2a3e; }

/* ── Right panel / reader page ───────────────────────────────────── */
#rightPanel { background: #12111a; }
#welcomePage {
    background: #12111a;
    font-size: 15px;
}

/* ── Nav bar ─────────────────────────────────────────────────────── */
#navBar {
    background: #0e0d15;
    border-top: 1px solid #1e1c2a;
}
#navArrow {
    background: #1a1828;
    color: #7a7090;
    border: 1px solid #2a2838;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
}
#navArrow:hover { background: #24213a; color: #c8b8e8; border-color: #4a3878; }
#navArrow:pressed { background: #141224; }
#navArrow:disabled { color: #2a2838; background: #0e0d15; border-color: #1a1828; }
#chapterLbl {
    font-size: 13px;
    color: #7a7090;
    letter-spacing: 0.01em;
}
#progressLbl {
    font-size: 11px;
    color: #4a4460;
}

/* ── Loading bar ─────────────────────────────────────────────────── */
#loadingBar {
    background: #1a1828;
    border: none;
    border-radius: 0;
}
#loadingBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7a5eb8, stop:1 #a87ed8);
    border-radius: 0;
}

/* ── Scrollbars ──────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0e0d15;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2a2838;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #3a3450; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #0e0d15;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #2a2838;
    border-radius: 3px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""