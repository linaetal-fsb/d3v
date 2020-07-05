from enum import Enum
from OpenGL import GL

import ctypes
import numpy as np


class GLEntityType(Enum):
    """!
    GLEntityType available for painting
    """
    QUAD = GL.GL_QUADS
    TRIA = GL.GL_TRIANGLES
    LINE = GL.GL_LINE
    POINT = GL.GL_POINT


class GLDataType(Enum):
    """!
    GLDataTypes available for the vertex data storing
    """
    FLOAT = GL.GL_FLOAT
    UBYTE = GL.GL_UNSIGNED_BYTE

class GLHelpFun:
    @staticmethod
    def datatypesize(GLDataType_arg):

        dtsize = 0
        if GLDataType_arg == GLDataType.FLOAT:
            dtsize = ctypes.sizeof(ctypes.c_float)
        elif GLDataType_arg == GLDataType.UBYTE:
            dtsize = ctypes.sizeof(ctypes.c_ubyte)
        return dtsize

    @staticmethod
    def numpydatatype(GLDataType_arg):

        dtype = np.dtype('f') # default
        if GLDataType_arg == GLDataType.FLOAT:
            dtype = np.dtype('f') # default
        elif GLDataType_arg == GLDataType.UBYTE:
            dtype = np.dtype('B')
        return dtype