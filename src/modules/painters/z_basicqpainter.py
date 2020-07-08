from PySide2.QtCore import Slot,Qt
from PySide2.QtGui import QOpenGLShaderProgram, QOpenGLShader
from PySide2.QtGui import QOpenGLVersionProfile, QOpenGLContext
from PySide2.QtGui import QSurfaceFormat,QFont
from PySide2.QtWidgets import QMessageBox
from painters import Painter
from signals import Signals, DragInfo
from PySide2.QtCore import QPoint, QRect
from geometry import Geometry
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide2.QtGui import QBrush, QPainter,QPen ,QPolygon,QColor
import PySide2.QtCore
from OpenGL import GL
from PySide2.QtWidgets import QApplication


class BasicQPainter(Painter):
    def __init__(self):
        super().__init__()
        self.drawInfo = False
        self.info= ""
        self.drawInfoRect = True
        self.width=0
        self.height=0
        self.colorRect = QColor(100, 100, 255, 255)
        self.colorText = QColor(0, 0, 0, 255)
        self.infoFontName = "Times"
        self.infoFontSize = 10
        self.infoFontType = QFont.Bold
        self.paintDevice =0

    def initializeGL(self):
        paintDevice = QApplication.instance().mainFrame.glWin
        super().initializeGL()
        self.paintDevice = paintDevice
        self.width = paintDevice.vport.width()
        self.height = paintDevice.vport.height()
        self.glf.initializeOpenGLFunctions()





    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass
    def paintGL(self):
        if not self.drawInfo:
            return
        painter = QPainter(self.paintDevice)
        self.glf.glDisable(GL.GL_CULL_FACE)
        font= QFont(self.infoFontName, self.infoFontSize, self.infoFontType)
        painter.setFont(font)
        pen=QPen(self.colorText, 1)
        painter.setPen(pen)
        brush=QBrush(self.colorRect)
        painter.setBrush(brush)

        rect = QRect(5, 5, self.width-10, 20)

        if self.drawInfoRect:
            painter.drawRect(rect)
            #painter.fillRect(rect,self.colorRect)
        painter.drawText(rect, Qt.AlignCenter, self.info)
        painter.end()


    def resizeGL(self, w:int, h:int):
        super().resizeGL(w,h)
        self.width=w
        self.height=h

    def updateGL(self):
        super().updateGL()


    def addGeometry(self, geometry:Geometry):
        self.drawInfo = True
        if isinstance(geometry.mesh, om.TriMesh):
            self.info = self.info+ "Tria Mesh"
        else:
            self.info = self.info+ "Poly Mesh"
        self.info = self.info + "; nf = " + str(geometry.mesh.n_faces())+"; "
        #self.requestGLUpdate()

def createPainter():
    return BasicQPainter()


