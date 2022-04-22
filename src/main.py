#!/usr/bin/env python

from application import App
from PySide6.QtCore import QCoreApplication, Qt
import mainwin

import sys


if __name__ == '__main__':
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = App(sys.argv)
    app.mainFrame = mainwin.create()
    app.mainFrame.show()
    app.run()
