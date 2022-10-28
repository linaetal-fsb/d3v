from PySide6.QtGui import QOpenGLFunctions
from PySide6.QtCore import Slot, Signal, QObject
from PySide6.QtWidgets import QApplication

import uuid

from commands import Command
from core import Geometry
from signals import Signals

class Painter(Command, QObject):
    def __init__(self):
        super().__init__()
        self.glf=0
        self._guid = uuid.uuid4()

    @property
    def guid(self):
        return self._guid

    @Slot()
    def onUpdateGL(self):
        Signals.get().updateGL.disconnect(self.onUpdateGL)
        self.updateGL()

    def updateGL(self):
        pass

    def paintGL(self):
        pass

    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass

    def initializeGL(self):
        self.glf = QOpenGLFunctions()
        pass

    def resizeGL(self, w:int, h:int):
        pass

    def showGeometry(self, geometry:Geometry):
        pass

    def hideGeometry(self, geometry:Geometry):
        pass

    def addGeometry(self, geometry:Geometry):
        pass

    def requestGLUpdate(self):
        Signals.get().updateGL.connect(self.onUpdateGL)
        app = QApplication.instance()
        app.mainFrame.glWin.update()



