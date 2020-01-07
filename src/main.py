#!/usr/bin/env python3

from application import App
from PySide2.QtCore import QCoreApplication, Qt
import mainwin

import sys


if __name__ == '__main__':
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = App(sys.argv)
    app.mainFrame = mainwin.create()
    app.mainFrame.show()
    app.run()
