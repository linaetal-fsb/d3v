from iohandlers import IOHandler, ImportError

from core import Geometry
import openmesh as om
import logging

class OpenMeshImporter(IOHandler):
    def __init__(self):
        super().__init__()

    def do_import_geometry(self, file_name):
        g = Geometry(name = file_name)
        m = om.read_trimesh(file_name)
        g.mesh = m
        logging.debug("do_import_geometry: {}".format(g.guid))
        return g

    def getImportFormats(self):
        return (".obj", ".stl", ".ply", ".off")

def createIOHandler():
    return OpenMeshImporter()