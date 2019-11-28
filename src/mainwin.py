from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile
from PySide2.QtWidgets import QMainWindow

from glwin import GlWin

class MainFrame(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)

    def glWin(self):
        return self.glWin_;

    def addPainter(self, painter):
        return self.glWin().addPainter()


def create():
    file = QFile('gl2.ui')
    file.open(QFile.ReadOnly)
    loader = QUiLoader()
    loader.registerCustomWidget(GlWin)
    mainwin = MainFrame()
    mainwin.window = loader.load(file, mainwin)
    file.close()
    mainwin.glWin_ = mainwin.window.findChild(GlWin, "glWin")
    return mainwin
