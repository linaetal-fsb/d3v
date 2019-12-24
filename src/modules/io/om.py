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
        try:
            m = om.read_trimesh(fileName)
        except:
            print("File not supported for read with openmesh")
            return
        g.mesh = m
        Signals.get().geometryImported.emit(g)

    def getImportFormats(self):
        return []


def createIOHandler():
    return OpenMeshImporter()