"""!
@package pyD3VVertData
OpenGL Vertices data file documentation

More detailssssssssss
"""
from OpenGL import GL
from PySide2.QtGui import QOpenGLBuffer, QOpenGLVertexArrayObject
from shiboken2.shiboken2 import VoidPtr

from painterbasic.glhelp import GLDataType

from painterbasic.glvertdata import VertDataCollector
from painterbasic.glvertdata import VertDataSingleChannel


# class that use Coordinates and normals
class VertDataCollectorVAO(VertDataCollector):
    """!
    VertDataCollectorCoord3fColor4ub class

    Data collector class collects all vertex data necessary for drawing a group of entities that share the same type.
    Three floats are used for the position (xyz), while four ubyte are used for color (r,g,b,a)
    Possible primitive types are defined by the enum (pyD3VOGLModel.GLEntityType)
    """
    def __init__(self, enttype):
        """!
        VertDataCollectorCoord3fColor4ub constructor


        """
        super().__init__(enttype)

        self._ne = 0
        self._ivert = 0
        self._nv = 0

        self._nv4et = self._getnumver4enttype()
        self._vao = QOpenGLVertexArrayObject()
        self._dVBOs = {}  # dictionary that holds VertDataSingleChannelVBO instances

    def GetAtrList(self):
        atlist=[]
        for key, value in self._dVBOs.items():
            atlist.append(value.attproplist())
        return atlist


    def setupVertexAttribs(self,glf):
        self._vao.create()
        vaoBinder = QOpenGLVertexArrayObject.Binder(self._vao)
        # Set VBO
        for key, value in self._dVBOs.items():
            value.setupVBO(glf)
        vaoBinder = None

    def drawvao(self, glfunctions):
        vaoBinder = QOpenGLVertexArrayObject.Binder(self._vao)
        glfunctions.glDrawArrays(self.oglprimtype(), 0, self.numvertices())
        vaoBinder = None

    def appendsize(self,numents):
        """
        Append  size with the specified number of entities

        @param numents: number of entities to add
        """
        self._ne += numents
    def numvertices(self):
        return self._ne * self._nv4et
    def _appendlistdata_f3(self,key, x1, y1, z1):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        """
        self._dVBOs[key].add_Data3(x1, y1, z1)
    def _appendlistdata_f4(self,key, x1, y1, z1,w1):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        """
        self._dVBOs[key].add_Data4(x1, y1, z1,w1)

    def _allocateattribmemory(self, GLDataType_arg,attNumData, attIndex, attName):
        """!
        Allocate memory for the vertex data channels

        Allocation size is based on the information collected by client calls to appendsize()
        """
        self._nv = self._ne * self._nv4et
        self._dVBOs[attName] = VertDataSingleChannelVBO(GLDataType_arg, attNumData, self._nv, attIndex, attName)

    def _incrementVertexCounter(self):
        self._ivert += 1
        return self._ivert

    def numverts(self):
        """!
        Get total number of vertices

        @retval: (\b int)total number of vertices
        """
        return self._nv



    def free(self):
        """!
        Free vertex data channels memory


        """

        for key, value in self._dVBOs.items():
            value.free()


