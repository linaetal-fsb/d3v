import sys
import os
import importlib.util
import importlib


def importModule(moduleFileName:str):
    moduleName = os.path.split(moduleFileName)[1]
    moduleName = os.path.splitext(moduleName)[0]
    return importlib.import_module(moduleName)





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
    except:
        pass


def importPainter(app, painter2load):
    try:
        m = importModule(painter2load)
        app.registerPainter(m.createPainter())
    except ImportError as e:
        print(e)
