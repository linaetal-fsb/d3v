from iohandlers import IOHandler
from signals import Signals
from geometry import Geometry
import openmesh as om
import os
import numpy as np

class DBBImporter(IOHandler):
    def __init__(self):
        super().__init__()
        Signals.get().importGeometry.connect(self.importGeometry)

    def importGeometry(self, fileName):
        if len(fileName) < 1:
            return
        filename, file_extension = os.path.splitext(fileName)
        if file_extension != ".dbb":
            return
        dbb=DBB(fileName)
        g = Geometry()
        g.mesh = dbb.getmesh()
        Signals.get().geometryImported.emit(g)

    def getImportFormats(self):
        return []


def createIOHandler():
    return DBBImporter()

class DBB ():
    def __init__(self,fileName):
        self.filename=fileName
    def getmesh(self):
        m=self.test()
        return m
    def test(self):
        mesh= om.TriMesh()
        vhandle = [0]*5
        data = np.array([0, 1, 0])
        vhandle[0] = mesh.add_vertex(data)
        #vhandle.append(mesh.add_vertex(data))
        data = np.array([1, 0, 0])
        vhandle[1] = mesh.add_vertex(data)
        data = np.array([2, 1, 0])
        vhandle[2] = mesh.add_vertex(data)
        data = np.array([0, -1, 0])
        vhandle[3] = mesh.add_vertex(data)
        data = np.array([2, -1, 0])
        vhandle[4] = mesh.add_vertex(data)

        fh0 = mesh.add_face(vhandle[0], vhandle[1], vhandle[2])
        fh1 = mesh.add_face(vhandle[1], vhandle[3], vhandle[4])
        fh2 = mesh.add_face(vhandle[0], vhandle[3], vhandle[1])

        vh_list = [vhandle[2], vhandle[1], vhandle[4]]
        fh3 = mesh.add_face(vh_list)
        return mesh
        pass
    def dbbmesh(self):
        mesh= om.TriMesh()
        #read self.filename
        return mesh
        pass


