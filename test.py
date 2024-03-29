import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QToolBar, QAction, QTextBrowser
from PyQt5.QtWebEngineWidgets import QWebEngineView
from ebooklib import epub
import ebooklib
import base64
from bs4 import BeautifulSoup

class EpubViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.last_scroll_position = 0
        self.is_scrolling_up = False

        self.prev_action = QAction("Previous Chapter", self)
        self.prev_action.triggered.connect(self.load_previous_item)

        self.next_action = QAction("Next Chapter", self)
        self.next_action.triggered.connect(self.load_next_item)

        self.toolbar = QToolBar("Chapter navigation")
        self.toolbar.addAction(self.prev_action)
        self.toolbar.addAction(self.next_action)

        self.addToolBar(self.toolbar)

        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 

        self.web_view = QTextBrowser()

        self.browse_action = QAction("Browse EPUB", self)
        self.browse_action.triggered.connect(self.browse_epub)
        
        toolbar = QToolBar()
        toolbar.addAction(self.browse_action)
        self.addToolBar(toolbar)
        
        layout = QVBoxLayout()
        layout.addWidget(self.web_view)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.file_path = ""
    
    def browse_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EPUB File", "", "EPUB Files (*.epub)")
        if file_path:
            self.file_path = file_path
            self.load_epub_content()

    def load_previous_item(self):
        if self.current_item_index <= 0:
            return

        self.current_item_index -= 2
        self.load_next_item()

    def load_epub_content(self):
        book = epub.read_epub(self.file_path)
        self.items = list(book.get_items())
        self.current_item_index = 0
        self.load_next_item()

    def load_next_item(self):
        if self.current_item_index >= len(self.items):
            return
        while self.current_item_index < len(self.items):
            item = self.items[self.current_item_index]
            self.current_item_index += 1

            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                print("Loading item", item.get_name())
                html_content = item.get_content().decode('utf-8')
                soup = BeautifulSoup(html_content, "html.parser")
                img_tags = soup.find_all("img")
                image_tags = soup.find_all("image")

                for img_tag in img_tags:
                    for item in self.items:
                        if item.get_type() == ebooklib.ITEM_IMAGE:
                            if img_tag["src"] in item.get_name():
                                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                                img_tag["src"] = f"data:image/lpg;base64,{img_data}"
                                break

                for image_tag in image_tags:
                    for item in self.items:
                        if item.get_type() == ebooklib.ITEM_IMAGE:
                            if image_tag["xlink:href"] in item.get_name():
                                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                                image_tag["xlink:href"] = f"data:image/jpg;base64,{img_data}"
                                break

                # Display XHTML or HTML content
                self.web_view.setHtml(str(soup))
                return str(soup)

def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()