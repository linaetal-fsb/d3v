from PySide2.QtCore import QObject
from geometry import Geometry
from signals import Signals
from selinfo import  SelectionInfo

class Selector(QObject):
    def __init__(self):
        super().__init__(None)

    def select(self, los, geometry):
        if not len(geometry):
            return
        # geometry je lista geometrije iz koje treba izracunati selekciju

        # selected je selected geometry
        # si je SelectionInfo --> sadrzi podatke o selekciji
        si = SelectionInfo()

        # nakon sto je selekcija odradjena
        # fill in sve podatke u SelectionInfo object
        # selected je selekcionirana geometrija

        selected = geometry[0] # samo privremeno
        selected.onSelected(si)

        # obavijesti sve zainteresirane da je selekcija promijenjena
        Signals.get().selectionChanged.emit(si)