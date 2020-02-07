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
        if not len(geometry):
            return
        P0Q= los[0]
        KQ=los[1]
        # transform to np arrays
        K = np.array([KQ.x(), KQ.y(), KQ.z()])
        P0 = np.array([P0Q.x(), P0Q.y(), P0Q.z()])
        
        # geometry je lista geometrije iz koje treba izracunati selekciju
        sis=[]
        for geo in geometry:
            isInBox=True
            #1. test bounding box
            #2. test mesh in geo
            if  isInBox:
                meshres = self.getMeshInterscection(K, P0,geo.mesh)
                if len(meshres) > 0:
                    si = SelectionInfo()
                    si.update(meshres[0], meshres[1], geo)
                    sis.append(si)

        # selected je selected geometry
        # si je SelectionInfo --> sadrzi podatke o selekciji

        if len(sis) > 0:
            si = sis[0]
            i=1
            while i < len(sis):
                if  sis[i].getDistance() < si.getDistance():
                    si=sis[i]
            # nakon sto je selekcija odradjena
            # fill in sve podatke u SelectionInfo object
            # selected je selekcionirana geometrija
            selected = si.getGeometry()
            selected.onSelected(si)

        else:
            selected= None
            si = SelectionInfo()
        # obavijesti sve zainteresirane da je selekcija promijenjena
        Signals.get().selectionChanged.emit(si)

    def getMeshInterscection(self,K, P0,mesh:om.TriMesh):
        result = []
        intersectedFacets = []
        intersectedFacetsDistances = []
        # Find all intersected facets
        infinity = float("inf")
        for fh in mesh.faces():
            d= self.rayIntersectsTriangleMollerTrumbore(K, P0,fh,mesh)
            if d != infinity:
                intersectedFacets.append(fh)
                intersectedFacetsDistances.append(d)
        # Find the closest point
        ii=-1
        if  len(intersectedFacets) > 0:
            ii=0
        i=1
        while i < len(intersectedFacets):
            if  intersectedFacetsDistances[i] < intersectedFacetsDistances[ii]:
                ii=i
            i=i+1
        if ii > -1:
            result.append(intersectedFacetsDistances[ii])
            result.append(intersectedFacets[ii])
        return result

    def rayIntersectsTriangleMollerTrumbore(self, K, P0, face: om.FaceHandle,mesh:om.TriMesh):
        #https://en.wikipedia.org/wiki/Möller–Trumbore_intersection_algorithm
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
        a = np.dot(edge1,h)

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
        t = np.multiply(f,np.dot(edge2, q))
        return  t
        #if t > e  and t < 1 - e:
        #    return  t
        #else:
        #    return infinity