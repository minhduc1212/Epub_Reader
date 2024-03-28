import sys
from PyQt5.QtWidgets import QApplication
from epubviewer_ui import EpubViewerUI
from PyQt5.QtWidgets import QFileDialog
from ebooklib import epub
import ebooklib
import base64
import concurrent.futures

class EpubViewer:
    def __init__(self):
        self.ui = EpubViewerUI()
        self.ui.browse_action.triggered.connect(self.browse_epub)
        self.ui.font_size_spinbox.valueChanged.connect(self.change_font_size)
        self.ui.margin_spinbox.valueChanged.connect(self.change_margin)

    def browse_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(self.ui, "Open EPUB File", "", "EPUB Files (*.epub)")
        if file_path:
            self.load_epub(file_path)

    def load_epub(self, file_path):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.load_epub_content, file_path)
            content = future.result()
        
        self.ui.text_browser.setHtml(content)
    
    def load_epub_content(self, file_path):
        book = epub.read_epub(file_path)
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
        
        return content
    
    def change_font_size(self, value):
        font_size = f"{value}px"
        self.ui.text_browser.setStyleSheet(f"font-size: {font_size};")

    def change_margin(self, value):
        margin = f"{value}px"
        self.ui.text_browser.setStyleSheet(f"margin: {margin};")

def main():
    app = QApplication(sys.argv)
    viewer = EpubViewer()
    viewer.ui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
