import openmesh as om
import uuid
from PySide2.QtCore import QObject
from bounds import BBox

class Geometry(QObject):
    def __init__(self, guid = None):
        super().__init__()
        self._guid = guid
        if not self._guid:
            self._guid = uuid.uuid4()

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

