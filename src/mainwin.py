from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile
from PySide6.QtWidgets import QMainWindow, QMenu
import os

from glwin import GlWin
from application import App
from geometry_tree import GeometryTree

class MainFrame(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)

        app = App.instance()
        mb = self.menuBar()
        f = mb.addMenu("&File")
        imp = f.addAction("&Import geometry")
        imp.triggered.connect(app.onImportGeometry)
        exp = f.addAction("&Export selected geometry")
        exp.triggered.connect(app.onExportGeometry)

        f.addSeparator()

        close = f.addAction("Close")
        close.triggered.connect(self.onClose)

        e = mb.addMenu("E&dit")
        e.addAction("Prefs")

        self._menuTools = mb.addMenu("Tools")

    @property
    def menuTools(self):
        return self._menuTools

    @property
    def glWin(self):
        return self.glWin_;

    def addPainter(self, painter):
        return self.glWin.addPainter(painter)

    def onClose(self, checked:bool):
        self.close()


def create():
    prefix = os.path.dirname(os.path.realpath(__file__))
    file = QFile(os.path.join(prefix,'gl2.ui'))
    file.open(QFile.ReadOnly)
    loader = QUiLoader()
    loader.registerCustomWidget(GlWin)
    loader.registerCustomWidget(GeometryTree)
    mainwin = MainFrame()
    mainwin.window = loader.load(file) #, mainwin)
    mainwin.setCentralWidget(mainwin.window)
    file.close()
    mainwin.glWin_ = mainwin.window.findChild(GlWin, "glWin")
    mainwin.gTree_ = mainwin.window.findChild(GeometryTree, "geometryTree")
    return mainwin
