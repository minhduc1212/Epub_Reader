from PyQt5.QtWidgets import QMainWindow, QTextBrowser, QVBoxLayout, QWidget, QSpinBox, QToolBar, QAction, QFileDialog

class EpubViewerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Viewer")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: white;") 
        
        self.text_browser = QTextBrowser()
        
        # Tạo nút browse, nút điều chỉnh cỡ chữ và nút điều chỉnh margin
        self.browse_action = QAction("Browse EPUB", self)
        
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(0, 100)
        self.font_size_spinbox.setValue(16)
        
        self.margin_spinbox = QSpinBox()
        self.margin_spinbox.setRange(0, 100)
        self.margin_spinbox.setValue(10)
        
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
