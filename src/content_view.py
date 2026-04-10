"""
content_view.py
A QTextBrowser subclass that:
  - Renders one EPUB chapter at a time.
  - Detects scroll position via verticalScrollBar().valueChanged.
  - Emits next/prev chapter signals when the user wheels past the
    top or bottom of the content (works for short pages too).
"""

from PyQt5.QtWidgets import QTextBrowser, QWidget
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QWheelEvent
from typing import Optional
import time


class ContentView(QTextBrowser):
    next_chapter_requested = pyqtSignal()
    prev_chapter_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setStyleSheet("background-color: transparent; border: none;")

        # Các biến trạng thái để theo dõi vị trí cuộn chuột
        self.last_scroll_position = 0
        self.is_scrolling_up = False
        
        # Thay thế cờ _is_loading bằng thời gian (debounce) để tránh bị khóa vĩnh viễn
        self._last_nav_time = 0.0

        # Kết nối sự kiện kéo thanh cuộn
        vbar = self.verticalScrollBar()
        if vbar:
            vbar.valueChanged.connect(self.check_scroll_position)

    def load_chapter_html(self, html: str):
        """Nạp nội dung HTML."""
        self.setHtml(html)
        
        # Reset lại trạng thái cuộn chuột sau khi tải nội dung mới
        self.last_scroll_position = 0
        self.is_scrolling_up = False
        self._last_nav_time = time.time()

    def check_scroll_position(self, position: int):
        """Xử lý khi người dùng kéo thanh cuộn."""
        now = time.time()

        self.is_scrolling_up = self.last_scroll_position > position
        self.last_scroll_position = position

        # Nếu đang trong thời gian chờ thì bỏ qua kích hoạt chuyển chương
        if now - self._last_nav_time < 0.5:
            return

        if position == 0 and self.is_scrolling_up:
            self._last_nav_time = now
            self.prev_chapter_requested.emit()
        vbar = self.verticalScrollBar()
        if vbar and position == vbar.maximum() and not self.is_scrolling_up:
            self._last_nav_time = now
            self.next_chapter_requested.emit()

    def wheelEvent(self, event: QWheelEvent):
        """Xử lý cuộn cho các chương quá ngắn (thanh cuộn không được kích hoạt)."""
        now = time.time()

        scrollbar = self.verticalScrollBar()
        if not scrollbar:
            super().wheelEvent(event)
            return

        dy = event.angleDelta().y()
        
        # Nếu cuộn lên
        if dy > 0:
            if scrollbar.value() == scrollbar.minimum():
                if now - self._last_nav_time > 0.5:
                    self._last_nav_time = now
                    self.prev_chapter_requested.emit()
                return
        # Nếu cuộn xuống
        elif dy < 0:
            if scrollbar.value() == scrollbar.maximum():
                if now - self._last_nav_time > 0.5:
                    self._last_nav_time = now
                    self.next_chapter_requested.emit()
                return

        # Giữ hành vi cuộn mặc định của QTextBrowser nếu chưa kịch trần
        super().wheelEvent(event)