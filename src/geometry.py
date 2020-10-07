import openmesh as om
import uuid
from PySide2.QtCore import QObject

from bounds import BBox
#from selinfo import SelectionInfo


class Geometry(QObject):
    def __init__(self, guid=None):
        super().__init__()
        self._guid = guid
        if not self._guid:
            self._guid = uuid.uuid4()

        self._mesh = om.TriMesh()
        self.subdivboxtree = 0

    def createSubdivisonBoxTree(self):
        from subDivBoxTree import SubDivBoxTree
        self.subdivboxtree = SubDivBoxTree(self._mesh)
        self.subdivboxtree.createTreeRoot(self.bbox)

    @property
    def guid(self):
        return self._guid

    @guid.setter
    def guid(self, newGuid):
        self._guid = newGuid

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, newMesh):
        self._mesh = newMesh
        self.createSubdivisonBoxTree()

    @property
    def bbox(self):
        bb = BBox.construct(self._mesh.points())
        return bb

    def onSelected(self, si):
        print ("Selected geometry: {}".format(self.guid))
        print("Selected facet: {}".format(si.face))
        print("Intersection point distance: {}".format(si.distance))
