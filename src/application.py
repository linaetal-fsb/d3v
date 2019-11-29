from PySide2.QtWidgets import QApplication
from PySide2.QtCore import QSettings, QCommandLineParser, QCommandLineOption

import sys
import os
import moduleImporter as importer
from signals import Signals

class App(QApplication):
    def __init__(self,argv):
        super().__init__(argv)
        self.setApplicationVersion("0.1")
        self.setOrganizationName("testung")
        self.setApplicationName("d3v")
        Signals.get().geometryImported.connect(self.registerGeometry)

# hardcoded path
#        defModulesPaths = os.path.join(self.applicationDirPath(), 'modules')
        defModulesPaths = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
        self.modulesPaths = []
        self.modulesPaths += [defModulesPaths]

# read the settings
#
# self.settings object holds values read from init file
# NOT active values!!!!
        self.settings = QSettings()
        if self.settings.contains('modules/paths/default-path'):
            self.modulesPaths = self.settings.value('modules/paths/default-path').toStringList()

# force from command line arguments
        self.parseArguments(argv)


    def run(self):
        self.loadAllModules()

        for m in self.models:
            Signals.get().importGeometry.emit(m)

        return self.exec_()


    def loadAllModules(self):
        #m = (general, commands, io, painters)
        # searches for possible modules to be imported
        modules2load = self.findAllPossibleModules(self.modulesPaths)

#setting python path BEFORE importing modules
        for p in self.modulesPaths:
            sys.path.append(p)


        self.iohandlers = []
        self.commands = []
        self.painters = []
        self.geometry = []

        self.loadCommands(modules2load[1])
        self.loadIOHandlers(modules2load[2])
        self.loadPainters(modules2load[3])

    def parseArguments(self,argv):
        parser = QCommandLineParser()
        help = parser.addHelpOption()
        version = parser.addVersionOption()

        apath = QCommandLineOption(('a','add-modules-path'), 'additional path where modules are searched for', valueName = 'path')
        rpath = QCommandLineOption(('r','replace-modules-path'), 'force new path where modules are searched for, instead of default one', valueName = 'path')
        saveOpts = QCommandLineOption(('s','save-options'), 'make command line options permanent for future usage')
        parser.addOption(apath)
        parser.addOption(rpath)
        parser.addOption(saveOpts)
        parser.addPositionalArgument('model','list of files (i.e. models) to load')

        if not parser.parse(argv):
            print(parser.errorText())
            exit(1)

        if parser.isSet(help):
            parser.showHelp()
            sys.exit(0)

        if parser.isSet(version):
            parser.showVersion()
            sys.exit(0)

        if parser.isSet(rpath):
            self.modulesPaths = [parser.value(rpath)]

        if parser.isSet(apath):
            p = parser.values(apath)
            self.modulesPaths += p
            print (self.modulesPaths)

        if parser.isSet(saveOpts):
            if parser.isSet(apath):
                self.settings.setValue('modules/paths/add-path', parser.values(apath))
            if parser.isSet(rpath):
                self.settings.setValue('modules/paths/default-path', parser.value(rpath))

        self.models = parser.positionalArguments()

    def loadIOHandlers(self, iohandlers2load):
        for h in iohandlers2load:
            importer.importIOHandler(self,h)

    def loadCommands(self, cmds2load):
        for c in cmds2load:
            importer.importCommand(self,c)

    def loadPainters(self, painters2load):
        for p in painters2load:
            importer.importPainter(self, p)

    def findAllPossibleModules(self, modulesPaths):
        general = []
        commands = []
        io = []
        painters = []
        for mPath in modulesPaths:
            if os.path.exists(mPath) == False:
                continue
            for m in os.listdir(mPath):
                mfname = os.path.join(mPath,m)
                if m == '__pycache__':
                    continue

                if m == 'commands' and os.path.isdir(mfname):
                    cpath = os.path.join(mPath, m)
                    res = self.findAllPossibleModules([cpath])
                    if res[0]:
                        commands.append(res[0])
                    continue

                if m == 'painters' and os.path.isdir(mfname):
                    ppath = os.path.join(mPath, m)
                    res = self.findAllPossibleModules([ppath])
                    if res[0]:
                        painters += res[0]
                    continue

                if m == 'io' and os.path.isdir(mfname):
                    iopath = os.path.join(mPath, m)
                    res = self.findAllPossibleModules([iopath])
                    if res[0]:
                        io.extend(res[0])
                    continue

                general.append(mfname)

        return (general, commands, io, painters)

    def registerIOHandler(self, handler):
        self.iohandlers.append(handler)

    def registerCommand(self, command):
        self.commands.append(command)

    def registerPainter(self, painter):
        self.painters.append(painter)

    def registerGeometry(self, geometry):
        self.geometry.append(geometry)
        Signals.get().geometryAdded.emit(geometry)
