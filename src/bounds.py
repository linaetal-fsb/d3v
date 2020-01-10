from PySide2.QtGui import QVector3D
import numpy as np

class BBox():
    def __init__(self, minCoord = None, maxCoord = None, empty:bool = False):
        self._minCoord = np.array(minCoord)
        self._maxCoord = np.array(maxCoord)

        self._empty = empty

    @classmethod
    def construct(cls, points):
        if not points:
            return BBox(empty = True)

        minc = np.array(points[0])
        maxc = np.array(points[0])

        for p in points:
            for i in range(3):
                minc[i] = min(minc[i], p[i])
                maxc[i] = max(maxc[i], p[i])

        return cls(minc, maxc)


    ''' union '''
    def __add__(self, other):
        if self.empty and other.empty:
            return BBox(empty = True)

        if self.empty:
            return other

        if other.empty:
            return self

        maxc = np.array([0,0,0])
        minc = np.array([0,0,0])
        for i in range(3):
            maxc[i] = max(self.maxCoord[i], other.maxCoord[i])
            minc[i] = min(self.minCoord[i], other.minCoord[i])

        return BBox(minc, maxc)

    def __or__(self, other):
        return self.__add__(other)


    ''' intersection '''
    def __mul__(self, other):
        if self.empty or other.empty:
            return BBox(empty = True)


        maxc = np.array([0,0,0])
        minc = np.array([0,0,0])
        for i in range(3):
            maxc[i] = min(self.maxCoord[i], other.maxCoord[i])
            minc[i] = max(self.minCoord[i], other.minCoord[i])

        empty = any(minc > maxc)
        return BBox(minc, maxc, empty)

    def __and__(self, other):
        return self.__mul__(other)

    def __nonzero__(self):
        return not self.empty


    @classmethod
    def intersection(cls, first:BBox, second:BBox):
        return cls = first * second

    @classmethod
    def union(cls, first:BBox, second:BBox):
        return cls = first + second

    @property
    def center(self):
        return (self._minCoord + self._maxCoord) * 0.5

    @property
    def radius(self):
        return np.linalg.norm(self._maxCoord - self._minCoord) * 0.5

    @property
    def minCoord(self):
        return self._minCoord

    @property
    def maxCoord(self):
        return self._maxCoord

    @property
    def empty(self):
        return self._empty


if __name__ == '__main__':
    import unittest as ut

    class BBTests(ut.TestCase):
        def test_empty(self):
            bb = BBox(empty = False)
            self.assertFalse(bb.empty)
            self.assertTrue(bb)

        def test_points(self):
            bb = BBox.construct([[-5, -5, -5], [0, 1, 2], [0, 0, 0], [10, 10, 10], [-5, -5, -5]])
            self.assertTrue(bb)
            self.assertTrue(all(bb.minCoord == [-5, -5,-5]))
            self.assertTrue(all(bb.maxCoord == [10,10,10]))

        def test_operations(self):
            bb1 = BBox.construct([[0,0,0], [10, 10, 10]])
            bb2 = BBox.construct([[5,5,5], [15, 15, 15]])

            bbu = bb1 + bb2
            bbi = bb1 * bb2
            self.assertTrue(all(bbu.minCoord == [0., 0., 0.]))
            self.assertTrue(all(bbu.maxCoord == [15., 15., 15.]))
            self.assertTrue(bbu)
            self.assertTrue(all(bbi.minCoord == [5., 5., 5.]))
            self.assertTrue(all(bbi.maxCoord == [10., 10., 10.]))
            self.assertTrue(bbi)

            bbu = bb1 | bb2
            bbi = bb1 & bb2
            self.assertTrue(all(bbu.minCoord == [0., 0., 0.]))
            self.assertTrue(all(bbu.maxCoord == [15., 15., 15.]))
            self.assertTrue(bbu)
            self.assertTrue(all(bbi.minCoord == [5., 5., 5.]))
            self.assertTrue(all(bbi.maxCoord == [10., 10., 10.]))
            self.assertTrue(bbi)

        def test_intersection_empty(self):
            bb1 = BBox.construct([[0,0,0], [10, 10, 10]])
            bb2 = BBox.construct([[15,15,15], [25, 25, 25]])

            bbu = bb1 + bb2
            bbi = bb1 * bb2
            self.assertTrue(all(bbu.minCoord == [0., 0., 0.]))
            self.assertTrue(all(bbu.maxCoord == [25., 25., 25.]))
            self.assertTrue(bbu)
            self.assertFalse(bbi)
            self.assertFalse(bbi.empty)

    ut.main()
