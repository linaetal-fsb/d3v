"""!
@package pyD3VVertData
OpenGL Vertices data file documentation

More detailssssssssss
"""
import numpy as np

from painterbasic.glhelp import GLEntityType, GLDataType, GLHelpFun

class VertDataCollector():
    """!
    VertDataCollector class  - base class

    Data collector class collects all vertex data necessary for drawing a group of entities that share the same type.
    Possible primitive types are defined by the enum (pyD3VOGLModel.GLEntityType)
    """
    def __init__(self, enttype):
        """!
        VertDataCollector constructor


        """
        self._enttype = enttype

    def oglprimtype(self):
        """!
        Get OpenGL primitive type

        @retval: (\b int)OpenGL primitive type constant
        """
        return self._enttype.value
    def _getnumver4enttype(self):
        """!
        Get number of vertices for the entity type (pyD3VOGLModel.GLEntityType)

        @retval: (\b int)  number of vertices for the entity type
        """
        if self._enttype == GLEntityType.QUAD:
            return 4
        elif self._enttype == GLEntityType.TRIA:
            return 3
        elif self._enttype == GLEntityType.LINE:
            return 2
        else:
            return 1

    def clone(self):
        """!
        Clone the instance

        Must be implemented in the derived class
        """
        return None

    def appendsize(self,numents):
        """
        Append  size with the specified number of entities

        @param numents: number of entities to add
        """
        pass

    def appendlistdata_f3xyzf3rgb(self, x, y, z, r, g, b):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param r: (\b float) red chanel 0-1
        @param g: (\b float) green chanel 0-1
        @param b: (\b float) blue chanel 0-1
        @retval: (\b int) index of the added vertex
        """
        pass

    def allocatememory(self):
        """!
        Allocate memory for the vertex data channels

        Allocation size is based on the information collected by client calls to appendsize()
        """
        pass

    def free(self):
        """!
        Free vertex data channels memory


        """
        pass


# class that use Coordinates and colors
class VertDataCollectorCoord3fColor4ub(VertDataCollector):
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
        self._cords = 0
        self._colors = 0
        self._nvet = self._getnumver4enttype()
        self._numents = 0
        self._ivert = -1
        self._numvertstotal = 0

    def appendsize(self, numents):
        """
        Append  size with the specified number of entities

        @param numents: number of entities to add
        """
        self._numents += numents

    def appendlistdata_f3xyzf3rgb(self, x, y, z, r, g, b):
        """!
        Append Vertex collector dictionary item with new vertex data

        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param r: (\b float) red chanel 0-1
        @param g: (\b float) green chanel 0-1
        @param b: (\b float) blue chanel 0-1
        @retval: (\b int) index of the added vertex
        """
        self._ivert += 1
        self._cords.add_Data3(x, y, z)
        self._colors.add_Data4(r*255, g*255, b*255, 255)
        return self._ivert

    def allocatememory(self):
        """!
        Allocate memory for the vertex data channels

        Allocation size is based on the information collected by client calls to appendsize()
        """
        self._numvertstotal = self._numents * self._nvet
        self._cords = VertDataSingleChannel(GLDataType.FLOAT, 3, self._numvertstotal)
        self._colors = VertDataSingleChannel(GLDataType.UBYTE, 4, self._numvertstotal)

    def numverts(self):
        """!
        Get total number of vertices

        @retval: (\b int)total number of vertices
        """
        return self._numvertstotal


    def free(self):
        """!
        Free vertex data channels memory


        """
        self._cords.free()
        self._colors.free()


    def clone(self):
        """!
        Clone the instance of VertDataCollectorCoord3fColor4ub class

        Overrides the base class abstract method
        @retval: (VertDataCollectorCoord3fColor4ub) clon
        """
        vdc = VertDataCollectorCoord3fColor4ub(self._enttype)
        return vdc



class VertDataSingleChannel():
    """!
    VertDataSingleChannel class

    Vertex data class that saves the single vertex channel (e.g. position or color) using the specifed data type
    Possible data types are defined by the enum (GLDataType)
    Size of the memory is determined in the constructor.
    """
    def __init__(self, dataType, nvertdata, nvert):
        """
        VertDataSingleChannel constructor


        @param dataType: (GLDataType) data type
        @param nvertdata: number of data for each vertex
        @param nvert:  number of vertices
        """
        self._i = 0
        self.m_data = 0
        self._nd4v = nvertdata
        self._nv = nvert
        self._datatype = dataType
        self._dtsize =GLHelpFun.datatypesize(self._datatype)
        self.m_data = np.empty(self._nv * self._nd4v, dtype= GLHelpFun.numpydatatype(dataType))

    def constData(self):
        return self.m_data.tobytes()

    def ogldatatype(self):
        return self._datatype.value

    def count(self):
        return self._i

    def free(self):
        self.m_data=None

    def numvertdata(self):
        return self._nd4v

    def numverts(self):
        return self._nv

    def datatypesize(self):
        return  self._dtsize

    def memsizetotal(self):
        return self.count()*self._dtsize

    def memsizeonevert(self):
        return self._nd4v * self._dtsize

    def vertexCount(self):
        return self.count() / self._nd4v

    def add_QVector3D(self, v):
        self.m_data[self._i] = v.x()
        self._i += 1
        self.m_data[self._i] = v.y()
        self._i += 1
        self.m_data[self._i] = v.z()
        self._i += 1

    def add_Data3(self, d1, d2, d3):
        self.m_data[self._i] = d1
        self._i += 1
        self.m_data[self._i] = d2
        self._i += 1
        self.m_data[self._i] = d3
        self._i += 1

    def add_Data4(self, d1, d2, d3, d4):
        self.m_data[self._i] = d1
        self._i += 1
        self.m_data[self._i] = d2
        self._i += 1
        self.m_data[self._i] = d3
        self._i += 1
        self.m_data[self._i] = d4
        self._i += 1



