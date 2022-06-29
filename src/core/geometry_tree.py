from PySide6.QtWidgets import QTreeWidget, QMenu
from PySide6.QtCore import Slot, Signal, QObject, Qt
from PySide6 import QtGui

from .geo_manager import geometry_manager
from .gtree_item import GTreeItem


class GeometryTree(QTreeWidget):
    counter = 0;
    def __init__(self, parent = None):
        super().__init__(parent)
        geometry_manager.geometry_created.connect(self.on_geometry_created)
        self.itemActivated.connect(self.on_item_changed)
        self.ad
 #       self.setContextMenuPolicy(Qt.CustomContextMenu)
#        self.customContextMenuRequested.connect(self.on_context_menu)

    def contextMenuEvent(self, evt: QtGui.QContextMenuEvent) -> None:
        menu = QMenu()
        menu.addActions(self.actions())
        menu.exec()

    @Slot()
    def on_context_menu(self):
        pass

    @Slot()
    def on_geometry_created(self, new_geometry):
        self.counter += 1
        root = GTreeItem(name = "Imported: " + str(self.counter), geometry=new_geometry)
        self.addTopLevelItem(root)
        self.create_subtree(root, new_geometry)

    def create_subtree(self, parent:GTreeItem, geometry: list):
        for g in geometry:
            chld = GTreeItem(g.name, g)
            parent.addChild(chld)
            self.create_subtree(chld, g.sub_geometry)


    @Slot()
    def on_item_changed(self, item: GTreeItem):
        geometry_manager.select_geometry([item.geometry])