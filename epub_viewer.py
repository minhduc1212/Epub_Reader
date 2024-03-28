import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QFileDialog, QSpinBox, QToolBar, QAction
from PyQt5.QtCore import Qt
from ebooklib import epub
from PyQt5.QtWebEngineWidgets import QWebEngineView
import ebooklib
import base64
from bs4 import BeautifulSoup

class EpubViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 
        
        self.text_browser = QWebEngineView()
        self.text_browser.page().scrollPositionChanged.connect(self.check_scroll_position)
        
        # Create browse button, font size adjustment button and margin adjustment button
        self.browse_action = QAction("Browse EPUB", self)
        self.browse_action.triggered.connect(self.browse_epub)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(0, 100)
        self.font_size_spinbox.setValue(16)
        self.font_size_spinbox.valueChanged.connect(self.change_font_size)
        
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 100)
        self.margin_spinbox.setValue(10)
        self.margin_spinbox.valueChanged.connect(self.change_margin)
        
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

        
        self.file_path = ""
    
    def browse_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EPUB File", "", "EPUB Files (*.epub)")
        if file_path:
            self.file_path = file_path
            self.load_epub_content()

    def load_epub_content(self):
        book = epub.read_epub(self.file_path)
        self.items = list(book.get_items())
        self.current_item_index = 0
        self.load_next_item()
        

    def load_next_item(self):
        while self.current_item_index < len(self.items):
            item = self.items[self.current_item_index]
            self.current_item_index += 1

            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html_content = item.get_content().decode('utf-8')
                soup = BeautifulSoup(html_content, "html.parser")
                img_tags = soup.find_all("img")
                image_tags = soup.find_all("image")

                for img_tag in img_tags:
                    for item in self.items:
                        if item.get_type() == ebooklib.ITEM_IMAGE:
                            if img_tag["src"] in item.get_name():
                                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                                img_tag["src"] = f"data:image/jpeg;base64,{img_data}"
                                break

                for image_tag in image_tags:
                    for item in self.items:
                        if item.get_type() == ebooklib.ITEM_IMAGE:
                            if image_tag["xlink:href"] in item.get_name():
                                img_data = base64.b64encode(item.get_content()).decode('utf-8')
                                image_tag["xlink:href"] = f"data:image/jpeg;base64,{img_data}"
                                break

                content = str(soup)
                self.text_browser.setHtml(content)
                return
    
    def change_font_size(self, value):
        font_size = f"{value}px"
        self.text_browser.setStyleSheet(f"font-size: {font_size};")

    
    def change_margin(self, value):
        margin = f"{value}px"
        self.text_browser.setStyleSheet(f"margin: {margin};")

    def check_scroll_position(self, position):
        if position.y() == self.text_browser.page().contentsSize().height() - self.text_browser.height():
            self.load_next_item()

def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()