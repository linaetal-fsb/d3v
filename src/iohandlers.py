from commands import Command
import os

class IOHandler(Command):
    def __init__(self):
        super().__init__()

    def importGeometry(self, fileName):
        pass

    def exportGeometry(self, fileName, geometry2export):
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
