from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt
from PySide6.QtWidgets import QMainWindow, QMenu, QStatusBar, QLabel, QProgressBar, QSpacerItem, QToolBar, QStyle
from PySide6.QtGui import QIcon
import os

from glwin import GlWin
from application import App
from core import GeometryTree, geometry_manager

class MainFrame(QMainWindow):
    def __init__(self, parent = None):
        super().__init__(parent)

        if not QIcon.themeName():
            QIcon.setThemeName("Oxygen")
        app = App.instance()
        style = app.style()

        mb = self.menuBar()
        tbar_file = QToolBar()
        tbar_file.setToolButtonStyle(Qt.ToolButtonIconOnly)

        f = mb.addMenu("&File")
        imp = f.addAction(style.standardIcon(QStyle.SP_DialogOpenButton), "&Import geometry")
        imp.triggered.connect(app.onImportGeometry)
        exp = f.addAction(style.standardIcon(QStyle.SP_DialogSaveButton), "&Export selected geometry")
        exp.triggered.connect(app.onExportGeometry)
        tbar_file.addAction(imp)
        tbar_file.addAction(exp)
        self.addToolBar(tbar_file)
        f.addSeparator()

        close = f.addAction("Close")
        close.triggered.connect(self.onClose)

        e = mb.addMenu("E&dit")
        tbar_e = QToolBar()
        prefs = e.addAction(style.standardIcon(QStyle.SP_FileDialogStart), "Prefs")
        tbar_e.addAction(prefs)
        self.addToolBar(tbar_e)

        self._menuTools = mb.addMenu("Tools")
        sbar = QStatusBar()
        self._coords = QLabel("x:0 y:0 z:0 ")

        self._progress = QProgressBar()
#        self._progress.setMaximum(100)
#        self._progress.setValue(35)
        sbar.addWidget(self._progress)
        sbar.addWidget(self._coords)
        self.setStatusBar(sbar)


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
