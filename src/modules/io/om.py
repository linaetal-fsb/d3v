from iohandlers import IOHandler, ImportError

from geometry import Geometry
import openmesh as om

class OpenMeshImporter(IOHandler):
    def __init__(self):
        super().__init__()

    def do_import_geometry(self, fileName):
        g = Geometry()
        m = om.read_trimesh(fileName)
        g.mesh = m
        return g

    def getImportFormats(self):
        return (".obj", ".stl", ".ply", ".off")

def createIOHandler():
    return OpenMeshImporter()