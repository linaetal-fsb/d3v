from enum import Enum
from PySide6.QtCore import Slot
from PySide6.QtGui import QVector4D,QVector3D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from painters import Painter
from a_painterbasic.glvertdatasforhaders import VertDataCollectorCoord3fNormal3fColor4f, VertDataCollectorCoord3fColor4f
from a_painterbasic.glhelp import GLEntityType, GLHelpFun, GLDataType
from OpenGL import GL
from core import Geometry, geometry_manager
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from PySide6.QtGui import QActionGroup,QAction
import time
from typing import List,Dict
import uuid
from a_painterbasic.basic_painter_base import BasicPainterGeometryBase
class SelModes(Enum):
    FULL_FILL = 1        # Full geometry, which is is selected, is colored in pink by a second shader
    FACET_FILL = 2     # Selected facet is colored in pink with glPolygonOffset to avoid z-fight

FACET_LIST_SEL_GUID = uuid.uuid4()
class BasicSelectionPainter(BasicPainterGeometryBase):

    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self.showBack = True

        self._doFacetListSelection = False
        self.selType = SelModes.FULL_FILL
        #self.selType = SelModes.FACET_FILL
        self.polyOffsetFactor = 1.0
        self.polyOffsetUnits = 1.0
        self.selectionColor = QVector4D(1.0, 0.0, 1.0, 1.0)

        self._last_processed_si = SelectionInfo()
        self._last_obtained_si = SelectionInfo()

        geometry_manager.selected_geometry_changed.connect(self.onSelectedGeometryChanged)
        self._s_selected_geo_guids:set = set()

        app = QApplication.instance()
        mf = app.mainFrame
        ag = QActionGroup(mf)
        self._menu.addSeparator()
        self.act_sel_mode_full_geo = ag.addAction(QAction('Geometry select', mf, checkable=True))
        self.act_sel_mode_full_geo.triggered.connect(self.onChangeSelectionMode)
        self.act_sel_mode_full_geo.setChecked(True)
        self._menu.addAction(self.act_sel_mode_full_geo)
        self.act_sel_mode_facet = ag.addAction(QAction('Facet select', mf, checkable=True))
        self.act_sel_mode_facet.triggered.connect(self.onChangeSelectionMode)
        self._menu.addAction(self.act_sel_mode_facet)
        self.onChangeSelectionMode()

    @property
    def name(self):
        return "Selection Painter"
    def onChangeSelectionMode(self):
        if self.act_sel_mode_full_geo.isChecked():
            self.selType = SelModes.FULL_FILL
        elif self.act_sel_mode_facet.isChecked():
            self.selType = SelModes.FACET_FILL
        if self.do_process_data:
            # remove all old reperesentation of geometry
            self._geoKey2Remove = list(self._dentsvertsdata.keys())
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
        # next line is specific to glwin - consider reviosion
        self.program.release()
        self.paintDevice.selector.selection_info_changled.connect(self.onSelectedInfoChanged)

    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass


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
            if self.selType == SelModes.FACET_FILL:
                if key == FACET_LIST_SEL_GUID:
                    key = self._last_processed_si.geometry.guid
            is_visible = self.is_visible_geo(key)
            is_selected_visible = is_visible and (self.is_selected_geo(key))
            if  is_selected_visible:
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                GL.glPolygonOffset(-self.polyOffsetFactor, -self.polyOffsetUnits)
                value.drawvao(self.glf)
                GL.glPolygonOffset(self.polyOffsetFactor, self.polyOffsetUnits)
                value.drawvao(self.glf)
                GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

    # Shader code ********************************************************
    def _vertex_shader_source(self):
        return self._vertex_shader_selection_source()
    def _fragment_shader_source(self):
        return self._fragment_shader_selection_source()
    def _vertex_shader_selection_source(self):
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

    def _fragment_shader_selection_source(self):
        return """varying highp vec3 vert;
                        varying highp vec3 vertNormal;
                        // varying highp vec4 colorV; 
                        uniform highp vec3 lightPos;
                        const highp vec4 selectionColor = vec4(1.0, 0.0, 1.0, 1.0);
                        void main() {
                           highp vec3 L = normalize(lightPos - vert);
                           highp float NL = max(dot(normalize(vertNormal), L), 0.0);
                           highp vec3 col = clamp(selectionColor.xyz * 0.2 + selectionColor.xyz * 0.8 * NL, 0.0, 1.0);
                           gl_FragColor = vec4(col, selectionColor.w);
                        }"""


    @Slot()
    def onSelectedInfoChanged(self, si: SelectionInfo):
        self._last_obtained_si = si
    @Slot()
    def onGeometryCreated(self, geometries:List[Geometry]):
        self.add_geometry_to_all_geo_dictionary(geometries)
    @Slot()
    def onGeometryRemoved(self, geometries:List[Geometry]):
        self.remove_geometries_from_all_geo_dictionary(geometries)

    def update_selected_geo_guids(self,selected:List[Geometry]):
        self._s_selected_geo_guids.clear()
        for g in selected:
            self._s_selected_geo_guids.add(g.guid)

    def is_selected_geo(self,guid):
        return guid in self._s_selected_geo_guids

    @Slot()
    def onSelectedGeometryChanged(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        if self.do_process_data:
            if self.selType == SelModes.FULL_FILL:
                last_selected_guids=self._s_selected_geo_guids.copy()
                self.update_selected_geo_guids(selected)
                for g in selected:
                    if not g.guid in last_selected_guids:
                        self._geo2Add.append(g)
                for key in last_selected_guids:
                    if not self.is_selected_geo(key):
                        self._geoKey2Remove.append(key)
                self.requestGLUpdate()
            elif self.selType == SelModes.FACET_FILL:
                self.update_selected_geo_guids(selected)
                self._doFacetListSelection = True
                self.requestGLUpdate()
        else:
            self.update_selected_geo_guids()

    def on_change_do_process_data(self):
        if self.do_process_data:
            # add all geometry data
            if self.selType == SelModes.FULL_FILL:
                for key,value in self._dgeos.items():
                    if key in self._s_selected_geo_guids:
                        self._geo2Add.append(value)
            elif self.selType == SelModes.FACET_FILL:
                self._doFacetListSelection = True
        else:
            #remove all geometry
            self._geoKey2Remove = list(self._dentsvertsdata.keys())

    def delayed_update_gl_data(self):
        if len(self._geoKey2Remove) > 0:
            for key in self._geoKey2Remove:
                self.delayed_remove_item_from_gl_data(key)
            self._geoKey2Remove.clear()
        # this could be improved by using the data from BasicFillPainter
        if len(self._geo2Add) > 0:
            for geometry in self._geo2Add:
                self.delayed_add_geometry_to_gl_data(geometry)
            self._geo2Add.clear()
        if self._doFacetListSelection:
            self.addFacetListSelectionDataToOGL()
            self._doFacetListSelection = False

    # Painter methods implementation code ********************************************************


    @Slot()
    def onGeometryStateChanging(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        pass


    def addFacetListSelectionDataToOGL(self):
        key = FACET_LIST_SEL_GUID
        si = self._last_obtained_si
        if not(self._last_processed_si is si):
            self._last_processed_si = si
            self.removeDictItem(key)
            if si.haveSelection():
                self.initnewdictitem(key, GLEntityType.TRIA)

                if type(si.geometry.mesh) == om.TriMesh:
                    nf = si.nFaces() * 2
                    self.appenddictitemsize(key, nf)
                    self.allocatememory(key)
                    self.addFacetListSelData4oglmdl(key, si, si.geometry)
                elif type(si.geometry.mesh) == om.PolyMesh:
                    fv_indices = si.geometry.mesh.fv_indices()
                    n_possible_triangles = fv_indices.shape[0] * (fv_indices.shape[1] - 2)
                    mask_not_triangles = fv_indices == -1
                    not_triangles = fv_indices[mask_not_triangles]
                    n_not_triangles = len(not_triangles)
                    n_triangles = n_possible_triangles - n_not_triangles

                    self.appenddictitemsize(key, n_triangles)
                    self.allocatememory(key)
                    self.addFacetListSelData4oglmdl_poly(key, si, si.geometry)
                self.bind_data(key)


    def addFacetListSelData4oglmdl(self, key, si, geometry):
        """
        Converts the vertices of the selected triangle to OpenGL data.

        :param key: key under which the selected triangle is saved.
        :param si: SelectionInfo holding the indices of the selected faces
        :param geometry: geometry holding the mesh data
        :return:
        """

        mesh = geometry.mesh

        normals = mesh.face_normals()
        points = mesh.points()
        face_indices = mesh.fv_indices()
        for fh in si.allfaces:
            vertex_indices = face_indices[fh]
            # n = mesh.normal(fh)
            n = normals[fh]
            c = [1.0, 0.0, 1.0, 1.0]
            # for vh in mesh.fv(fh):  # vertex handle
            for vh in vertex_indices:
                p = points[vh]
                # p = mesh.point(vh)
                # to compensate z-fight
                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0], p[1], p[2],
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])
            for vh in vertex_indices[::-1]:
                p = points[vh]
                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0], p[1], p[2],
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])
        return

    """ 
    Utilities for Polymesh
    """
    def addFacetListSelData4oglmdl_poly(self, key, si, geometry):
        """
        Converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL
        :param key: key under which the geometry is saved
        :param si: SelectionInfo object holding the face indices which are selected
        :param geometry: geometry holding the mesh data which is to be converted
        :return:
        """
        mesh = geometry.mesh
        normals = mesh.face_normals()
        points = mesh.points()
        fv_indices = mesh.fv_indices()
        selected_fv_indices = fv_indices[si.allfaces]
        selected_face_normals = normals[si.allfaces]
        cstype = 0
        c = [1.0, 0.0, 1.0, 1.0]

        self.add_poly_mesh_arrays_data_to_gl(key, selected_fv_indices, points, selected_face_normals, cstype, c, None, None)
        return



class DummyPainter(Painter):
    def __init__(self):
        pass

# Create Dummy Painter to avoid painter import error for parent directory
def createPainter():
    #return DummyPainter()
    return BasicSelectionPainter()