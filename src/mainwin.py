from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile
from PySide2.QtWidgets import QMainWindow, QMenu

from glwin import GlWin
from application import App

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

    def glWin(self):
        return self.glWin_;

    def addPainter(self, painter):
        return self.glWin().addPainter()

    def onClose(self, checked:bool):
        self.close()


def create():
    file = QFile('gl2.ui')
    file.open(QFile.ReadOnly)
    loader = QUiLoader()
    loader.registerCustomWidget(GlWin)
    mainwin = MainFrame()
    mainwin.window = loader.load(file, mainwin)
    mainwin.setCentralWidget(mainwin.window)
    file.close()
    mainwin.glWin_ = mainwin.window.findChild(GlWin, "glWin")
    return mainwin
