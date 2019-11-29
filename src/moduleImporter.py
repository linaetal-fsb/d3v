import sys
import os
import importlib.util


def importModule(moduleFileName:str):
    moduleName = os.path.splitext(moduleFileName)[0]
    spec = importlib.util.spec_from_file_location(moduleName, moduleFileName)
    module = importlib.util.module_from_spec(spec)
    sys.modules[moduleName] = module
    spec.loader.exec_module(module)
    return module




def importIOHandler(app, iohandler2load):
    try:
        h = importModule(iohandler2load)
        app.registerIOHandler(h.createIOHandler())

    except FileNotFoundError as err:
        print("Folder '{}' not found ".format(err.filename))


def importCommand(app, command2load):
    try:
        m = importModule(command2load)
        app.registerCommand(m.createCommand())

    except FileNotFoundError as err:
        print("Folder '{}' not found ".format(err.filename))
    except e:
        pass


def importPainter(app, painter2load):
    try:
        m = importModule(painter2load)
        app.registerPainter(m.createPainter())
    except ImportError as e:
        print(e)
