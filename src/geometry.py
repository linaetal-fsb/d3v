import openmesh as om
import uuid
from PySide2.QtCore import QObject

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
    def bounds(self):
        if not _mesh.vertices():
            return (None, None)
        bb = [_mesh.vertices(0), _mesh.vertices(0)]
        for v in _mesh.vertices():
            if bb[0].x()