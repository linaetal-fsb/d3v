from selection import Selector
from PySide2.QtWidgets import QApplication
from selectorbasic.basicselector import BasicSelector

def createCommand():
    app = QApplication.instance()
    glw = app.mainFrame.glWin
    glw.selector = BasicSelector()
    print("Setting 'BasicSelector' as selector for Glwin...")
    return None