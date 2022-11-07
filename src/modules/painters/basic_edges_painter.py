from enum import Enum
from PySide6.QtCore import Slot
from PySide6.QtGui import QVector4D,QVector3D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from painters import Painter
from dir_basic_painter.glvertdatasforhaders import VertDataCollectorCoord3fNormal3fColor4f, VertDataCollectorCoord3fColor4f
from dir_basic_painter.glhelp import GLEntityType, GLHelpFun, GLDataType
from OpenGL import GL
from core import Geometry, geometry_manager
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from PySide6.QtGui import QActionGroup,QAction
import time
from typing import List,Dict
from dir_basic_painter.basic_painter_base import BasicPainterGeometryBase
import uuid
class BasicEdgesPainter(BasicPainterGeometryBase):

    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self.act_do_process_data.setChecked(False)
        self.act_do_paint.setChecked(False)
        self.showBack = False

        self.lineWidth = 1.0
        self._use_outline = False
        self._outline_treshold_angle = 30  # deg
        self._do_process_data = False
        self.polygonWFColor = QVector4D(0.0, 0.0, 0.0, 1.0)

        # Add menu items
        app = QApplication.instance()
        mf = app.mainFrame

        ag = QActionGroup(mf)
        self._menu.addSeparator()
        self.act_all_edges = ag.addAction(QAction('All edges', mf, checkable=True))
        self.act_all_edges.triggered.connect(self.onChangeShowEdges)
        self.act_all_edges.setChecked(True)
        self._menu.addAction(self.act_all_edges)
        self.act_outline_edges = ag.addAction(QAction('Outline edges', mf, checkable=True))
        self.act_outline_edges.triggered.connect(self.onChangeShowEdges)
        self._menu.addAction(self.act_outline_edges)
        self.onChangeShowEdges()
        self._menu.addSeparator()




    @property
    def name(self):
        return "Edges Painter"

    def onChangeShowEdges(self):
        if self.act_outline_edges.isChecked():
            self._use_outline = True
        elif self.act_all_edges.isChecked():
            self._use_outline = False
        if self.do_process_data:
            # remove all old reperesentation of geometry
            self._geoKey2Remove = list(self._dentsvertsdata.keys())
            # add new representation of all geometry data
            self._geo2Add = list(self._dgeos.values())
            self.requestGLUpdate()

    def on_change_do_process_data(self):
        if self.do_process_data:
            # add all geometry data
            self._geo2Add = list(self._dgeos.values())
        else:
            # remove all geometry
            self._geoKey2Remove = list(self._dentsvertsdata.keys())

    def initializeShaderProgram(self):
        self.program = QOpenGLShaderProgram()
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexShader)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentShader)
        self.program.link()
        self.program.bind()
        self.projMatrixLoc = self.program.uniformLocation("projMatrix")
        self.mvMatrixLoc = self.program.uniformLocation("mvMatrix")
        self.shader_edge_color = self.program.uniformLocation("edge_color")
        self.program.release()


    def basic_painter_before_paint(self):
        proj = self.paintDevice.proj
        mv = self.paintDevice.mv
        self.program.bind()
        self.program.setUniformValue(self.projMatrixLoc, proj)
        self.program.setUniformValue(self.mvMatrixLoc, mv)


    def basic_painter_paint(self):
        super().basic_painter_paint()
        self.glf.glEnable(GL.GL_DEPTH_TEST)

        for key, value in self._dentsvertsdata.items():
            if self.is_visible_geo(key):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                self.program.setUniformValue(self.shader_edge_color, self.polygonWFColor)
                value.drawvao(self.glf)

    def resizeGL(self, w: int, h: int):
        super().resizeGL(w, h)

    def _vertex_shader_source(self):
        return self._vertex_shader_wf_source()
    def _fragment_shader_source(self):
        return self._fragment_shader_wf_source()
    def _vertex_shader_wf_source(self):
        return """attribute vec4 vertex;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                uniform vec4 edge_color;
                void main() {
                   gl_Position = projMatrix * mvMatrix * vertex;
                   // colorV = color;
                }"""

    def _fragment_shader_wf_source(self):
        return """
                uniform vec4 edge_color;
                void main() {
                gl_FragColor = edge_color;
                }
               """

    # Painter methods implementation code ********************************************************

    @Slot()
    def onGeometryCreated(self, geometries:List[Geometry]):
        if self.do_process_data:
            super().onGeometryCreated(geometries)
        self.add_geometry_to_all_geo_dictionary(geometries)

    @Slot()
    def onGeometryRemoved(self, geometries:List[Geometry]):
        if self.do_process_data:
            super().onGeometryRemoved(geometries)
        self.remove_geometries_from_all_geo_dictionary(geometries)

    @Slot()
    def onGeometryStateChanging(self, visible: List[Geometry], loaded: List[Geometry], selected: List[Geometry]):
        pass

    def delayed_add_geometry_to_gl_data(self, geometry: Geometry):
        key = geometry.guid
        mesh = geometry.mesh
        self.delayed_add_mesh_edges_to_gl_data(key, mesh)

    def delayed_add_mesh_edges_to_gl_data(self, key, mesh:om.PolyMesh):
        self.initnewdictitem(key, GLEntityType.LINE)
        if self._use_outline:
            n_vertices, vertices = \
                self.get_mesh_outlines(mesh, self._outline_treshold_angle, True)
        else:
            n_vertices, vertices = self.get_mesh_edges(mesh)
        n_lines = int(n_vertices / 2)
        self.appenddictitemsize(key, n_lines)
        self.allocatememory(key)
        self.add_line_data_to_gl(key, n_vertices, vertices)
        self.bind_data(key)


    def delayed_rebuild_visible_geometry_edges(self):
        self.resetmodel()
        # generate wireframe of all loaded geometries
        for key, geometry in self._dgeos.items():
            self.delayed_add_mesh_edges_to_gl_data(geometry)


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
                self.delayed_add_geometry_to_gl_data(geometry)
            self._geo2Add.clear()

    def get_mesh_outlines(self, mesh: om.TriMesh, max_angle=20,
                          include_boundary=True):  # max angle(in deg) is the maximum angle between two faces for the edge between them to be counted as an outline,       include_boundary (bool) is wether boundary edges are considered outlines
        mesh_points = mesh.points()
        mesh.request_face_normals()
        mesh.update_normals()
        mesh_normals = mesh.face_normals()
        mesh_evi = mesh.edge_vertex_indices()
        mesh_efi = mesh.edge_face_indices()  # if mesh is not closed some efi will have -1 in them
        mesh_boundary_ei = np.where((mesh_efi == -1).any(-1))[0]
        mesh_closed_ei = np.delete(np.arange(mesh_efi.shape[0]), mesh_boundary_ei, axis=0)
        mesh_closed_efi = mesh_efi[mesh_closed_ei]
        mesh_closed_efn = mesh_normals[mesh_closed_efi]  # edge-face normals
        v1 = mesh_closed_efn[:, 0, :]
        v2 = mesh_closed_efn[:, 1, :]
        cos = np.abs(np.sum(v1 * v2, axis=1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1)))
        is_outline_edge = cos <= np.cos(max_angle / 57.3)
        outline_ei = mesh_closed_ei[is_outline_edge]
        if include_boundary == True:
            outline_ei = np.append(outline_ei, mesh_boundary_ei)
        outline_evi = mesh_evi[outline_ei]
        outline_points = mesh_points[outline_evi]
        vertices = np.array(outline_points, dtype=np.float32).flatten()
        n_vertices = len(outline_evi) * 2
        return n_vertices, vertices

    def get_mesh_edges(self, mesh):
        fv_indices = mesh.fv_indices()
        points = mesh.points()

        n_corners_max = len(fv_indices[0])

        faces_drawn = np.zeros(len(fv_indices), dtype=np.bool)
        corner_idx_array = range(2, n_corners_max)[::-1]
        line_indices = []
        for corner_idx in corner_idx_array:
            existing = fv_indices[:, corner_idx] != -1

            existing_fv_indices = fv_indices[existing & ~faces_drawn]
            existing_fv_indices = existing_fv_indices[:, 0: corner_idx + 1]
            faces_drawn = faces_drawn | existing

            fv_indices_repeated = np.repeat(existing_fv_indices, 2, axis=1)
            fv_indices_repeated[:, :-1] = fv_indices_repeated[:, 1:]
            fv_indices_repeated[:, -1] = fv_indices_repeated[:, 0]
            fv_indices_repeated = fv_indices_repeated.flatten()

            line_indices = np.concatenate([line_indices, fv_indices_repeated])

        line_indices = line_indices.astype(np.uint)
        n_vertices = len(line_indices)
        vertices = points[line_indices]
        vertices = np.array(vertices, dtype=np.float32).flatten()
        return n_vertices, vertices

class DummyPainter(Painter):
    def __init__(self):
        pass

# Create Dummy Painter to avoid painter import error for parent directory
def createPainter():
    #return DummyPainter()
    return BasicEdgesPainter()
