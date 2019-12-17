import math
import numpy
import ctypes


class Sphere:
    def __init__(self, x, y, z, radious):
        """!
        D3VModelCtrlSimple constructor
        Calls the base class constructor
        """
        super().__init__()
        self.radius = radious
        self.subdivision = 1
        self.X = x
        self.Y = y
        self.Z = z
        self.vertices = []
        self.normals = []
        self.indices = []
        self.colors = []
        self.lineIndices = []
        self.interleavedVertices = []
        self.buildVerticesFlat()

    def getnumtria(self):
        return int(len(self.indices)/3)

    def addVertices(self, v1, v2, v3):
        self.vertices.append(v1[0])  # x
        self.vertices.append(v1[1])  # y
        self.vertices.append(v1[2])  # z
        self.vertices.append(v2[0])
        self.vertices.append(v2[1])
        self.vertices.append(v2[2])
        self.vertices.append(v3[0])
        self.vertices.append(v3[1])
        self.vertices.append(v3[2])


    @staticmethod
    def computeScaleForLength(v, length):
        return length / math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

    def computeHalfVertex(self, v1, v2, length,x,y,z, newV):
        newV[0] = v1[0] + v2[0]-2*x
        newV[1] = v1[1] + v2[1]-2*y
        newV[2] = v1[2] + v2[2]-2*z
        scale = self.computeScaleForLength(newV, length)
        newV[0] = newV[0]* scale+x
        newV[1] = newV[1]* scale+y
        newV[2] = newV[2]* scale+z

    def addSubLineIndices(self, i1, i2, i3, i4, i5, i6):
        self.lineIndices.append(i1)  # i1 - i2
        self.lineIndices.append(i2)
        self.lineIndices.append(i2)  # i2 - i6
        self.lineIndices.append(i6)
        self.lineIndices.append(i2)  # i2 - i3
        self.lineIndices.append(i3)
        self.lineIndices.append(i2)  # i2 - i4
        self.lineIndices.append(i4)
        self.lineIndices.append(i6)  # i6 - i4
        self.lineIndices.append(i4)
        self.lineIndices.append(i3)  # i3 - i4
        self.lineIndices.append(i4)
        self.lineIndices.append(i4)  # i4 - i5
        self.lineIndices.append(i5)

    def addNormal(self, nx, ny, nz):
        self.normals.append(nx)
        self.normals.append(ny)
        self.normals.append(nz)

    def addNormals(self, n1, n2, n3):
        self.normals.append(n1[0])  # nx
        self.normals.append(n1[1])  # ny
        self.normals.append(n1[2])  # nz
        self.normals.append(n2[0])
        self.normals.append(n2[1])
        self.normals.append(n2[2])
        self.normals.append(n3[0])
        self.normals.append(n3[1])
        self.normals.append(n3[2])

        # code from IcoSphere

    def addIndices(self, i1, i2, i3):
        self.indices.append(i1)
        self.indices.append(i2)
        self.indices.append(i3)

    @staticmethod
    def computeFaceNormal(v1, v2, v3):
        EPSILON = 0.000001
        n = [0, 0, 0]

        ex1 = v2[0] - v1[0]
        ey1 = v2[1] - v1[1]
        ez1 = v2[2] - v1[2]
        ex2 = v3[0] - v1[0]
        ey2 = v3[1] - v1[1]
        ez2 = v3[2] - v1[2]

        # cross product: e1 x e2
        nx = (ey1 * ez2) - (ez1 * ey2)
        ny = (ez1 * ex2) - (ex1 * ez2)
        nz = (ex1 * ey2) - (ey1 * ex2)

        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > EPSILON:
            lengthInv = 1.0 / length
            n[0] = nx * lengthInv
            n[1] = ny * lengthInv
            n[2] = nz * lengthInv
        return n

    def subdivideVerticesFlat(self):
        tmpVertices = []
        tmpIndices = []
        indexCount = 0
        newV1 = [0, 0, 0]
        newV2 = [0, 0, 0]
        newV3 = [0, 0, 0]  # new vertex positions
        normal = [0, 0, 0]
        index = 0

        for i in range(self.subdivision):
            # copy prev arrays
            tmpVertices = self.vertices.copy()
            tmpIndices = self.indices.copy()
            # clear prev arrays
            self.vertices.clear()
            self.normals.clear()
            self.indices.clear()
            self.lineIndices.clear()

            index = 0
            indexCount = len(tmpIndices)

            for j in range(0, indexCount, 3):
                # get 3 vertices of a triangle
                v1 = tmpVertices[tmpIndices[j] * 3:tmpIndices[j] * 3+3]
                v2 = tmpVertices[tmpIndices[j + 1] * 3:tmpIndices[j + 1] * 3+3]
                v3 = tmpVertices[tmpIndices[j + 2] * 3:tmpIndices[j + 2] * 3+3]

                # get 3 new vertices by spliting half on each edge
                self.computeHalfVertex(v1, v2, self.radius,self.X,self.Y,self.Z, newV1)
                self.computeHalfVertex(v2, v3, self.radius,self.X,self.Y,self.Z, newV2)
                self.computeHalfVertex(v1, v3, self.radius,self.X,self.Y,self.Z, newV3)

                # add 4 new triangles
                self.addVertices(v1, newV1, newV3)
                normal = Sphere.computeFaceNormal(v1, newV1, newV3)
                self.addNormals(normal, normal, normal)
                self.addIndices(index, index + 1, index + 2)

                self.addVertices(newV1, v2, newV2)
                normal = Sphere.computeFaceNormal(newV1, v2, newV2)
                self.addNormals(normal, normal, normal)
                self.addIndices(index + 3, index + 4, index + 5)

                self.addVertices(newV1, newV2, newV3)
                normal = Sphere.computeFaceNormal(newV1, newV2, newV3)
                self.addNormals(normal, normal, normal)
                self.addIndices(index + 6, index + 7, index + 8)

                self.addVertices(newV3, newV2, v3)
                normal = Sphere.computeFaceNormal(newV3, newV2, v3)
                self.addNormals(normal, normal, normal)
                self.addIndices(index + 9, index + 10, index + 11)

                #  add new line indices per iteration
                self.addSubLineIndices(index, index + 1, index + 4, index + 5, index + 11, index + 9)
                index += 12  # next index

    def buildInterleavedVertices(self):
        self.interleavedVertices.clear()
        count = self.vertices.count(self)
        for i in range(0, count, 3):
            self.interleavedVertices.append(self.vertices[i])
            self.interleavedVertices.append(self.vertices[i + 1])
            self.interleavedVertices.append(self.vertices[i + 2])

            self.interleavedVertices.append(self.normals[i])
            self.interleavedVertices.append(self.normals[i + 1])
            self.interleavedVertices.append(self.normals[i + 2])

    # ///////////////////////////////////////////////////////////////////////////////
    # // compute 12 vertices of icosahedron using spherical coordinates
    # // The north pole is at (0, 0, r) and the south pole is at (0,0,-r).
    # // 5 vertices are placed by rotating 72 deg at elevation 26.57 deg (=atan(1/2))
    # // 5 vertices are placed by rotating 72 deg at elevation -26.57 deg
    # ///////////////////////////////////////////////////////////////////////////////
    def computeIcosahedronVertices(self, xo, yo, zo):
        PI = math.pi
        H_ANGLE = PI / 180 * 72    # 72 degree = 360 / 5
        V_ANGLE = math.atan(1.0 / 2)  # elevation = 26.565 degree

        vertices = [0]*(12 * 3)    # 12 vertices
        hAngle1 = -PI / 2 - H_ANGLE / 2  # start from -126 deg at 2nd row
        hAngle2 = -PI / 2                # start from -90 deg at 3rd row

        # the first top vertex (0, 0, r)
        vertices[0] = 0 + xo
        vertices[0+1] = 0 + yo
        vertices[0+2] = self.radius+zo

        # 10 vertices at 2nd and 3rd rows
        for i in range(1, 6):
            i1 = i * 3         # for 2nd row
            i2 = (i + 5) * 3   # for 3rd row

            z = self.radius * math.sin(V_ANGLE)  # elevation
            xy = self.radius * math.cos(V_ANGLE)

            vertices[i1] = xy * math.cos(hAngle1) + xo  # x
            vertices[i2] = xy * math.cos(hAngle2) + xo
            vertices[i1 + 1] = xy * math.sin(hAngle1) + yo
            vertices[i2 + 1] = xy * math.sin(hAngle2) + yo
            vertices[i1 + 2] = z+zo  # z
            vertices[i2 + 2] = -z+zo

            # next horizontal angles
            hAngle1 += H_ANGLE
            hAngle2 += H_ANGLE

        # the last bottom vertex (0, 0, -r)
        i1 = 11 * 3
        vertices[i1] = 0 + xo
        vertices[i1 + 1] = 0 + yo
        vertices[i1 + 2] = -self.radius+zo



        return vertices

    def buildVerticesFlat(self):
        S_STEP = 186 / 2048.0
        T_STEP = 322 / 1024.0
        tmpVertices = self.computeIcosahedronVertices(self.X, self.Y, self.Z)
        self.vertices.clear()
        self.normals.clear()
        self.indices.clear()
        self.lineIndices.clear()
        n = [0, 0, 0]  # face normal
        index = 0
        v0 = tmpVertices[0:3]
        v11 = tmpVertices[11 * 3: 11 * 3 + 3]

        for i in range(1,6):
            v1 = tmpVertices[i * 3:i * 3 + 3]
            if i < 5:
                v2 = tmpVertices[(i + 1) * 3:(i + 1) * 3 + 3]
            else:
                v2 = tmpVertices[3: 3 + 3]

            v3 = tmpVertices[(i + 5) * 3: (i + 5) * 3 + 3]

            if (i + 5) < 10:
                v4 = tmpVertices[(i + 6) * 3:(i + 6) * 3+3]
            else:
                v4 = tmpVertices[6 * 3:6 * 3 + 3]

            # add a triangle in 1st row
            n = Sphere.computeFaceNormal(v0, v1, v2)
            self.addVertices(v0, v1, v2)
            self.addNormals(n, n, n)
            self.addIndices(index, index + 1, index + 2)

            # add 2 triangles in 2nd row
            n = Sphere.computeFaceNormal(v1, v3, v2)
            self.addVertices(v1, v3, v2)
            self.addNormals(n, n, n)
            self.addIndices(index + 3, index + 4, index + 5)

            n=Sphere.computeFaceNormal(v2, v3, v4)
            self.addVertices(v2, v3, v4)
            self.addNormals(n, n, n)
            self.addIndices(index + 6, index + 7, index + 8)

            # add a triangle in 3rd row
            n=Sphere.computeFaceNormal(v3, v11, v4)
            self.addVertices(v3, v11, v4)
            self.addNormals(n, n, n)
            self.addIndices(index + 9, index + 10, index + 11)

            self.lineIndices.append(index)  # (i, i + 1)
            self.lineIndices.append(index + 1)  # (i, i + 1)
            self.lineIndices.append(index + 3)  # (i + 3, i + 4)
            self.lineIndices.append(index + 4)
            self.lineIndices.append(index + 3)  # (i + 3, i + 5)
            self.lineIndices.append(index + 5)
            self.lineIndices.append(index + 4)  # (i + 4, i + 5)
            self.lineIndices.append(index + 5)
            self.lineIndices.append(index + 9)  # (i + 9, i + 10)
            self.lineIndices.append(index + 10)
            self.lineIndices.append(index + 9)  # (i + 9, i + 11)
            self.lineIndices.append(index + 11)

            index += 12

        self.subdivideVerticesFlat()
        self.buildInterleavedVertices()
        self.setcolor(0.39, 1.0, 1.0,1.0)
        pass
    def setcolor(self,r,g,b,a):
        nt = self.getnumtria()
        self.colors = [0.0]*nt*3*4
        for i in range(0, nt):  # interate through all of the triangles
            iimin = i * 3
            iimax = iimin + 3
            for ii in range(iimin, iimax):
                iv = self.indices[ii] * 4  # each vertex has xyz
                self.colors[iv]=r
                self.colors[iv+1] = g
                self.colors[iv+2] = b
                self.colors[iv+3] = a
            # for ii in range(iimin, iimax):
            #     iv = self.indices[ii] * 4  # each vertex has xyz
            #     self.colors[iv]=r
            #     self.colors[iv+1] = g-i/nt
            #     self.colors[iv+2] = b
            #     self.colors[iv+3] = a
        pass
