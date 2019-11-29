from PySide2.QtCore import QObject, QPoint, QPointF, QSize, QRect, Signal, Slot
from PySide2.QtGui import QMatrix4x4, QVector3D, QVector4D

from geometry import Geometry

class DragInfo:
    def __init__(self, wpos: QPoint, wsize: QSize, mv: QMatrix4x4, proj: QMatrix4x4, vport: QRect):
        self.wsize = wsize
        self.mvm = mv
        self.proj = proj
        self.vport = vport
        self.wStartPos = wpos
        self._normalize(self.wStartPos)
        self.wCurrentPos = self.wStartPos

    def update(self, wpos: QPoint):
        self.wLastCurrentPos = self.wCurrentPos
        self.wCurrentPos = wpos
        self._normalize(self.wCurrentPos)

    @property
    def mCurrentPos(self):
        p = QVector3D(self.wCurrentPos.x, self.wCurrentPos.y, 0.5)
        return p.unproject(self.mv, self.proj, self.vport)

    @property
    def mStartPos(self):
        p = QVector3D(self.wStartPos.x, self.wStartPos.y, 0.5)
        return p.unproject(self.mv, self.proj, self.vport)

    @property
    def mLastCurrentPos(self):
        p = QVector3D(self.wLastCurrentPos.x, self.wLastCurrentPos.y, 0.5)
        return p.unproject(self.mv, self.proj, self.vport)

    @property
    def wDelta(self):
        d = self.wCurrentPos - self.wStartPos
        return d

    @property
    def normalizedDelta(self):
        d = self.wDelta
        nd = QPointF(float(d.x())/self.wsize.width(), float(d.y())/self.wsize.height())
        return nd

    def _normalize(self, wpos: QPoint):
        wpos.setY(self.wsize.height() - wpos.y())  # convert to GL coord system
        return wpos


class Signals(QObject):
    __instance = None

    updateGL = Signal()
    draggingBegin = Signal(DragInfo)
    dragging = Signal(DragInfo)
    draggingEnd = Signal(DragInfo)

    geometryAdded = Signal(Geometry)
    geometryImported = Signal(Geometry)
    importGeometry = Signal(str)

    def __init__(self):
        """ Virtually private constructor. """
        if Signals.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            super().__init__()
            Signals.__instance = self

    @staticmethod
    def get():
        if Signals.__instance == None:
            Signals()
        return Signals.__instance

