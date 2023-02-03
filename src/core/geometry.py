import openmesh as om
import uuid
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem

from bounds import BBox
import enum
from .gtree_item import GTreeItem


class Geometry(QObject):
    def __init__(self, name='', guid=None):
        super().__init__()
        self._name = name
        self._full_name = name
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
        assert bool(self._subgeometry) == False or self.mesh_empty()
        return self._mesh

    @mesh.setter
    def mesh(self, newMesh):
        assert bool(self._subgeometry) == False or newMesh.vertices_empty()
        self._mesh = newMesh

    @property
    def bbox(self):
        bb = BBox.construct(self._mesh.points())
        return bb

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def full_name(self):
        return self._full_name

    @full_name.setter
    def full_name(self, new_name):
        self._full_name = new_name

    @property
    def sub_geometry(self):
        assert bool(self._subgeometry) == False or self.mesh_empty() == True
        return self._subgeometry

    @sub_geometry.setter
    def sub_geometry(self, geometry):
        assert geometry == False or self.mesh_empty() == True
        self._subgeometry = geometry

    def mesh_empty(self):
        return self._mesh.vertices_empty() and self._mesh.edges_empty() and self._mesh.faces_empty()

    def onSelected(self, si):
        if __debug__:
            print("Selected geometry: {}".format(self.guid))
            print("Selected facet: {}".format(si.face))
            print("Intersection point distance: {}".format(si.distance))

    def flattened(self):
        flattened = []
        if self.sub_geometry:
            for s in self.sub_geometry:
                flattened += s.flattened()
            return flattened
        else:
            flattened.append(self)
            return flattened
