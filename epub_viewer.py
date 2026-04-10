import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QSpinBox, QToolBar, QAction, QTextBrowser
from PyQt5.QtCore import Qt
from ebooklib import epub
import ebooklib
import base64
from bs4 import BeautifulSoup
from typing import List, Any

class EpubViewer(QMainWindow):
    #giao diện
    def __init__(self):
        super().__init__()

        self.last_scroll_position: int = 0
        self.is_scrolling_up: bool = False
        self.current_item_index: int = 0
        self.items: List[Any] = []
        self.file_path: str = ""

        # Create the actions for the toolbar
        self.prev_action = QAction("Previous Chapter", self)
        self.prev_action.triggered.connect(self.load_previous_item)

        self.next_action = QAction("Next Chapter", self)
        self.next_action.triggered.connect(self.load_next_item)

        # Create a toolbar and add the actions to it
        self.toolbar = QToolBar("Chapter navigation")
        self.toolbar.addAction(self.prev_action)
        self.toolbar.addAction(self.next_action)

        # Add the toolbar to the QMainWindow
        self.addToolBar(self.toolbar)

        # ...

        self.font_size = "16px"
        self.margin = "0px 400px 0px 400px"

        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 

        self.text_browser = QTextBrowser()
        vbar = self.text_browser.verticalScrollBar()
        if vbar:
            vbar.valueChanged.connect(self.check_scroll_position)

        # Create browse button, font size adjustment button and margin adjustment button
        self.browse_action = QAction("Browse EPUB", self)
        self.browse_action.triggered.connect(self.browse_epub)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(0, 100)
        self.font_size_spinbox.setValue(20)
        self.font_size_spinbox.valueChanged.connect(self.change_font_size)

        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 1000)
        self.margin_spinbox.setValue(350)
        self.margin_spinbox.valueChanged.connect(self.change_margin)

        self.apply_styles()
        
        # Add actions to toolbar
        toolbar = QToolBar()
        toolbar.addAction(self.browse_action)
        toolbar.addWidget(self.font_size_spinbox)
        toolbar.addWidget(self.margin_spinbox)
        self.addToolBar(toolbar)
        
        #Text Area
        layout = QVBoxLayout()
        layout.addWidget(self.text_browser)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.text_browser.setStyleSheet("border: none;")

    
    def browse_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EPUB File", "", "EPUB Files (*.epub)")
        if file_path:
            self.file_path = file_path
            self.load_epub_content()

    def load_previous_item(self):
        self.current_item_index -= 2
        if self.current_item_index < 0:
            self.current_item_index = 0

        self.load_next_item()

    def load_epub_content(self):
        book = epub.read_epub(self.file_path)
        self.items = list(book.get_items())
        self.current_item_index = 0
        self.load_next_item()

    def load_next_item(self) :
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
                    for img_item in self.items:
                        if img_item.get_type() == ebooklib.ITEM_IMAGE:
                            if img_tag["src"] in img_item.get_name():
                                img_data = base64.b64encode(img_item.get_content()).decode('utf-8')
                                img_tag["src"] = f"data:image/jpeg;base64,{img_data}"
                                break

                for image_tag in image_tags:
                    for img_item in self.items:
                        if img_item.get_type() == ebooklib.ITEM_IMAGE:
                            if image_tag["xlink:href"] in img_item.get_name():
                                img_data = base64.b64encode(img_item.get_content()).decode('utf-8')
                                image_tag["xlink:href"] = f"data:image/jpeg;base64,{img_data}"
                                break

                content = str(soup).replace("xlink:href", "src")
                content = content.replace("image", "img")
                self.text_browser.setHtml(content)
                return content
    
    def apply_styles(self):
        self.text_browser.setStyleSheet(f"QTextBrowser {{ font-size: {self.font_size}; margin: {self.margin}; }}")

    def change_font_size(self, value: int):
        self.font_size = f"{value}px"
        self.apply_styles()

    def change_margin(self, value: int):
        self.margin = f"0px {value}px 0px {value}px"
        self.apply_styles()
    #cuộn chuột
    def check_scroll_position(self, position: int):
        if position == 0 and self.is_scrolling_up:
            self.load_previous_item()
        vbar = self.text_browser.verticalScrollBar()
        if vbar and position == vbar.maximum() and not self.is_scrolling_up:
            self.load_next_item()

        self.is_scrolling_up = self.last_scroll_position > position
        self.last_scroll_position = position
def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()