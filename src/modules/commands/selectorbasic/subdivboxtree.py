import time
import openmesh as om
import numpy as np

from bounds import BBox
from selectorbasic.raytracing import Box3DIntersection


class SubDivBoxTree(Box3DIntersection):
    def __init__(self, mesh):
        """
        SubDixBoxTree is a datastructure for 3D geometries consisting of triangles.
        The triangles (= facets) of the geometry are divided into groups.
        The amount of triangles per group is defined by _maxFacets.
        The idea is that one SubDixBoxTree is created for every geometry added to basicpainter.
        SubDixBoxTree yields a performance increase in the selection of a facet of the corresponding geometry.
        The performance increase depends on the number of facets.
        SubDixBoxTree is currently working only for triangle facets.

        :param mesh: openmesh.Trimesh. Mesh that holds all vertices and faces of the geometry
        """

        super().__init__()
        self.mesh = mesh
        self.facets = []
        self.nodes = []
        self._maxfacets = 1000
        # self._maxfacets = 2
        self.name = ""

    def getIntersectedLeafs(self, o, d, intrsectLeafs):
        if self.intersectsWithRay(o, d):
            if self.isleaf:
                intrsectLeafs.append(self)
            else:
                for node in self.nodes:
                    isInBox, intrsectLeafs = node.getIntersectedLeafs(o, d, intrsectLeafs)

        return len(intrsectLeafs) > 0, intrsectLeafs

    def createTreeRoot(self, box: BBox):
        if not self.mesh.has_face_normals():
            self.mesh.request_face_normals()
            self.mesh.update_face_normals()

        fv_indices = self.mesh.fv_indices()
        points = self.mesh.points()
        if __debug__:
            tsTR = time.perf_counter()
        self.setFromBBox(box)
        self.name = "root"
        nf = len(fv_indices)
        facets = np.array(range(nf))
        self.setFacets(facets)
        self.createTree(fv_indices, points)
        if __debug__:
            dtTR = time.perf_counter() - tsTR
            print("Tree creation time, s:", dtTR)
        # self.printTreeInfo()

    def createTree(self, fv_indices: [], points: []):
        if self.numFacets > self._maxfacets:
            self.subdivideOn2(fv_indices, points)
            for node in self.nodes:
                node.createTree(fv_indices, points)

    def subdivideOn2(self, fv_indices: [], points: []):
        # determine max deltas of bbox
        dx = self.maxCoord[0] - self.minCoord[0]
        dy = self.maxCoord[1] - self.minCoord[1]
        dz = self.maxCoord[2] - self.minCoord[2]
        dmax = max(dx, dy, dz)

        # Copy full bounding box two times and split them half
        sbox1 = self.copy()
        sbox1.name = self.name + "_1"
        sbox2 = self.copy()
        sbox2.name = self.name + "_2"
        if dx == dmax:
            sbox1.maxCoord[0] = (self.maxCoord[0] + self.minCoord[0]) * 0.5
            sbox2.minCoord[0] = sbox1.maxCoord[0]
        elif dy == dmax:
            sbox1.maxCoord[1] = (self.maxCoord[1] + self.minCoord[1]) * 0.5
            sbox2.minCoord[1] = sbox1.maxCoord[1]
        else:
            sbox1.maxCoord[2] = (self.maxCoord[2] + self.minCoord[2]) * 0.5
            sbox2.minCoord[2] = sbox1.maxCoord[2]

        if type(self.mesh) == om.TriMesh:
            fv_indices = fv_indices[self.facets]
            face_vertices = points[fv_indices]
            faceCGs = face_vertices.sum(axis=1) / 3
        else:
            fv_indices = fv_indices[self.facets]
            faceCGs = np.zeros((len(fv_indices), 3))
            n_corners_max = len(fv_indices[0])
            corners_iter = range(2, n_corners_max)
            polygons_done = np.zeros(len(fv_indices), dtype=np.bool)
            for corner_idx in corners_iter[::-1]:
                are_polygons = fv_indices[:, corner_idx] != -1
                mask = are_polygons & ~polygons_done
                iter_fv_indices = fv_indices[mask]
                iter_fv_indices = iter_fv_indices[:, :corner_idx+1]

                polygons_done = polygons_done | are_polygons

                iter_face_vertices = points[iter_fv_indices]
                iter_faceCGs = iter_face_vertices.sum(axis=1) / (corner_idx + 1)
                faceCGs[mask] = iter_faceCGs

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
        cb.setMinCoord(self.minCoord.copy())
        cb.setMaxCoord(self.maxCoord.copy())
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
