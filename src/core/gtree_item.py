from PySide6.QtWidgets import QTreeWidgetItem
#from .geometry import Geometry

class GTreeItem(QTreeWidgetItem):
    def __init__(self, name:str, geometry):
        super(GTreeItem, self).__init__([name])
        self._geometry = geometry

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, g):
        self._geometry = g



# class GTreeItem:
#     def __init__(self, parent: 'GTreeItem' = None):
#         self._parent = parent
#         self._children = []
#
#     def appendChild(self, item: 'GTreeItem'):
#         """Add item as a child"""
#         self._children.append(item)
#
#     def child(self, row: int) -> 'GTreeItem':
#         """Return the child of the current item from the given row"""
#         return self._children[row]
#
#     def parent(self) -> 'GTreeItem':
#         """Return the parent of the current item"""
#         return self._parent
#
#     def childCount(self) -> int:
#         """Return the number of children of the current item"""
#         return len(self._children)
#
#     def row(self) -> int:
#         """Return the row where the current item occupies in the parent"""
#         return self._parent._children.index(self) if self._parent else 0
#
#     @classmethod
#     def load(
#             cls, value, parent: 'GTreeItem' = None, sort=True
#     ) -> 'GTreeItem':
#         """Create a 'root' TreeItem from a nested list or a nested dictonary
#
#         Examples:
#             with open("file.json") as file:
#                 data = json.dump(file)
#                 root = TreeItem.load(data)
#
#         This method is a recursive function that calls itself.
#
#         Returns:
#             TreeItem: TreeItem
#         """
#         rootItem = parent #GTreeItem(parent)
#
#         if isinstance(value, dict):
#             items = sorted(value.items()) if sort else value.items()
#
#             for key, value in items:
#                 child = cls.load(value, rootItem)
#                 child.key = key
#                 child.value_type = type(value)
#                 rootItem.appendChild(child)
#
#         elif isinstance(value, list):
#             for index, value in enumerate(value):
#                 child = cls.load(value, rootItem)
#                 child.key = index
#                 child.value_type = type(value)
#                 rootItem.appendChild(child)
#
#         else:
#             rootItem.value = value
#             rootItem.value_type = type(value)
#
#         return rootItem
