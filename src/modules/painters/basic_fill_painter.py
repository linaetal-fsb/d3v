from enum import Enum
from PySide6.QtCore import Slot
from PySide6.QtGui import QVector4D,QVector3D,QColor
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from painters import Painter
from a_painterbasic.glvertdatasforhaders import VertDataCollectorCoord3fNormal3fColor4f, VertDataCollectorCoord3fColor4f
from a_painterbasic.glhelp import GLEntityType, GLHelpFun, GLDataType
from OpenGL import GL
from core import Geometry, geometry_manager
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox,QColorDialog
from PySide6.QtGui import QActionGroup,QAction
import time
from typing import List,Dict
import uuid
from a_painterbasic.basic_painter_base import BasicPainterGeometryBase
key_show_face = 'show_face'
class BasicFillPainter(BasicPainterGeometryBase):
    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self.showBack = True
        self._geos_fill_preference ={}

    @property
    def name(self):
        return "Fill Painter"

    def on_action_set_color(self):
        super().on_action_set_color()
        self.on_change_do_process_data()
        self.requestGLUpdate()

    def initializeShaderProgram(self):
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexShader)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentShader)
        self.program.link()
        self.program.bind()
        self.projMatrixLoc = self.program.uniformLocation("projMatrix")
        self.mvMatrixLoc = self.program.uniformLocation("mvMatrix")
        self.normalMatrixLoc = self.program.uniformLocation("normalMatrix")
        self.lightPosLoc = self.program.uniformLocation("lightPos")
        self.glf.initializeOpenGLFunctions()  # might not been necessary
        self.program.release()


    def basic_painter_before_paint(self):
        proj = self.paintDevice.proj
        mv = self.paintDevice.mv
        normalMatrix = mv.normalMatrix()
        self.program.bind()
        self.program.setUniformValue(self.lightPosLoc, self._light_position)
        self.program.setUniformValue(self.projMatrixLoc, proj)
        self.program.setUniformValue(self.mvMatrixLoc, mv)
        self.program.setUniformValue(self.normalMatrixLoc, normalMatrix)


    def basic_painter_paint(self):
        super().basic_painter_paint()
        self.glf.glEnable(GL.GL_DEPTH_TEST)
        self.glf.glEnable(GL.GL_CULL_FACE)
        # self.glf.glDisable(GL.GL_CULL_FACE)
        for key, value in self._dentsvertsdata.items():
            if self.is_visible_geo(key):
                    GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                    value.drawvao(self.glf)


    # Shader code ********************************************************
    def _vertex_shader_source(self):
        return """attribute vec4 vertex;
                attribute vec3 normal;
                attribute vec4 color;
                varying vec3 vert;
                varying vec3 vertNormal;
                varying vec4 colorV;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                uniform mat3 normalMatrix;
                void main() {
                   vert = vertex.xyz;
                   vertNormal = normalMatrix * normal;
                   gl_Position = projMatrix * mvMatrix * vertex;
                   colorV = color;
                }"""

    def _fragment_shader_source(self):
        return """varying highp vec3 vert;
                varying highp vec3 vertNormal;
                varying highp vec4 colorV; 
                uniform highp vec3 lightPos;
                void main() {
                   highp vec3 L = normalize(lightPos - vert);
                   highp float NL = max(dot(normalize(vertNormal), L), 0.0);
                   highp vec3 col = clamp(colorV.rgb * 0.2 + colorV.rgb * 0.8 * NL, 0.0, 1.0);
                   gl_FragColor = vec4(col, colorV.a);
                }"""

    # Painter methods implementation code ********************************************************

    @Slot()
    def onGeometryStateChanging(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        pass

    @Slot()
    def onGeometryCreated(self, geometries:List[Geometry]):
        self.determine_geos_fill_preference(geometries)
        if self.do_process_data:
            super().onGeometryCreated(geometries)
        self.add_geometry_to_all_geo_dictionary(geometries)


    @Slot()
    def onGeometryRemoved(self, geometries:List[Geometry]):
        if self.do_process_data:
            super().onGeometryRemoved(geometries)
        self.remove_geometries_from_all_geo_dictionary(geometries)
        self.remove_items_from_geos_fill_preference(geometries)

    def on_change_do_process_data(self):
        if self.do_process_data:
            # add all geometry data
            self._geo2Add = list(self._dgeos.values())
        else:
            #remove all geometry
            self._geoKey2Remove = list(self._dentsvertsdata.keys())

    def delayed_update_gl_data(self):
        if len(self._geoKey2Remove) > 0:
            for key in self._geoKey2Remove:
                self.delayed_remove_item_from_gl_data(key)
            self._geoKey2Remove.clear()
        if len(self._geo2Add) > 0:
            for geometry in self._geo2Add:
                if self.get_geo_fill_pref(geometry.guid):
                    self.delayed_add_geometry_to_gl_data(geometry)
            self._geo2Add.clear()

    def get_geo_fill_pref(self, key):
        return  self._geos_fill_preference.get(key, True)
    def set_geo_fill_pref(self, key, value):
        self._geos_fill_preference[key] = bool(value)
    def determine_geos_fill_preference(self, geometries:List[Geometry]):
        for g in geometries:
            use_fill= True
            try:
                use_fill= g.attributes[key_show_face]
            except:
                pass
            self.set_geo_fill_pref(g.guid, use_fill)
    def remove_items_from_geos_fill_preference(self, geometries:List[Geometry]):
        for g in geometries:
            self._geos_fill_preference.pop(g.guid)

class DummyPainter(Painter):
    def __init__(self):
        pass

# Create Dummy Painter to avoid painter import error for parent directory
def createPainter():
    #return DummyPainter()
    return BasicFillPainter()