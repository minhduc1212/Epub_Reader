from PyQt5 import QtWidgets, QtWebEngineWidgets
from ebooklib import epub
import sys
import ebooklib

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, html_content):
        super().__init__()

        self.browser = QtWebEngineWidgets.QWebEngineView()
        self.setCentralWidget(self.browser)

        self.browser.setHtml(html_content)

def open_epub(filepath):
    book = epub.read_epub(filepath)
    html_content = ""
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            html_content += item.get_content().decode('utf-8')
    return html_content

app = QtWidgets.QApplication(sys.argv)

filepath = 'Hứa Tiên Chí.epub'  # replace with your epub file path
html_content = open_epub(filepath)

window = MainWindow(html_content)
window.show()

app.exec_()