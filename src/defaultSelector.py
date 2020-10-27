from rayTracing import Ray, Box3DIntersection
from signals import Signals
from selinfo import SelectionInfo
import openmesh as om
import numpy as np
from selection import Selector
import time
from PySide2.QtCore import Slot
from subDivBoxTree import SubDivBoxTree


class DefaultSelector(Selector):
    def __init__(self):
        super().__init__()
        self.subDivBoxTrees = {}

    def addGeometry(self, geometry):
        """
        Creates a SubDivBoxTree object for a given geometry. The SubDixBoxTree object is saved internally in a dict.
        :param geometry: geometry of type Geometry
        :return:
        """
        subDivBoxTree = SubDivBoxTree(geometry.mesh)
        subDivBoxTree.createTreeRoot(geometry.bbox)
        self.subDivBoxTrees[geometry.guid] = subDivBoxTree

    @Slot()
    def onGeometryAdded(self, geometry):
        self.addGeometry(geometry)

    def removeGeometry(self, geometry):
        """
        Removes the SubDixBoxTree which corresponds to geometry from the dict.
        :param geometry: geometry of type Geometry
        :return:
        """
        self.subDivBoxTrees.pop(geometry.guid)

    def select(self, los, geometries):
        tSS = time.perf_counter()
        self.selectList(los, geometries)
        dtS = time.perf_counter() - tSS
        print("Selection time, s:", dtS)

    def selectList(self, los, geometries):
        """
        Determines if a ray defined by los variable intersects with a geometry contained in geometry variable. Emits a
        signal containing the selected geometry instead of returning the selected geometry.

        :param los: line of sight. los = [o, d], where o is the position of the viewer and d is the direction to the
        targeted object. o and d are given as QVector3D
        :param geometry: list holding the current geometries
        :return:
        """
        if not len(geometries):
            return
        sis = []
        for geometry in geometries:
            # 1. test bounding box
            o = [los[0].x(), los[0].y(), los[0].z()]
            d = [los[1].x(), los[1].y(), los[1].z()]
            intrsectLeafs = []
            guid = geometry.guid
            isInBox, intrsectLeafs = self.subDivBoxTrees[guid].getIntersectedLeafs(o, d, intrsectLeafs)

            points = geometry.mesh.points()
            fv_indices = geometry.mesh.fv_indices()

            # 2. test mesh in intersected subdivision box tree leafs
            if isInBox:
                for leaf in intrsectLeafs:
                    meshres = self.getMeshInterscection(o, d, leaf.facets, points, fv_indices)
                    # meshres = self.getMeshInterscectionSDBTNew(ray, leaf.facets, geo.mesh)
                    if len(meshres) > 0:
                        si = SelectionInfo()
                        si.update(meshres[0], meshres[1], geometry)
                        sis.append(si)

        # Looks for geometry with shortest distance and gives it to
        if len(sis) > 0:
            si = sis[0]
            i = 1
            while i < len(sis):
                if sis[i].getDistance() < si.getDistance():
                    si = sis[i]
                i = i + 1
            # nakon sto je selekcija odradjena
            # fill in sve podatke u SelectionInfo object
            # selected je selekcionirana geometrija
            selected = si.getGeometry()
            selected.onSelected(si)

        else:
            selected = None
            si = SelectionInfo()
        # obavijesti sve zainteresirane da je selekcija promijenjena
        Signals.get().selectionChanged.emit(si)

    def getMeshInterscection(self, o, d, fhlist, points, fv_indices):
        """
        Calculates the facet with which a ray intersects. If several facets intersect with the incident ray, the facet
        with minimum distance from ray origin is returned.

        :param o: ray origin
        :param d: ray propagation delta: d = [dx, dy, dz]
        :param fhlist: Indices of the faces for which an intersection should be proved.
        :param points: array holding all vertices of the geometry.
        :param fv_indices: array holding vertex indices of each face. fhlist.shape = (n, 3), where n is the amount of
        faces.
        :return: A list holding the distance and the index of the intersected facet with minimum distance to ray origin.
        """
        infinity = float("inf")

        chosen_fv_indices = fv_indices[fhlist]
        chosen_points = points[chosen_fv_indices]

        ds = self.rayIntersectsTriangleMollerTrumboreSDBT(o, d, chosen_points[:, 0], chosen_points[:, 1], chosen_points[:, 2])
        mask = ds != infinity
        intersectedFacets = fhlist[mask]
        intersectedFacetsDistances = ds[mask]

        if len(intersectedFacets) == 0:
            return []

        idx_min = np.argmin(intersectedFacetsDistances)
        result = [intersectedFacetsDistances[idx_min], intersectedFacets[idx_min]]
        return result

    def rayIntersectsTriangleMollerTrumboreSDBT(self, o, d, v0, v1, v2):
        """
        Calculates if a ray defined by (o, d) intersects with which triangles given by v0, v1, v2 holding the
        coordinates of the triangle corners. This function is meant for processing of several triangles,
        so v0, v1, v2 each have dim = (n, 3), where n is the amount of triangles.
        Algorithm originated from https://en.wikipedia.org/wiki/Möller–Trumbore_intersection_algorithm

        :param o: ray origin
        :param d: ray propagation delta: d = [dx, dy, dz]
        :param v0: (x, y, z) coordinate of first triangle corner
        :param v1: (x, y, z) coordinate of second triangle corner
        :param v2: (x, y, z) coordinate of third triangle corner
        :return: boolean array holding True if ray intersects with corresponding triangle and False otherwise/
        """
        e = 0.00000001
        infinity = float("inf")
        edge1 = np.subtract(v1, v0)
        edge2 = np.subtract(v2, v0)
        h = np.cross(d, edge2)
        a = np.sum(edge1 * h, axis=1)
        results = np.zeros(len(a))
        results[(-e < a) & (a < e)] = infinity

        mask = results != infinity
        f = 1.0 / a[mask]
        s = np.subtract(o, v0[mask])
        dot_sh = np.sum(s * h[mask], axis=1)
        u = np.multiply(f, dot_sh)
        _results = results[mask]
        _results[(u < 0.0) | (u > 1.0)] = infinity
        results[mask] = _results

        mask = results != infinity
        s = np.subtract(o, v0[mask])
        q = np.cross(s, edge1[mask])
        dot_dq = np.sum(d * q, axis=1)
        f = 1.0 / a[mask]
        v = f * dot_dq
        _results = results[mask]
        dot_sh = np.sum(s * h[mask], axis=1)
        u = np.multiply(f, dot_sh)
        _results[(v < 0.0) | (u + v > 1.0)] = infinity
        results[mask] = _results

        mask = results != infinity
        s = np.subtract(o, v0[mask])
        q = np.cross(s, edge1[mask])
        dot_edge2_q = np.sum(edge2[mask] * q, axis=1)
        f = 1.0 / a[mask]
        t = np.multiply(f, dot_edge2_q)
        mask = results != infinity
        results[mask] = t
        return results
