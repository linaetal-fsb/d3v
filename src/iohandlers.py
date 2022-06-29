from commands import Command
from core import Geometry, geometry_manager
from PySide6.QtWidgets import QMessageBox
import os

class ImportError(Exception):
    def __init__(self, why:str):
        super().__init__(why)

class IOHandler(Command):
    def __init__(self):
        super().__init__()

    def import_geometry(self, fileName):
        try:
            geometry = self.do_import_geometry(fileName)
            geometry_manager.add_geometry([geometry])
        except Exception as err:
            QMessageBox.warning(None, "Error", "Problem loading '{}': {}".format(fileName, err))

    def do_import_geometry(self, file_name):
        return []

    def export_geometry(self, file_name, geometry2export):
        pass

    def supportsImport(self, fname):
        ext = os.path.splitext(fname)[1]
        return ext in self.getImportFormats()

    def supportsExport(self, fname):
        ext = os.path.splitext(fname)
        return ext in self.getExportFormats()


    def getImportFormats(self):
        return []

    def getExportFormats(self):
       return []
