from PySide2.QtWidgets import QOpenGLWidget, QApplication
from PySide2.QtGui import QMouseEvent, QMatrix4x4, QVector3D, QQuaternion, QOpenGLDebugLogger, QOpenGLDebugMessage
from PySide2.QtCore import Qt, QRect, Slot

from signals import Signals, DragInfo
from painterbasic.basicpainter import BasicPainter

from bounds import  BBox
from selection import Selector
from application import App


class GlWin(QOpenGLWidget):
    glPainters = [BasicPainter()]
    mv = QMatrix4x4()
    proj = QMatrix4x4()
    vport = QRect()
    eye = QVector3D(0, 0, 10.0)  # position of the viewer
    poi = QVector3D(0, 0, 0)  # point of interest
    pan = QVector3D(0, 0, 0)
    phi = 0.0  # rotation about X
    theta = 0.0  # rotation about Y
    zoomFactor = 1.0 #vrport

    _rotate = 1
    _zoom   = 2
    _pan    = 4
    _kbModifiers = {
        Qt.NoModifier: _rotate,
        Qt.ShiftModifier: _zoom,
        Qt.ControlModifier: _pan,
    }
 
    _bb = BBox(empty = True)

    #def __init__(self,  parent=None):
        #pass
        #QOpenGLWidget.__init__(self,parent)
        #QOpenGLFunctions.__init__(self)

    def paintGL(self):
        ratio = float(self.vport.width())/float(self.vport.height())
        self.proj = QMatrix4x4()
        r = self._bb.radius * 2.0 if not self._bb.empty else 10.0
        self.proj.ortho(-r*ratio * self.zoomFactor,r*ratio * self.zoomFactor,
                        -r * self.zoomFactor,r * self.zoomFactor,
                        -r, r)

        for p in self.glPainters:
            p.setprogramvalues(self.proj, self.mv, self.mv.normalMatrix(), QVector3D(0, 0, 70))

        for p in self.glPainters:
            p.paintGL()


    def initializeGL(self):
        self._glDebugCounter = 0
        self._glLogger = QOpenGLDebugLogger(self)
        self._glLogger.initialize()
        self._glLogger.messageLogged.connect(self.showGlDebugMessage)
        self._glLogger.startLogging()

        Signals.get().updateGL.connect(self.updateGL)
        Signals.get().dragging.connect(self.onDrag)
        Signals.get().draggingEnd.connect(self.onDragEnd)
        Signals.get().geometryAdded.connect(self.onGeometryAdded)

        for p in self.glPainters:
            p.initializeGL()

    def resizeGL(self, w:int, h:int):
        self.vport.setWidth(w)
        self.vport.setHeight(h)

        for p in self.glPainters:
            p.resizeGL(w,h)

    def addPainter(self, painter):
        self.glPainters.append(painter)

    def mouseMoveEvent(self, event:QMouseEvent):
        self.dragInfo.update(event.pos())
        Signals.get().dragging.emit(self.dragInfo)

    def mouseDoubleClickEvent(self, event:QMouseEvent):
        pass

    def mousePressEvent(self, event:QMouseEvent):
        self.dragInfo = DragInfo(event.pos(), self.geometry(), self.mv, self.proj, self.vport)
        Signals.get().draggingBegin.emit(self.dragInfo)

    def mouseReleaseEvent(self, event:QMouseEvent):
        self.dragInfo.update(event.pos())
        Signals.get().draggingEnd.emit(self.dragInfo)

        # mouse click
        if event.button() == Qt.LeftButton and self.dragInfo.wCurrentPos == self.dragInfo.wStartPos:
            s = Selector()
            P0 = self.dragInfo.wCurrentPos
            K = rotation(self.mv) .rotatedVector(QVector3D(0.0, 0.0, -1.0))
            s.select([P0,K], App.instance().geometry)

    @Slot()
    def updateGL(self):
        self.update()

    @Slot()
    def onDrag(self, di:DragInfo):
        app = QApplication.instance()
        mouse = QApplication.mouseButtons()
        kb = QApplication.keyboardModifiers()

        mt = self.calcMovementType(mouse, kb)
        if mt == self._zoom:
            self.updateZoomData(di)
        if mt == self._pan:
            self.updatePanData(di)
        if mt == self._rotate:
            self.updateRotateData(di)
        self.update()

    def updateZoomData(self, di:DragInfo):
        lastPos = di.wLastCurrentPos
        pos = di.wCurrentPos
        d = pos.y() - lastPos.y()
        d = float(d)/di.wsize.height()
        minz = 1.0/1.15
        maxz = 1.15
        if d >= 0:
            z = 0.5 * (maxz - 1.0) * (d + 1) + 1.0
        else:
            z = 0.5 * (1.0 - minz) * (d + 1) + minz
        self.zoomFactor *= z


    def updatePanData(self, di: DragInfo):
        pan = di.mCurrentPos - di.mLastCurrentPos
        self.mv = di.mvm
        self.mv.translate(pan)

    def updateRotateData(self, di:DragInfo):
        d = di.normalizedDelta
        #[-1:1] --> 2*[-pi:pi]
        self.phi = 2.0 * ((-d.y() + 1.0) * 1.57 - 1.57)
        self.theta = 2.0 * ((d.x() + 1.0) * 3.14 - 3.14)

        rot = rotation(di.mvm)
        r = self._bb.radius if not self._bb.empty else 10.0
        trans = translation(di.mvm)
        if trans.length() < 1.0e-5:
            trans = QVector3D(0,0,-r)
        addRot = QQuaternion.fromEulerAngles(self.phi * 57.3, self.theta * 57.3, 0.0)
        self.mv = QMatrix4x4()

        self.mv.translate(trans)
        self.mv.rotate(addRot)
        self.mv.rotate(rot)


    def calcMovementType(self, mb:Qt.MouseButtons, km:Qt.KeyboardModifiers):
        if mb == Qt.NoButton or mb == Qt.RightButton:
            return None

        if mb == Qt.MiddleButton:
            return self._pan

        assert(mb == Qt.LeftButton)

        if km == Qt.NoModifier:
            return self._kbModifiers[Qt.NoModifier]
        if km == Qt.ShiftModifier:
            return self._kbModifiers[Qt.ShiftModifier]
        if km == Qt.ControlModifier:
            return self._kbModifiers[Qt.ControlModifier]

        return None

    @Slot()
    def onDragEnd(self, di:DragInfo):
        self.onDrag(di)

    @Slot()
    def onGeometryAdded(self, geometry):
        self._bb =  self._bb + geometry.bbox
        for p in self.glPainters:
            p.addGeometry(geometry)


    @Slot()
    def showGlDebugMessage(self, msg:QOpenGLDebugMessage):
        self._glDebugCounter += 1
        print("{:3}: {}".format(self._glDebugCounter, msg.message()))



def rotation(m:QMatrix4x4):
    x = QVector3D(m.column(0))
    y = QVector3D(m.column(1))
    z = QVector3D(m.column(2))
    retVal = QQuaternion.fromAxes(x,y,z)
    return retVal

def translation(m:QMatrix4x4):
    retval = QVector3D(m.column(3))
    return retval