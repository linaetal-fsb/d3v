from commands import Command

class IOHandler(Command):
    def __init__(self):
        super().__init__()

    def importGeometry(self, fileName):
        pass

    def exportGeometry(self, fileName, geometry2export):
        pass

    def getImportFormats(self):
        return []

    def getExportFormats(self):
       return []
