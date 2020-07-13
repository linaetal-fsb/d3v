from PySide2.QtCore import QObject
from PySide2.QtGui import QVector3D
from geometry import Geometry
from signals import Signals
from selinfo import  SelectionInfo
import  openmesh as om
import numpy as np
import math

class Selector(QObject):
    def __init__(self):
        super().__init__(None)

    def select(self, los, geometry):
        pass
