
from PySide2 import QtCore
from PySide2.QtWidgets import QMenu

class Command(QtCore.QObject):
    def __init__(self):
        super().__init__()

    def initialize(self, app):
        pass

