import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextBrowser, QVBoxLayout, QWidget, QPushButton, QFileDialog, QSpinBox, QToolBar, QAction
from PyQt5.QtCore import Qt
from ebooklib import epub
import ebooklib
import base64

class EpubViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 
        
        self.text_browser = QTextBrowser()
        
        # Tạo nút browse, nút điều chỉnh cỡ chữ và nút điều chỉnh margin
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
        
        # Thêm các action vào thanh công cụ
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
            self.load_epub()

    def load_epub(self):
        if self.file_path:
            book = epub.read_epub(self.file_path)
            content = ""
            
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content += item.get_content().decode('utf-8')
                elif item.get_type() == ebooklib.ITEM_IMAGE:
                    img_data = base64.b64encode(item.get_content())
                    img_format = book.get_items_of_media_type('image/jpg')  # Get the image format (like 'jpeg', 'png', etc.)
                    img_src = f"data:image/{img_format};base64,{img_data.decode('utf-8')}"
                    img_tag = f'<img src="{img_src}" />'
                    content += img_tag
            
            self.text_browser.setHtml(content)
    
    def change_font_size(self, value):
        font_size = f"{value}px"
        self.text_browser.setStyleSheet(f"font-size: {font_size};")

    
    def change_margin(self, value):
        margin = f"{value}px"
        self.text_browser.setStyleSheet(f"margin: {margin};")

def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
