import time

import numpy as np

from bounds import BBox
from rayTracing import dmnsn_aabb


class SubDivBoxTree(dmnsn_aabb):
    def __init__(self, mesh):
        super().__init__()
        self.mesh = mesh
        self.facets = []
        self.nodes = []
        self.node_list = []
        self._maxfacets = 1000
        self.name = ""

    def getIntersectedLeafs(self, optray, t, intrsectLeafs):
        if self.dmnsn_ray_box_intersection(optray, t):
            if self.isleaf:
                intrsectLeafs.append(self)
            else:
                for node in self.nodes:
                    node.getIntersectedLeafs(optray, t, intrsectLeafs)

        return len(intrsectLeafs) > 0

    def new(self):
        cb = SubDivBoxTree(None)
        cb.min.copyFrom(self.min)
        cb.max.copyFrom(self.max)
        return cb

    def createTreeRoot(self, box: BBox):
        if not self.mesh.has_face_normals():
            self.mesh.request_face_normals()
            self.mesh.update_face_normals()

        ar_fv_indices = self.mesh.fv_indices().tolist()
        ar_points = self.mesh.points().tolist()
        self.createTreeRootList(box, ar_fv_indices, ar_points)

    def createTreeRootList(self, box: BBox, fv_indices: [], points: []):
        tsTR = time.perf_counter()
        self.setFromBBox(box)
        self.name = "root"
        nf = len(fv_indices)
        facets = np.array(range(nf))
        self.setFacets(facets)
        fv_indices = np.array(fv_indices)
        points = np.array(points)
        self.createTree(fv_indices, points)
        dtTR = time.perf_counter() - tsTR
        print("Tree creation time, s:", dtTR)
        # self.printTreeInfo()

    def createTree(self, fv_indices: [], points: []):
        if self.numFacets > self._maxfacets:
            self.subdivideOn2New(fv_indices, points)
            for node in self.nodes:
                node.createTree(fv_indices, points)

    def subdivideOn2New(self, fv_indices: [], points: []):
        # determine max deltas of bbox
        dx = self.max.X - self.min.X
        dy = self.max.Y - self.min.Y
        dz = self.max.Z - self.min.Z
        dmax = max(dx, dy, dz)

        # Copy full bounding box two times and split them half
        sbox1 = self.copy()
        sbox1.name = self.name + "_1"
        sbox2 = self.copy()
        sbox2.name = self.name + "_2"
        if dx == dmax:
            sbox1.max.X = (self.max.X + self.min.X) * 0.5
            sbox2.min.X = sbox1.max.X
        elif dy == dmax:
            sbox1.max.Y = (self.max.Y + self.min.Y) * 0.5
            sbox2.min.Y = sbox1.max.Y
        else:
            sbox1.max.Z = (self.max.Z + self.min.Z) * 0.5
            sbox2.min.Z = sbox1.max.Z

        faceCGs = self.calcAllFacetsCG(self.facets, fv_indices, points)

        isIn_sbox1 = sbox1.isIn_array(faceCGs)
        facets_sbox1 = self.facets[isIn_sbox1]
        facets_sbox2 = self.facets[~isIn_sbox1]
        sbox1.setFacets(facets_sbox1)
        sbox2.setFacets(facets_sbox2)

        # Clear the parent bounding box
        self.clearFacets()
        # If the splitted bounding box contains face, append it to nodes -> Starts over in SubDivideOn2
        if sbox1.numFacets > 0:
            self.nodes.append(sbox1)
        if sbox2.numFacets > 0:
            self.nodes.append(sbox2)

    @staticmethod
    def calcAllFacetsCG(face_indices, all_fv_indices, points):
        fv_indices = all_fv_indices[face_indices]
        face_vertices = points[fv_indices]
        faceCGs = face_vertices.sum(axis=1) / 3
        return faceCGs

    """
    Utilitiy functions
    """
    def printTreeInfo(self):
        print(self.name, end="", flush=True)
        if self.isleaf:
            print(", is leaf, ", end="", flush=True)
            print(self.numFacets, end="", flush=True)
            print(" faces.")
        else:
            print(", not leaf.")
        for node in self.nodes:
            node.printTreeInfo()

    def copy(self):
        cb = SubDivBoxTree(self.mesh)
        cb.min.copyFrom(self.min)
        cb.max.copyFrom(self.max)
        return cb

    def addFacet(self, fh):
        self.facets.append(fh)

    def setFacets(self, ifhs):
        self.facets = ifhs

    def clearFacets(self):
        self.facets = np.array([])

    @property
    def isnode(self):
        return len(self.nodes) > 0

    @property
    def isleaf(self):
        return len(self.facets) > 0

    @property
    def numFacets(self):
        return len(self.facets)
