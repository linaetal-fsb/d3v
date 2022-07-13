from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem
#from .gtree_item import  GTreeItem

class __geometry_manager(QObject):

    #signals

    # emitted right before any change in geometry
    geometry_state_changing = Signal(list, list, list)       # visible, loaded, selected

    visible_geometry_changed = Signal(list, list, list)      # visible, loaded, selected
    selected_geometry_changed = Signal(list, list, list)     # visible, loaded, selected
    geometry_created = Signal(list)
    geometry_removed = Signal(list)

    __loaded_geometry = set()
    __visible_geometry = set()
    __selected_geometry = set()

    def __init__(self):
        super().__init__()

    def add_geometry(self, geometry_2_add):
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        g2a = set(geometry_2_add)
        self.__loaded_geometry |= g2a
        self.geometry_created.emit(list(geometry_2_add))
        self.visible_geometry_changed.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)

    def remove_geometry(self, geometry_2_remove:list):
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        self.__loaded_geometry = set(self.__loaded_geometry) - set(geometry_2_remove)
        to_emit = list(geometry_2_remove - self.__loaded_geometry)
        self.geometry_removed.emit(to_emit)

    def hide_geometry(self, geometry_2_hide):
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        hidden = set(geometry_2_hide)
        self.__visible_geometry -= hidden
        self.visible_geometry_changed.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)

    def show_geometry(self, geometry_2_show):
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        g2s = set(geometry_2_show)
        self.__visible_geometry |= g2s
        self.visible_geometry_changed.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)

    def select_geometry(self, geometry_2_select = None, selection_info = None, exclusive_selection = True):
        assert(geometry_2_select is None or selection_info is None)
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        if exclusive_selection:
            self.__selected_geometry.clear()
        selected = geometry_2_select or (selection_info.geometry,)
        print("{}".format(selected[0].guid))
        g2s = set(selected)
        self.__selected_geometry |= g2s
        self.selected_geometry_changed.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)

    def unselect_geometry(self, geometry_2_unselect):
        self.geometry_state_changing.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)
        g2u = set(geometry_2_unselect)
        self.__selected_geometry -= g2u
        self.selected_geometry_changed.emit(self.visible_geometry, self.loaded_geometry, self.selected_geometry)

    @property
    def loaded_geometry(self):
        return list(self.__loaded_geometry)

    @property
    def visible_geometry(self):
        return list(self.__visible_geometry)

    @property
    def selected_geometry(self):
        return list(self.__selected_geometry)

    @property
    def view_model(self):
        return self._view_model


geometry_manager = __geometry_manager()
