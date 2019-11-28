from PySide2.QtGui import QOpenGLFunctions

from commands import Command
from geometry import Geometry
from signals import Signals

class Painter(Command):
    def __init__(self):
        super().__init__()
        self.glf=QOpenGLFunctions()

    def updateGL(self):
        Signals.updateGL.emit()

    def paintGL(self):
        pass

    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass

    def initializeGL(self):
        pass

    def resizeGL(self, w:int, h:int):
        pass

    def showGeometry(self, geometry:Geometry):
        pass

    def hideGeometry(self, geometry:Geometry):
        pass

    def addGeometry(self, geometry:Geometry):
        pass
