from rayTracing import dmnsn_ray, dmnsn_optimized_ray, dmnsn_aabb
from signals import Signals
from selinfo import SelectionInfo
import openmesh as om
import numpy as np
from selection import Selector
import time


class DefaultSelector(Selector):
    def __init__(self):
        super().__init__()

    def select(self, los, geometry):
        tSS = time.perf_counter()
        # self.selectOld(los,geometry)
        self.selectList(los, geometry)
        # self.selectNP(los, geometry)

        dtS = time.perf_counter() - tSS
        print("Selection time, s:", dtS)

    def selectList(self, los, geometry):
        if not len(geometry):
            return
        sis = []
        intrsectLeafs = []
        for geo in geometry:
            isInBox = True
            # 1. test bounding box
            t = 99999999
            ray = dmnsn_ray(los)
            opt_ray = dmnsn_optimized_ray(ray)
            intrsectLeafs.clear()
            isInBox = geo.subdivboxtree.getIntersectedLeafs(opt_ray, t, intrsectLeafs)

            points = geo.mesh.points()
            fv_indices = geo.mesh.fv_indices()

            # 2. test mesh in intersected subdivision box tree leafs
            if isInBox:
                for leaf in intrsectLeafs:
                    meshres = self.getMeshInterscectionSDBTNew(ray, leaf.facets, points, fv_indices)
                    # meshres = self.getMeshInterscectionSDBTNew(ray, leaf.facets, geo.mesh)
                    if len(meshres) > 0:
                        si = SelectionInfo()
                        si.update(meshres[0], meshres[1], geo)
                        sis.append(si)

        # selected je selected geometry
        # si je SelectionInfo --> sadrzi podatke o selekciji

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

    def getMeshInterscectionSDBTNew(self, ray: dmnsn_ray, fhlist, points, fv_indices):
        infinity = float("inf")

        chosen_fv_indices = fv_indices[fhlist]
        chosen_points = points[chosen_fv_indices]

        ds = self.rayIntersectsTriangleMollerTrumboreSDBT(ray, chosen_points[:, 0], chosen_points[:, 1], chosen_points[:, 2])

        mask = ds != infinity
        intersectedFacets = fhlist[mask]
        intersectedFacetsDistances = ds[mask]

        if len(intersectedFacets) == 0:
            return []

        idx_min = np.argmin(intersectedFacetsDistances)
        result = [intersectedFacetsDistances[idx_min], intersectedFacets[idx_min]]
        return result

    def getMeshInterscectionSDBTNew_notOptimized(self, ray: dmnsn_ray, fhlist, mesh: om.TriMesh):
        result = []
        intersectedFacets = []
        intersectedFacetsDistances = []
        # Find all intersected facets
        infinity = float("inf")
        points = mesh.points().tolist()
        fv_indices = mesh.fv_indices().tolist()
        for ifh in fhlist:
            d = self.rayIntersectsTriangleMollerTrumboreSDBT(ray,
                                                             points[fv_indices[ifh][0]],
                                                             points[fv_indices[ifh][1]],
                                                             points[fv_indices[ifh][2]])
            if d != infinity:
                intersectedFacets.append(ifh)
                intersectedFacetsDistances.append(d)
        # Find the closest point
        ii = -1
        if len(intersectedFacets) > 0:
            ii = 0
        i = 1
        while i < len(intersectedFacets):
            if intersectedFacetsDistances[i] < intersectedFacetsDistances[ii]:
                ii = i
            i = i + 1
        if ii > -1:
            result.append(intersectedFacetsDistances[ii])
            result.append(intersectedFacets[ii])
        return result

    def rayIntersectsTriangleMollerTrumboreSDBT(self, ray: dmnsn_ray, v0, v1, v2):
        # https://en.wikipedia.org/wiki/Möller–Trumbore_intersection_algorithm
        # base on  Java Implementation code
        e = 0.00000001
        infinity = float("inf")
        K = ray.n.XYZ
        P0 = ray.x0.XYZ
        edge1 = np.subtract(v1, v0)
        edge2 = np.subtract(v2, v0)
        h = np.cross(K, edge2)
        a = np.sum(edge1 * h, axis=1)
        results = np.zeros(len(a))
        results[(-e < a) & (a < e)] = infinity

        f = 1.0 / a
        s = np.subtract(P0, v0)
        u = np.multiply(f, np.sum(s * h, axis=1))
        results[(u < 0.0) | (u > 1.0)] = infinity

        q = np.cross(s, edge1)
        v = f * np.sum(K * q, axis=1)
        results[(v < 0.0) | (u + v > 1.0)] = infinity

        t = np.multiply(f, np.sum(edge2 * q, axis=1))
        mask = results != infinity
        results[mask] = t[mask]
        return results

    def rayIntersectsTriangleMollerTrumboreSDBT_notOptimized(self, ray: dmnsn_ray, v0, v1, v2):
        # https://en.wikipedia.org/wiki/Möller–Trumbore_intersection_algorithm
        # base on  Java Implementation code
        e = 0.00000001
        infinity = float("inf")
        K = ray.n.XYZ
        P0 = ray.x0.XYZ
        edge1 = np.subtract(v1, v0)
        edge2 = np.subtract(v2, v0)
        h = np.cross(K, edge2)
        a = np.dot(edge1, h)

        if -e < a < e:
            return infinity  # This ray is parallel to this triangle.

        f = 1.0 / a
        s = np.subtract(P0, v0)
        u = np.multiply(f, np.dot(s, h))
        if u < 0.0 or u > 1.0:
            return infinity

        q = np.cross(s, edge1)
        v = f * np.dot(K, q)
        if v < 0.0 or u + v > 1.0:
            return infinity
        # At this stage we can compute t to find out where the intersection point is on the line.
        t = np.multiply(f, np.dot(edge2, q))
        return t
        # if t > e  and t < 1 - e:
        #    return  t
        # else:
        #    return infinity

    def getMeshInterscectionSDBT(self, ray: dmnsn_ray, fhlist, mesh: om.TriMesh):
        result = []
        intersectedFacets = []
        intersectedFacetsDistances = []
        # Find all intersected facets
        infinity = float("inf")
        coords = []
        for fh in fhlist:
            coords.clear()
            for vh in mesh.fv(fh):  # vertex handle
                p = mesh.point(vh)
                coords.append(p)
            v0 = coords[0]
            v1 = coords[1]
            v2 = coords[2]
            d = self.rayIntersectsTriangleMollerTrumboreSDBT(ray, v0, v1, v2)
            if d != infinity:
                intersectedFacets.append(fh)
                intersectedFacetsDistances.append(d)
        # Find the closest point
        ii = -1
        if len(intersectedFacets) > 0:
            ii = 0
        i = 1
        while i < len(intersectedFacets):
            if intersectedFacetsDistances[i] < intersectedFacetsDistances[ii]:
                ii = i
            i = i + 1
        if ii > -1:
            result.append(intersectedFacetsDistances[ii])
            result.append(intersectedFacets[ii])
        return result

    def getMeshInterscection(self, K, P0, mesh: om.TriMesh):
        intersectedFacets = []
        intersectedFacetsDistances = []
        # Find all intersected facets
        infinity = float("inf")
        for fh in mesh.faces():
            d = self.rayIntersectsTriangleMollerTrumbore(K, P0, fh, mesh)
            if d != infinity:
                intersectedFacets.append(fh)
                intersectedFacetsDistances.append(d)

        # Find the closest point
        result = []
        ii = -1
        if len(intersectedFacets) > 0:
            ii = 0
        i = 1
        while i < len(intersectedFacets):
            if intersectedFacetsDistances[i] < intersectedFacetsDistances[ii]:
                ii = i
            i = i + 1
        if ii > -1:
            result.append(intersectedFacetsDistances[ii])
            result.append(intersectedFacets[ii])
        return result

    def selectOld(self, los, geometry):
        if not len(geometry):
            return
        P0Q = los[0]
        KQ = los[1]
        # transform to np arrays
        K = np.array([KQ.x(), KQ.y(), KQ.z()])
        P0 = np.array([P0Q.x(), P0Q.y(), P0Q.z()])

        # geometry je lista geometrije iz koje treba izracunati selekciju
        sis = []
        for geo in geometry:
            isInBox = True
            # 1. test bounding box
            t = 99999999
            box = dmnsn_aabb()
            box.setFromBBox(geo.bbox)
            ray = dmnsn_ray(los)
            opt_ray = dmnsn_optimized_ray(ray)
            isInBox = self.dmnsn_ray_box_intersection(opt_ray, box, t)
            # 2. test mesh in geo
            if isInBox:
                meshres = self.getMeshInterscection(K, P0, geo.mesh)
                if len(meshres) > 0:
                    si = SelectionInfo()
                    si.update(meshres[0], meshres[1], geo)
                    sis.append(si)

        # selected je selected geometry
        # si je SelectionInfo --> sadrzi podatke o selekciji

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

    def rayIntersectsTriangleMollerTrumbore(self, K, P0, face: om.FaceHandle, mesh: om.TriMesh):
        # https://en.wikipedia.org/wiki/Möller–Trumbore_intersection_algorithm
        # base on  Java Implementation code
        e = 0.00000001
        infinity = float("inf")
        coords = []
        for vh in mesh.fv(face):  # vertex handle
            p = mesh.point(vh)
            coords.append(p)
        v0 = coords[0]
        v1 = coords[1]
        v2 = coords[2]

        edge1 = np.subtract(v1, v0)
        edge2 = np.subtract(v2, v0)
        h = np.cross(K, edge2)
        a = np.dot(edge1, h)

        if -e < a < e:
            return infinity  # This ray is parallel to this triangle.

        f = 1.0 / a
        s = np.subtract(P0, v0)
        u = np.multiply(f, np.dot(s, h))
        if u < 0.0 or u > 1.0:
            return infinity

        q = np.cross(s, edge1)
        v = f * np.dot(K, q)
        if v < 0.0 or u + v > 1.0:
            return infinity
        # At this stage we can compute t to find out where the intersection point is on the line.
        t = np.multiply(f, np.dot(edge2, q))
        return t
        # if t > e  and t < 1 - e:
        #    return  t
        # else:
        #    return infinity

    def dmnsn_ray_box_intersection(self, optray: dmnsn_optimized_ray, box: dmnsn_aabb, t):
        # This is actually correct, even though it appears not to handle edge cases
        # (ray.n.{x,y,z} == 0).  It works because the infinities that result from
        # dividing by zero will still behave correctly in the comparisons.  Rays
        # which are parallel to an axis and outside the box will have tmin == inf
        # or tmax == -inf, while rays inside the box will have tmin and tmax
        # unchanged.

        tx1 = (box.min.X - optray.x0.X) * optray.n_inv.X
        tx2 = (box.max.X - optray.x0.X) * optray.n_inv.X

        tmin = min(tx1, tx2)
        tmax = max(tx1, tx2)

        ty1 = (box.min.Y - optray.x0.Y) * optray.n_inv.Y
        ty2 = (box.max.Y - optray.x0.Y) * optray.n_inv.Y

        tmin = max(tmin, min(ty1, ty2))
        tmax = min(tmax, max(ty1, ty2))

        tz1 = (box.min.Z - optray.x0.Z) * optray.n_inv.Z
        tz2 = (box.max.Z - optray.x0.Z) * optray.n_inv.Z

        tmin = max(tmin, min(tz1, tz2))
        tmax = min(tmax, max(tz1, tz2))

        return tmax >= max(0.0, tmin) and tmin < t
