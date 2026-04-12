import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from src.reader_window import ReaderWindow


def main():
    # Enable high DPI
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("NightReader")
    app.setOrganizationName("NightReader")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = ReaderWindow()
    window.show()

    # Open file from command line argument if provided
    if len(sys.argv) > 1 and sys.argv[1].endswith(".epub"):
        window.load_epub(sys.argv[1])

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()