"""
toc_panel.py
Displays the table-of-contents as a tree.
Emits chapter_selected(spine_index) when an entry is clicked.
"""

from typing import List

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget,
                              QTreeWidgetItem, QLabel, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor


class TOCPanel(QWidget):
    chapter_selected = pyqtSignal(int)  # spine_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    # ------------------------------------------------------------------ #
    #  UI setup                                                            #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QFrame()
        header.setObjectName("tocHeader")
        header.setFixedHeight(46)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl = QLabel("Table of Contents")
        lbl.setObjectName("tocHeaderLabel")
        h_layout.addWidget(lbl)
        layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("tocSep")
        layout.addWidget(sep)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setAnimated(True)
        self.tree.setObjectName("tocTree")
        self.tree.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.tree)

        # Empty-state label (shown when no book is open)
        self._empty_label = QLabel("Open a book to see its contents")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("tocEmpty")
        layout.addWidget(self._empty_label)
        self._empty_label.hide()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def load_toc(self, toc_entries):
        """
        Build QTreeWidget from a list of TOCEntry objects.
        Depth info drives parent–child hierarchy.
        """
        from .epub_parser import TOCEntry

        self.tree.clear()
        self._empty_label.hide()
        self.tree.show()

        if not toc_entries:
            self.tree.hide()
            self._empty_label.show()
            return

        # Stack of (depth, QTreeWidgetItem | invisibleRoot)
        root = self.tree.invisibleRootItem()
        stack: list = [(-1, root)]

        for entry in toc_entries:
            d = entry.depth
            # Pop back to a parent that is shallower than current depth
            while len(stack) > 1 and stack[-1][0] >= d:
                stack.pop()

            parent_item = stack[-1][1]
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, entry.spine_index)

            title = entry.title
            item.setText(0, title)

            # Style by depth
            font = QFont()
            if d == 0:
                font.setPointSize(10)
                font.setWeight(QFont.Medium)
            else:
                font.setPointSize(9)

            item.setFont(0, font)
            parent_item.addChild(item)
            stack.append((d, item))

        self.tree.expandAll()

    def highlight_chapter(self, spine_index: int):
        """Select and scroll to the TOC entry matching *spine_index*."""
        root = self.tree.invisibleRootItem()
        if root:
            self._find_and_select(root, spine_index)

    def clear(self):
        self.tree.clear()
        self.tree.hide()
        self._empty_label.show()

    # ------------------------------------------------------------------ #
    #  Internals                                                           #
    # ------------------------------------------------------------------ #

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        spine_index = item.data(0, Qt.ItemDataRole.UserRole)
        if spine_index is not None:
            self.chapter_selected.emit(spine_index)

    def _find_and_select(self, parent: QTreeWidgetItem, spine_index: int) -> bool:
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child is None:
                continue
            if child.data(0, Qt.ItemDataRole.UserRole) == spine_index:
                self.tree.setCurrentItem(child)
                self.tree.scrollToItem(child)
                return True
            if child is not None and self._find_and_select(child, spine_index):
                return True
        return False