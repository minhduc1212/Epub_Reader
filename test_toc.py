from bs4 import BeautifulSoup
from ebooklib import epub
import ebooklib


book = epub.read_epub("Đau Ơi Bay Đi.epub")
toc = book.get_items_of_type(ebooklib.ITEM_NAVIGATION)
for item in toc:
    print(item.get_content().decode("utf-8"))
