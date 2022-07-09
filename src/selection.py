from PySide6.QtCore import QObject, Signal
from core import geometry_manager
from PySide6.QtGui import QVector3D
from core import Geometry
from signals import Signals
from selinfo import SelectionInfo
import openmesh as om
import numpy as np
import math


class Selector(QObject):
    selection_info_changled = Signal(SelectionInfo)

    def __init__(self):
        super().__init__(None)

    def select(self, los, srcGeometry=None, publish=True):
        geometry = srcGeometry or geometry_manager.visible_geometry
        si = self._select(los, geometry) if geometry else SelectionInfo()
        if publish:
            self.selection_info_changled.emit(si)
            geometry_manager.select_geometry(selection_info=si)

    def _select(self, los, geometry):
        return SelectionInfo()
