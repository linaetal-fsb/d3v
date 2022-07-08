import openmesh as om
import uuid
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem

from bounds import BBox
import enum
from .gtree_item import GTreeItem

class Geometry(QObject):
    def __init__(self, name = '', guid=None):
        super().__init__()
        self._name = name
        self._guid = guid
        if not self._guid:
            self._guid = uuid.uuid4()

        self._subgeometry = []
        self._mesh = om.TriMesh()

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

    @property
    def bbox(self):
        bb = BBox.construct(self._mesh.points())
        return bb

    @property
    def name(self):
        return self._name

    @property
    def sub_geometry(self):
        return self._subgeometry

    @sub_geometry.setter
    def sub_geometry(self, geometry: "Geometry"):
        self._subgeometry = geometry

    def onSelected(self, si):
        if __debug__:
            print ("Selected geometry: {}".format(self.guid))
            print("Selected facet: {}".format(si.face))
            print("Intersection point distance: {}".format(si.distance))