class VertDataCollectorCoord3fNormal3f(VertDataCollectorVAO):
    """!
    VertDataCollectorCoord3fColor4ub class

    Data collector class collects all vertex data necessary for drawing a group of entities that share the same type.
    Three floats are used for the position (xyz), while four ubyte are used for color (r,g,b,a)
    Possible primitive types are defined by the enum (pyD3VOGLModel.GLEntityType)
    """
    def __init__(self, enttype):
        """!
        VertDataCollectorCoord3fColor4ub constructor


        """
        super().__init__(enttype)

    def appendlistdata_f3xyzf3n(self, x, y, z, nx, ny, nz):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param n[0]- nx: (\b float) red chanel 0-1
        @param n[1]- ny: (\b float) green chanel 0-1
        @param n[2]- nz (\b float) blue chanel 0-1
        @retval: (\b int) index of the added vertex
        """

        self._appendlistdata_f3("vertex",x, y, z)
        self._appendlistdata_f3("normal", nx, ny, nz)
        return self._incrementVertexCounter()

    def allocatememory(self):
        """!
        Allocate memory for the vertex data channels

        Allocation size is based on the information collected by client calls to appendsize()
        """
        ndata=3 # x,y,z
        self._allocateattribmemory(GLDataType.FLOAT,ndata, 0,"vertex")
        ndata = 3  # nx,ny,nz
        self._allocateattribmemory(GLDataType.FLOAT,ndata, 1, "normal")

    def clone(self):
        """!
        Clone the instance of VertDataCollectorCoord3fColor4ub class

        Overrides the base class abstract method
        @retval: (VertDataCollectorCoord3fColor4ub) clon
        """
        vdc = VertDataCollectorCoord3fNormal3f(self._enttype)
        return vdc

class VertDataCollectorCoord3fNormal3fColor4f(VertDataCollectorVAO):
    """!
    VertDataCollectorCoord3fColor4ub class

    Data collector class collects all vertex data necessary for drawing a group of entities that share the same type.
    Three floats are used for the position (xyz), while four ubyte are used for color (r,g,b,a)
    Possible primitive types are defined by the enum (pyD3VOGLModel.GLEntityType)
    """
    def __init__(self, enttype):
        """!
        VertDataCollectorCoord3fColor4ub constructor


        """
        super().__init__(enttype)

    def appendlistdata_f3xyzf3nf4rgba(self, x, y, z, nx, ny, nz,r,g,b,a):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param n[0]- nx: (\b float) red chanel 0-1
        @param n[1]- ny: (\b float) green chanel 0-1
        @param n[2]- nz (\b float) blue chanel 0-1
        @retval: (\b int) index of the added vertex
        """

        self._appendlistdata_f3("vertex",x, y, z)
        self._appendlistdata_f3("normal", nx, ny, nz)
        self._appendlistdata_f4("color", r, g, b,a)
        return self._incrementVertexCounter()

    def appendlistdata_f3xyzf3n(self, x, y, z, nx, ny, nz):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param n[0]- nx: (\b float) red chanel 0-1
        @param n[1]- ny: (\b float) green chanel 0-1
        @param n[2]- nz (\b float) blue chanel 0-1
        @retval: (\b int) index of the added vertex
        """

        self._appendlistdata_f3("vertex",x, y, z)
        self._appendlistdata_f3("normal", nx, ny, nz)
        self._appendlistdata_f4("color", 1.0, 0.0, 0.0, 1.0)
        return self._incrementVertexCounter()

    def allocatememory(self):
        """!
        Allocate memory for the vertex data channels

        Allocation size is based on the information collected by client calls to appendsize()
        """
        ndata=3 # x,y,z
        self._allocateattribmemory(GLDataType.FLOAT,ndata, 0,"vertex")
        ndata = 3  # nx,ny,nz
        self._allocateattribmemory(GLDataType.FLOAT,ndata, 1, "normal")
        ndata = 4  # r,g,b,a
        self._allocateattribmemory(GLDataType.FLOAT, ndata, 2, "color")

    def clone(self):
        """!
        Clone the instance of VertDataCollectorCoord3fColor4ub class

        Overrides the base class abstract method
        @retval: (VertDataCollectorCoord3fColor4ub) clon
        """
        vdc = VertDataCollectorCoord3fNormal3fColor4f(self._enttype)
        return vdc

class VertDataSingleChannelVBO(VertDataSingleChannel):

    def __init__(self, dataType, nvertdata, nvert, index, name):
        """!
        OGLModelVertCordFColorUB constructor
        """
        super().__init__(dataType, nvertdata, nvert)
        self._vbo = QOpenGLBuffer()
        self._attIndex = index
        self._attName = name

    def attproplist(self):
        return [self._attName, self._attIndex]

    def deleteVBO(self):
        self._vbo.destroy()

    def setupVBO(self,glf):
        self._vbo.create()
        self._vbo.bind()
        self._vbo.allocate(self.constData(), self.memsizetotal())
        self._vbo.bind()
        glf.glEnableVertexAttribArray(self._attIndex)
        null = VoidPtr(0)
        doNormalization = int(GL.GL_FALSE)
        glf.glVertexAttribPointer(self._attIndex,
                                self.numvertdata(),
                                int(self.ogldatatype()),
                                doNormalization,
                                self.memsizeonevert(), null)
        self._vbo.release()
