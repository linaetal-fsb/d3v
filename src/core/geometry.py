import openmesh as om
import uuid
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem

from bounds import BBox
import enum
from geometry_tree import GTreeItem

class Geometry(QObject):
    def __init__(self, name = '', guid=None):
        super().__init__()
        self.__name = name
        self._guid = guid
        if not self._guid:
            self._guid = uuid.uuid4()

        self._mesh = om.TriMesh()

    @property
    def guid(self):
        return self._guid

    @guid.setter
    def guid(self, newGuid):
        self._guid = newGuid

    @property
    def mesh(self):
        return self._mesh

    @mesh.setter
    def mesh(self, newMesh):
        self._mesh = newMesh

    @property
    def bbox(self):
        bb = BBox.construct(self._mesh.points())
        return bb

    def onSelected(self, si):
        if __debug__:
            print ("Selected geometry: {}".format(self.guid))
            print("Selected facet: {}".format(si.face))
            print("Intersection point distance: {}".format(si.distance))



class __geometry_manager(QObject):

    #signals
    visible_geometry_changed = Signal(list, list, list ) # visible, loaded, selected
    selected_geometry_changed = Signal(list, list)     # selected, visible
    geometry_created = Signal(list)
    geometry_removed = Signal(list)

    __loaded_geometry = set()
    __visible_geometry = set()
    __selected_geometry = set()

    def __init__(self):
        super().__init__()
        self.__view_model = QStandardItemModel()

        itm = QStandardItem("root")
        self.__view_model.setItem(0, 0, itm)

    def add_geometry(self, geometry_2_add):
        g2a = set(geometry_2_add)
        self.__loaded_geometry |= g2a
        for g in g2a:
            GTreeItem.load(g)
#        for g in g2a:
#            itm = QStandardItem(str(g.guid))
#            self.__view_model.setItem(0,0, itm)
        self.geometry_created.emit(list(geometry_2_add))


    def remove_geometry(self, geometry_2_remove:list):
        self.__loaded_geometry = set(self.__loaded_geometry) - set(geometry_2_remove)
        to_emit = list(geometry_2_remove - self.__loaded_geometry)
        self.geometry_removed.emit(to_emit)


    def hide_geometry(self, geometry_2_hide: list):
        hidden = set(geometry_2_hide)
        self.__visible_geometry -= hidden
        self.visible_geometry_changed.emit(self.__visible_geometry, self.__loaded_geometry, self.__selected_geometry)


    def show_geometry(self, geometry_2_show: list):
        g2s = set(geometry_2_show)
        self.__visible_geometry |= g2s
        self.visible_geometry_changed.emit(self.__visible_geometry, self.__loaded_geometry, self.__selected_geometry)

    def select_geometry(self, geometry_2_select):
        g2s = set(geometry_2_select)
        self.__selected_geometry |= g2s
        self.visible_geometry_changed.emit(self.__visible_geometry, self.__loaded_geometry, self.__selected_geometry)

    def unselect_geometry(self, geometry_2_unselect):
        g2u = set(geometry_2_unselect)
        self.__selected_geometry -= g2u
        self.visible_geometry_changed.emit(self.__visible_geometry, self.__loaded_geometry, self.__selected_geometry)

    @property
    def loaded_geometry(self):
        return self.__loaded_geometry

    @property
    def visible_geometry(self):
        return self.__visible_geometry

    @property
    def selected_geometry(self):
        return self.__selected_geometry

    @property
    def view_model(self):
        return self.__view_model

geometry_manager = __geometry_manager()