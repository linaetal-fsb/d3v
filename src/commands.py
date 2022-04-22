
from PySide6 import QtCore
from PySide6.QtWidgets import QMenu

class Command(QtCore.QObject):
    def __init__(self):
        super().__init__()

    def initialize(self, app):
        pass

