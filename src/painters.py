from PySide2.QtGui import QOpenGLFunctions
from PySide2.QtCore import Signal, QObject
from signal import Signals
from commands import Command
from geometry import Geometry

class Painter(Command):
    def __init__(self):
        super().__init__()
        self.glf=0

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

    def requestUpdateGL(self):
        Signals.get().requestUpdateGL.emit(self)


class PainterSignals(QObject):
    __metaclass__ = Painter
    requestUpdateGL = Signal(Painter)
