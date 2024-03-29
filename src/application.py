from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide6.QtCore import QSettings, QCommandLineParser, QCommandLineOption, QObject, QEvent

import sys
import os
import moduleImporter as importer
from signals import Signals
from core import geometry_manager
import logging

class App(QApplication):
    def __init__(self,argv):
        super().__init__(argv)
        self.setApplicationVersion("0.1")
        self.setOrganizationName("testung")
        self.setApplicationName("d3v")
        Signals.get().importGeometry.connect(self.doImportGeometry)
        geometry_manager.visible_geometry_changed.connect(self.request_update)
        geometry_manager.selected_geometry_changed.connect(self.request_update)

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
        for p in self.painters:
            self.mainFrame.addPainter(p)


        for m in self.models:
            Signals.get().importGeometry.emit(m)

        return self.exec_()


    def loadAllModules(self):
        #m = (general, commands, io, painters)
        # searches for possible modules to be imported
        modules2load = self.findAllPossibleModules(self.modulesPaths)

#setting python path BEFORE importing modules
        sys.path.append(os.path.dirname(__file__))
        for p in self.modulesPaths:
            sys.path.append(p)
            for m in ('painters', 'io', 'commands'):
                sys.path.append(os.path.join(p,m))


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
        llevel = QCommandLineOption(('l','log-level'), 'verbosity of the logging. oen of (debug,info,warning,error,critical)', valueName = 'log_level')
        parser.addOption(apath)
        parser.addOption(rpath)
        parser.addOption(llevel)
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

        if parser.isSet(llevel):
            levels = {
                    'debug': logging.DEBUG,
                    'info': logging.INFO,
                    'warning': logging.WARNING,
                    'error': logging.ERROR,
                    'critical':logging.CRITICAL
                    }
            v = parser.value(llevel)
            if v not in levels.keys():
                print('log level must be one of: {}'.format(list(levels.keys())))
                sys.exit(-2)
            logging.basicConfig(level=levels[v])

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
                        commands.extend(res[0])
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

    def onImportGeometry(self, checked:bool):
        dir = self.settings.value("io/lastImportLocation", ".")
        fname = QFileDialog.getOpenFileName(None, "Import Geometry", dir)
        if fname[0]:
            dir = os.path.dirname(fname[0])
            self.settings.setValue("io/lastImportLocation", dir)
            Signals.get().importGeometry.emit(fname[0])

    def onExportGeometry(self, checked:bool):
        QMessageBox.warning(None, "Export geometry", "Exporting gemeoetry is not implemented")


    def doImportGeometry(self, fname):
        for h in self.iohandlers:
            if h.supportsImport(fname):
                geometry = h.import_geometry(fname)
                to_add = geometry,
                geometry_manager.add_geometry(to_add)
                geometry_manager.show_geometry(to_add)
                return
        QMessageBox.warning(None, "Import geometry", "No suitable iohandler found to import")

    @property
    def mainFrame(self):
        return self._mainFrame

    @mainFrame.setter
    def mainFrame(self, mainFrame):
        self._mainFrame = mainFrame


    def request_update(self, visible, loaded, selected):
        self.mainFrame.update()

