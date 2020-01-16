from PySide2.QtCore import QObject
import openmesh as om
#from geometry import Geometry
class SelectionInfo(QObject):

    def __init__(self):
        self.distance=-1
        self.face=0
        self.geometry =0
    def getDistance(self):
        return self.distance
    def getFace(self):
        return  self.face
    def getGeometry(self):
        return  self.geometry
    def setInfo(self,distance:float,face:om.FaceHandle,geometry):
        self.distance=distance
        self.face=face
        self.geometry = geometry
    def haveIntersection(self):
        return self.distance >= 0.0

