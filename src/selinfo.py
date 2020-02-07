from PySide2.QtCore import QObject
import openmesh as om
from geometry import Geometry
class SelectionInfo(QObject):

    def __init__(self, orig=None):
        super(SelectionInfo, self).__init__()
        if orig is None:
            self.distance= float("inf")
            self.face=om.FaceHandle()
            self.geometry = Geometry()
            self.allfaces=[]
        else:
            self.distance = orig.distance
            self.face = orig.face
            self.geometry = orig.geometry

    def getDistance(self):
        return self.distance
    def getFace(self):
        return  self.face
    def getGeometry(self):
        return  self.geometry
    def update(self, distance:float, face:om.FaceHandle, geometry:Geometry):
        self.distance=distance
        self.face=face
        self.geometry = geometry
        self.allfaces.clear()
        self.allfaces.append(face)
    def haveSelection(self):
        return self.distance < float("inf")
    def isEmpty(self):
        return  not self.haveSelection()
    def nFaces(self):
        return len(self.allfaces)



