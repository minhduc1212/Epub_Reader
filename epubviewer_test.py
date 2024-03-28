import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QSpinBox, QToolBar, QAction
from PyQt5.QtCore import QThread, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from bs4 import BeautifulSoup
from ebooklib import epub
import ebooklib
import base64

class LoadEpubThread(QThread):
    content_loaded = pyqtSignal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        content = self.load_epub_content()
        self.content_loaded.emit(content)

    def load_epub_content(self):
        book = epub.read_epub(self.file_path)
        all_content = ""
        img_tags = []
        image_tags = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html_content = item.get_content().decode('utf-8')
                all_content += html_content
                
        soup = BeautifulSoup(all_content, "html.parser")
        img_tags.extend(soup.find_all("img"))
        image_tags.extend(soup.find_all("image"))
        
        for img_tag in img_tags:
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    if img_tag["src"] in item.get_name():
                        img_data = base64.b64encode(item.get_content()).decode('utf-8')
                        img_tag["src"] = f"data:image/jpeg;base64,{img_data}"
                        break

        for image_tag in image_tags:
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_IMAGE:
                    if image_tag["xlink:href"] in item.get_name():
                        img_data = base64.b64encode(item.get_content()).decode('utf-8')
                        image_tag["xlink:href"] = f"data:image/jpeg;base64,{img_data}"
                        break

        content = str(soup)
        return content

class EpubViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 
        
        self.web_view = QWebEngineView()
        
        self.browse_action = QAction("Browse EPUB", self)
        self.browse_action.triggered.connect(self.browse_epub)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(0, 100)
        self.font_size_spinbox.setValue(16)
        self.font_size_spinbox.valueChanged.connect(self.change_font_size)
        
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 700)
        self.margin_spinbox.setValue(300)
        self.margin_spinbox.valueChanged.connect(self.change_margin)
        
        toolbar = QToolBar()
        toolbar.addAction(self.browse_action)
        toolbar.addWidget(self.font_size_spinbox)
        toolbar.addWidget(self.margin_spinbox)
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
            self.load_epub_content_thread()

    def load_epub_content_thread(self):
        self.load_thread = LoadEpubThread(self.file_path)
        self.load_thread.content_loaded.connect(self.update_text_browser)
        self.load_thread.start()

    def update_text_browser(self, content):
        self.web_view.setHtml(content)
    
    def change_font_size(self, value):
        font_size = f"{value}px"
        self.web_view.setStyleSheet(f"font-size: {font_size};")

    def change_margin(self, value):
        margin = f"{value}px"
        self.web_view.setStyleSheet(f"margin: {margin};")

def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()