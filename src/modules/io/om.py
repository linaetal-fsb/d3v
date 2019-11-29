from iohandlers import IOHandler
from signals import Signals
from geometry import Geometry
import openmesh as om

class OpenMeshImporter(IOHandler):
    def __init__(self):
        super().__init__()
        Signals.get().importGeometry.connect(self.importGeometry)

    def importGeometry(self, fileName):
        g = Geometry()
        m = om.read_trimesh(fileName)
        g.mesh = m
        Signals.get().geometryImported.emit(g)

    def getImportFormats(self):
        return []


def createIOHandler():
    return OpenMeshImporter()