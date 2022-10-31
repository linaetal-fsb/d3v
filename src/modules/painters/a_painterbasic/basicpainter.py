from enum import Enum
from PySide6.QtCore import Slot
from PySide6.QtGui import QVector4D,QVector3D
from PySide6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader
from PySide6.QtOpenGL import QOpenGLVersionProfile
from PySide6.QtGui import QSurfaceFormat, QOpenGLContext
from PySide6.QtWidgets import QMessageBox
from painters import Painter
from signals import Signals, DragInfo
from a_painterbasic.glvertdatasforhaders import VertDataCollectorCoord3fNormal3fColor4f, VertDataCollectorCoord3fColor4f
from a_painterbasic.glhelp import GLEntityType, GLHelpFun, GLDataType
from OpenGL import GL
from PySide6.QtCore import QCoreApplication
from core import Geometry, geometry_manager
import selection
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide6.QtGui import QBrush, QPainter, QPen, QPolygon, QColor, QFont
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
from PySide6.QtGui import QActionGroup,QAction
import time
from typing import List,Dict
import uuid

class SelModes(Enum):
    FACET_WF = 1                # Selected Facet marked by wireframe using glPolygonMode
    FULL_FILL_SHADER = 2        # Full geometry, which is is selected, is colored in pink by a second shader
    FULL_WF = 4                 # Full geometry marked by pink wireframe using glPolygonMode
    FACET_FILL_GLOFFSET = 5     # Selected facet is colored in pink with glPolygonOffset to avoid z-fight

FACET_LIST_SEL_GUID = uuid.uuid4()
class BasicPainter(Painter):

    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self._dentsvertsdata = {}  # dictionary that holds vertex data for all primitive and  submodel combinations
        self._dgeos = {}  # dictionary that holds existing geometries
        self._geo2Add:List[Geometry] = []
        self._geo2Rebuild:List[Geometry] = []
        self._geo2Remove:List[Geometry] = []
        self._doFacetListSelection = False
        self.program = 0
        self.projMatrixLoc = 0
        self.mvMatrixLoc = 0
        self.normalMatrixLoc = 0
        self.lightPosLoc = 0
        self.vertexShader = self._vertex_shader_source()
        self.fragmentShader = self._fragment_shader_source()
        # model / geometry
        self.addGeoCount = 0

        geometry_manager.geometry_created.connect(self.onGeometryCreated)
        geometry_manager.geometry_removed.connect(self.onGeometryRemoved)
        geometry_manager.geometry_state_changing.connect(self.onGeometryStateChanging)
        geometry_manager.visible_geometry_changed.connect(self.onVisibleGeometryChanged)
        geometry_manager.selected_geometry_changed.connect(self.onSelectedGeometryChanged)


        self.paintDevice = 0 # this will actually glWin during initializeGL
        self.selType = SelModes.FULL_FILL_SHADER
        #self.selType = SelModes.FACET_FILL_GLOFFSET

        # Note: _WF selection modes are not reasonable for everything bigger than triangles, because the wireframe
        # is applied by ogl shader and all geometries are drawn as triangles
        self._showBack = False
        self._multFactor = 1
        self.showBack = True

        self.selectionProgram = 0
        self.vertexSelectionShader = self._vertex_shader_selection_source()
        self.fragmentSelectionShader = self._fragment_shader_selection_source()
        self.projMatrixLoc_selection = 0
        self.mvMatrixLoc_selection = 0
        self.normalMatrixLoc_selection = 0
        self.lightPosLoc_selection = 0

        self.wireframeProgram = 0
        self.vertexWireframeShader = self._vertex_shader_wf_source()
        self.fragmentWireframeShader = self._fragment_shader_wf_source()
        self.projMatrixLoc_wireframe = 0
        self.mvMatrixLoc_wireframe = 0
        self.wfColor_wireframe = 0

        self.lineWidth = 1.0
        self.polyOffsetFactor = 1.0
        self.polyOffsetUnits = 1.0

        self.selectionColor = QVector4D(1.0, 0.0, 1.0, 1.0)
        self._use_wf_outline = False
        self._wf_outline_treshold_angle = 30 #deg
        self._show_wf = False
        self.polygonWFColor = QVector4D(0.0, 0.0, 0.0, 1.0)

        self._s_selected_geo_guids:set = set()
        self._s_visible_geo_guids: set = set()
        self._last_processed_si = SelectionInfo()
        self._last_obtained_si = SelectionInfo()
        # Add menu items
        app = QApplication.instance()
        mf = app.mainFrame
        tools = app.mainFrame.menuTools
        menu = QMenu("Basic Painter", app.mainFrame)
        ag = QActionGroup(mf)

        self.act_no_edges = ag.addAction(QAction('Without edges', mf, checkable=True))
        self.act_no_edges.triggered.connect(self.onChangeShowEdges)
        self.act_no_edges.setChecked(True)
        menu.addAction(self.act_no_edges)
        self.act_all_edges = ag.addAction(QAction('All edges', mf, checkable=True))
        self.act_all_edges.triggered.connect(self.onChangeShowEdges)
        #self.act_all_edges.setChecked(True)
        menu.addAction(self.act_all_edges)
        self.act_outline_edges = ag.addAction(QAction('Outline edges', mf, checkable=True))
        self.act_outline_edges.triggered.connect(self.onChangeShowEdges)
        menu.addAction(self.act_outline_edges)
        self.onChangeShowEdges()
        self._executeWireframeUpdate = False
        tools.addMenu(menu)
        menu.addSeparator()
        self._light_position = QVector3D(0, 0, 10000) #inifinity


    def onChangeShowEdges(self):
        if self.act_outline_edges.isChecked():
            self._show_wf=True
            self._use_wf_outline = True
        elif self.act_all_edges.isChecked():
            self._show_wf=True
            self._use_wf_outline = False
        else:
            self._show_wf = False
            self._use_wf_outline = False
        self._executeWireframeUpdate = True
        self.requestGLUpdate()

    @property
    def showBack(self):
        return self._showBack

    @showBack.setter
    def showBack(self, newShowBack):
        self._showBack = newShowBack
        self._multFactor = 1
        if self._showBack:
            self._multFactor = 2

    def initializeGL(self):
        self.paintDevice = QApplication.instance().mainFrame.glWin
        # next line is specific to glwin - consider reviosion
        self.paintDevice.selector.selection_info_changled.connect(self.onSelectedInfoChanged)
        self.width = self.paintDevice.vport.width()
        self.height = self.paintDevice.vport.height()
        super().initializeGL()
        self.initializeShaderProgram()
        self.initializeShaderProgramWf()
        self.initializeShaderProgramSelection()



    def initializeShaderProgram(self):
        self.program = QOpenGLShaderProgram()
        self.glf.initializeOpenGLFunctions()
        self.glf.glClearColor(0.0, 0.0, 0.0, 1)
        self.program.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexShader)
        self.program.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentShader)
        self.program.link()
        self.program.bind()
        self.projMatrixLoc = self.program.uniformLocation("projMatrix")
        self.mvMatrixLoc = self.program.uniformLocation("mvMatrix")
        self.normalMatrixLoc = self.program.uniformLocation("normalMatrix")
        self.lightPosLoc = self.program.uniformLocation("lightPos")
        self.program.release()

    def initializeShaderProgramWf(self):
        # Shader for wireframe
        #if (self.selType in [SelModes.FACET_WF, SelModes.FULL_WF, SelModes.FACET_FILL_GLOFFSET]) or self._show_wf:
        self.wireframeProgram = QOpenGLShaderProgram()
        self.wireframeProgram.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexWireframeShader)
        self.wireframeProgram.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentWireframeShader)
        self.wireframeProgram.link()
        self.wireframeProgram.bind()
        self.projMatrixLoc_wireframe = self.wireframeProgram.uniformLocation("projMatrix")
        self.mvMatrixLoc_wireframe = self.wireframeProgram.uniformLocation("mvMatrix")
        self.wfColor_wireframe = self.wireframeProgram.uniformLocation("wfColor")
        self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
        self.wireframeProgram.release()
        GL.glLineWidth(self.lineWidth)

    def initializeShaderProgramSelection(self):
        # Shader for full fil selection
        self.selectionProgram = QOpenGLShaderProgram()
        self.selectionProgram.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexSelectionShader)
        self.selectionProgram.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentSelectionShader)
        self.selectionProgram.link()
        self.selectionProgram.bind()
        self.projMatrixLoc_selection = self.selectionProgram.uniformLocation("projMatrix")
        self.mvMatrixLoc_selection = self.selectionProgram.uniformLocation("mvMatrix")
        self.normalMatrixLoc_selection = self.selectionProgram.uniformLocation("normalMatrix")
        self.lightPosLoc_selection = self.selectionProgram.uniformLocation("lightPos")
        self.selectionProgram.release()

    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass


    def set_shader_program_values(self):
        proj = self.paintDevice.proj
        mv = self.paintDevice.mv
        normalMatrix = mv.normalMatrix()
        self.program.bind()
        self.program.setUniformValue(self.lightPosLoc, self._light_position)
        self.program.setUniformValue(self.projMatrixLoc, proj)
        self.program.setUniformValue(self.mvMatrixLoc, mv)
        self.program.setUniformValue(self.normalMatrixLoc, normalMatrix)
        self.program.release()

    def set_shader_wf_program_values(self):
        proj = self.paintDevice.proj
        mv = self.paintDevice.mv
        self.wireframeProgram.bind()
        self.wireframeProgram.setUniformValue(self.projMatrixLoc_wireframe, proj)
        self.wireframeProgram.setUniformValue(self.mvMatrixLoc_wireframe, mv)
        self.wireframeProgram.release()

    def set_shader_selection_program_values(self):
        proj = self.paintDevice.proj
        mv = self.paintDevice.mv
        normalMatrix = mv.normalMatrix()
        self.selectionProgram.bind()
        self.selectionProgram.setUniformValue(self.lightPosLoc_selection, self._light_position)
        self.selectionProgram.setUniformValue(self.projMatrixLoc_selection, proj)
        self.selectionProgram.setUniformValue(self.mvMatrixLoc_selection, mv)
        self.selectionProgram.setUniformValue(self.normalMatrixLoc_selection, normalMatrix)
        self.selectionProgram.release()

    def paintGL(self):
        self.set_shader_program_values()
        self.set_shader_selection_program_values()
        self.set_shader_wf_program_values()
        super().paintGL()
        self.glf.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self.glf.glEnable(GL.GL_DEPTH_TEST)
        self.glf.glEnable(GL.GL_CULL_FACE)
        # self.glf.glDisable(GL.GL_CULL_FACE)

        for key, value in self._dentsvertsdata.items():
            is_visible = self.is_visible_geo(key)
            is_selected_visible = is_visible and (self.is_selected_geo(key))
            if  is_selected_visible and (self.selType == SelModes.FULL_FILL_SHADER):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                self.selectionProgram.bind()
                value.drawvao(self.glf)
                self.selectionProgram.release()
            elif is_selected_visible and (self.selType == SelModes.FULL_WF):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                self.program.bind()
                value.drawvao(self.glf)
                self.program.release()
            elif (key == FACET_LIST_SEL_GUID) and (self.selType == SelModes.FACET_WF):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                value.drawvao(self.glf)
                self.wireframeProgram.release()

            elif (key == FACET_LIST_SEL_GUID) and (self.selType == SelModes.FACET_FILL_GLOFFSET):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                GL.glPolygonOffset(-self.polyOffsetFactor, -self.polyOffsetUnits)
                value.drawvao(self.glf)
                GL.glPolygonOffset(self.polyOffsetFactor, self.polyOffsetUnits)
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

            if is_visible:
                if type(key) == str:
                    if "_wf" in key:
                        GL.glPolygonMode(GL.GL_FRONT_AND_BACK,GL.GL_LINE)
                        self.wireframeProgram.bind()
                        self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.polygonWFColor)
                        value.drawvao(self.glf)
                        self.wireframeProgram.release()
                else:
                    GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                    self.program.bind()
                    value.drawvao(self.glf)
                    self.program.release()

    def resizeGL(self, w: int, h: int):
        super().resizeGL(w, h)

    def updateGL(self):
        '''
        This function is called when the correct GL context is active
        All changes of OpengGL VAO-s have to be called from this method
        :return:
        '''
        super().updateGL()
        self.updateGeometry()
        if self._executeWireframeUpdate:
            self.delayedRebuildVisibleGeometryWireframe()
            self._executeWireframeUpdate = False

    def resetmodel(self):
        """!
        Reset the model

        Cleans the dictionary
        """
        for key, value in self._dentsvertsdata.items():
            value.free()
        self._dentsvertsdata.clear()

    def removeDictItem(self, key):
        """!
        Reset the item

        Cleans the dictionary
        """
        if key in self._dentsvertsdata:
            self._dentsvertsdata[key].free()
            del self._dentsvertsdata[key]

    def removeGeometryItem(self, key):
        if key in self._dgeos:
            del self._dgeos[key]

    def addGeometryItem(self, geometry:Geometry):
        self._dgeos[geometry.guid] = geometry

    def initnewdictitem(self, key, enttype):
        """!
        Initialize a new dictionary item that holds data for rendering
        @param key: (\b str) item key
        @param enttype: (GLEntityType) primitive drawing entity type
        @retval None
        """

        self._dentsvertsdata[key] = VertDataCollectorCoord3fNormal3fColor4f(enttype)

    def initnewdictitem_withoutN(self, key, enttype):
        self._dentsvertsdata[key] = VertDataCollectorCoord3fColor4f(enttype)

    def appendlistdata_f3xyzf3nf4rgba(self, key, x, y, z, nx, ny, nz, r, g, b, a):
        """!
        Append Vertex collector dictionary item with new vertex data
        @param key: (\b str) dictonary key
        @param x: (\b float) x coordinate
        @param y: (\b float) y coordinate
        @param z: (\b float) z coordinate
        @param nx: (\b float) x normal coordinate
        @param ny: (\b float) y normal coordinate
        @param nz: (\b float) z normal coordinate
        @retval: (\b int) index of the added vertex
        """
        return self._dentsvertsdata[key].appendlistdata_f3xyzf3nf4rgba(x, y, z, nx, ny, nz, r, g, b, a)

    def setlistdata_f3xyzf3nf4rgba(self, key, vertex_data, normal_data, color_data):
        """
        Sets the vertex, normal and color data to VAO object
        :param key: geometry key to which the vertex, normal and color data belongs
        :param vertex_data: vertex coordinates as flattened array
        :param normal_data: normal coordinates as flattened array
        :param color_data: rgba values of each vertex as flattened array
        :return:
        """
        self._dentsvertsdata[key].setlistdata_f3xyzf3nf4rgba(vertex_data, normal_data, color_data)

    def setVertexCounter(self, key, n_faces):
        """
        Set the amount of vertices to VAO object
        :param key: geometry key
        :param n_faces: Amount of faces of corresponding geometry
        :return:
        """
        if self._showBack:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3 * 2)
        else:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3)

    def setVertexCounter_byNum(self, key, num_vertices):
        self._dentsvertsdata[key].setVertexCounter(num_vertices)

    def appenddictitemsize(self, key, numents):
        """!
        Append dictionary item size with the specified number of entities
        :@param key:(str) key
        :@param numents:(\b int) number of entities to be added
        """
        self._dentsvertsdata[key].appendsize(numents * self._multFactor)

    def allocatememory(self):
        """!
        Allocate memory for all dictionary items that holds data for rendering

        Allocation size is based on the information collected by client calls to appenddictitemsize()
        """

        for key, value in self._dentsvertsdata.items():
            value.allocatememory()

    def allocatememory(self, key):
        """!
        Allocate memory for all dictionary items that holds data for rendering

        Allocation size is based on the information collected by client calls to appenddictitemsize()
        """
        self._dentsvertsdata[key].allocatememory()

    def bindData(self, key):
        self._dentsvertsdata[key].setupVertexAttribs(self.glf)
        atrList = self._dentsvertsdata[key].GetAtrList()
        for ent in atrList:
            self.program.bindAttributeLocation(ent[0], ent[1])

    def bindWireframeData(self, key):
        self._dentsvertsdata[key].setupVertexAttribs(self.glf)
        atrList = self._dentsvertsdata[key].GetAtrList()
        for ent in atrList:
            self.wireframeProgram.bindAttributeLocation(ent[0], ent[1])

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

    def _vertex_shader_wf_source(self):
        return """attribute vec4 vertex;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                uniform vec4 wfColor;
                void main() {
                   gl_Position = projMatrix * mvMatrix * vertex;
                   // colorV = color;
                }"""

    def _fragment_shader_wf_source(self):
        return """
                uniform vec4 wfColor;
                void main() {
                gl_FragColor = wfColor;
                }
               """

    # region selection logic implementation
    def update_selected_geo_guids(self,selected:List[Geometry]):
        self._s_selected_geo_guids.clear()
        for g in selected:
            self._s_selected_geo_guids.add(g.guid)

    def is_selected_geo(self,guid):
        return guid in self._s_selected_geo_guids

    def is_visible_geo(self,guid):
        return guid in self._s_visible_geo_guids

    @Slot()
    def onSelectedInfoChanged(self, si: SelectionInfo):
        self._last_obtained_si = si

    @Slot()
    def onSelectedGeometryChanged(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        self.update_selected_geo_guids(selected)
        if self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL_GLOFFSET]:
            self._doFacetListSelection = True
            self.requestGLUpdate()


    # Painter methods implementation code ********************************************************


    @Slot()
    def onGeometryCreated(self, geometries:List[Geometry]):
        self._geo2Add.extend(geometries)
        self.requestGLUpdate()

    @Slot()
    def onGeometryRemoved(self, geometries:List[Geometry]):
        self._geo2Remove.extend(geometries)
        self.requestGLUpdate()

    @Slot()
    def onGeometryStateChanging(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        pass

    @Slot()
    def onVisibleGeometryChanged(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        self._s_visible_geo_guids.clear()
        for g in visible:
            self._s_visible_geo_guids.add(g.guid)
            if self._show_wf:
                self._s_visible_geo_guids.add(str(g.guid) + "_wf")

    def rebuildGeometry(self, geometry: Geometry):
        self._geo2Rebuild.append(geometry)
        self.requestGLUpdate()
        pass

    def delayedAddGeometry(self, geometry: Geometry):
        # tsAG = time.perf_counter()
        self.addGeoCount = self.addGeoCount + 1
        key = geometry.guid
        # self.resetmodel()
        self.initnewdictitem(key, GLEntityType.TRIA)
        self.addGeometryItem(geometry)

        if type(geometry.mesh) == om.TriMesh:
            print("TriMesh")
            n_triangles = geometry.mesh.n_faces()

            self.appenddictitemsize(key, n_triangles)
            self.allocatememory(key)
            self.addMeshdata4oglmdl(key, geometry)

        elif type(geometry.mesh) == om.PolyMesh:
            print("PolyMesh")
            fv_indices = geometry.mesh.fv_indices()
            n_possible_triangles = fv_indices.shape[0] * (fv_indices.shape[1] - 2)
            mask_not_triangles = fv_indices == -1
            not_triangles = fv_indices[mask_not_triangles]
            n_not_triangles = len(not_triangles)
            n_triangles = n_possible_triangles - n_not_triangles
            self.appenddictitemsize(key, n_triangles)
            self.allocatememory(key)
            self.addMeshdata4oglmdl_poly(key, geometry)

        else:
            print("Not handled mesh type")
        self.bindData(key)

        self.delayedAddGeometryWireframeEntities(geometry)

    def delayedAddGeometryWireframeEntities(self, geometry: Geometry):
        if not self._show_wf:
            return
        self.addGeoCount = self.addGeoCount + 1
        key = str(geometry.guid) + "_wf"
        self.initnewdictitem(key, GLEntityType.LINE)
        if self._use_wf_outline:
            n_vertices, vertices = \
                self.get_mesh_outlines(geometry.mesh, self._wf_outline_treshold_angle, True)
        else:
            n_vertices, vertices = self.get_mesh_edges(geometry.mesh)
        n_lines = int(n_vertices / 2)
        self.appenddictitemsize(key, n_lines)
        self.allocatememory(key)
        self.addWFdata4oglmdl(key, n_vertices, vertices)
        self.bindWireframeData(key)

    def is_wf_key(self,key):
        if type(key) == str:
            return "_wf" in key
        return False

    def delayedRebuildVisibleGeometryWireframe(self):
        # remove all existing wireframes
        keys = list(self._dentsvertsdata.keys())
        for key in keys:
            if self.is_wf_key(key):
                self.processRemoveGeometry(key)
        # generate wireframe of all loaded geometries
        if self._show_wf:
            for key,geometry in self._dgeos.items():
                self.delayedAddGeometryWireframeEntities(geometry)
            # set visibility based on visible geometries
            for key,geometry in self._dgeos.items():
                self._s_visible_geo_guids.add(str(key) + "_wf")
            pass

    def delayedRebuildGeometry(self, geometry: Geometry):
        self.delayedRemoveGeometry(geometry)
        self.delayedAddGeometry(geometry)

    def processRemoveGeometry(self,key):
        self.removeDictItem(key)
        self._s_visible_geo_guids.remove(key)
        self.removeGeometryItem(key)

    def delayedRemoveGeometry(self, geometry: Geometry):
        key = geometry.guid
        self.processRemoveGeometry(key)
        if self._show_wf:
            key = str(key) + "_wf"
            self.processRemoveGeometry(key)

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

                    if self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL_GLOFFSET]:
                        self.addFacetListSelData4oglmdl(key, si, si.geometry)
                    else:
                        raise Exception("Unhandled Selection Type!")

                elif type(si.geometry.mesh) == om.PolyMesh:
                    fv_indices = si.geometry.mesh.fv_indices()
                    n_possible_triangles = fv_indices.shape[0] * (fv_indices.shape[1] - 2)
                    mask_not_triangles = fv_indices == -1
                    not_triangles = fv_indices[mask_not_triangles]
                    n_not_triangles = len(not_triangles)
                    n_triangles = n_possible_triangles - n_not_triangles

                    if self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL_GLOFFSET]:
                        self.appenddictitemsize(key, n_triangles)
                        self.allocatememory(key)
                        self.addFacetListSelData4oglmdl_poly(key, si, si.geometry)
                    else:
                        raise Exception("Unhandled Selection Type!")
                self.bindData(key)

    def updateGeometry(self):
        if len(self._geo2Remove) > 0:
            for geometry in self._geo2Remove:
                self.delayedRemoveGeometry(geometry)
            self._geo2Remove.clear()
        if len(self._geo2Add) > 0:
            for geometry in self._geo2Add:
                self.delayedAddGeometry(geometry)
            self._geo2Add.clear()
        if len(self._geo2Rebuild) > 0:
            for geometry in self._geo2Rebuild:
                self.delayedRebuildGeometry(geometry)
            self._geo2Rebuild.clear()
        if self._doFacetListSelection:
            self.addFacetListSelectionDataToOGL()
            self._doFacetListSelection = False



    def createVertexData(self, fv_indices_flattened, points):
        """
        Creates a flattened array holding the coordinates x, y, and z, of all vertices
        :param fv_indices_flattened: flattened face-vertex indices
        :param points: coordinates x, y, and z, of all vertices
        :return:
        """
        mesh_points = points[fv_indices_flattened]
        data_mesh_points = mesh_points.flatten()

        return data_mesh_points

    def createNormaldata(self, face_normals_to_draw):
        """
        Creates a flattened array holding the normals for each vertex
        :param face_normals_to_draw: array holding normals of each face
        :return:
        """
        mesh_normals = np.repeat(face_normals_to_draw, 3, axis=0)
        data_mesh_normals = mesh_normals.flatten()

        return data_mesh_normals

    def createConstantColorData(self, c, n_faces):
        """
        Creates a flattened array holding the rgba color of each vertex
        :param c: color which is assigned to each vertex
        :param n_faces: amount of faces
        :return:
        """
        mesh_colors = np.tile(c, 3 * n_faces)
        data_mesh_colors = mesh_colors.flatten()
        return data_mesh_colors

    def createFaceColorData(self, face_colors):
        """
        Create a flattened array holding the rgba color of each vertex
        :param face_colors: array with shape (n, 4), holding the color of each face, where n is the amount of faces
        :return:
        """
        mesh_colors = np.repeat(face_colors, 3, axis=0)
        data_mesh_colors = mesh_colors.flatten()
        return data_mesh_colors

    def createVertexColorData(self, vertex_colors, fv_indices_flattened):
        """
        Creates a flattened array holding the rgba color of each vertex
        :param vertex_colors: array holding the colors of all vertices
        :param fv_indices_flattened: array holding the indices of the vertices for which the color array is created
        :return:
        """
        return vertex_colors[fv_indices_flattened]

    def addMeshdata4oglmdl(self, key, geometry):
        """
        Converts the mesh data of a geometry to the vertex data necessary for OpenGL.

        :param key: key under which the geometry is saved
        :param geometry: geometry which mesh data is to be converted
        :return:
        """
        if __debug__:
            tsAMD = time.perf_counter()
        mesh = geometry.mesh

        # color data
        cstype = 0  # color source type
        if mesh.has_face_colors():
            ar_face_colors = mesh.face_colors()
            cstype = 1
        elif mesh.has_vertex_colors():
            ar_vertex_colors = mesh.vertex_colors()
            cstype = 2
        else:
            c = [0.4, 1.0, 1.0, 1.0]  # default color

        # normals data
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals()

        n_faces = mesh.n_faces()

        fv_indices_np = mesh.fv_indices()
        face_normals_np = mesh.face_normals()
        ar_points = mesh.points()

        fv_indices_flattened = fv_indices_np.flatten()

        data_mesh_points = self.createVertexData(fv_indices_flattened, ar_points)

        data_mesh_normals = self.createNormaldata(face_normals_np)

        if cstype == 0:
            data_mesh_colors = self.createConstantColorData(c, n_faces)
        elif cstype == 1:
            data_mesh_colors = self.createFaceColorData(ar_face_colors)
        elif cstype == 2:
            # Vertex colors has not been tested and is only implemented from context.
            # --> Errors can occur.
            data_mesh_colors = self.createVertexColorData(ar_vertex_colors, fv_indices_flattened)

        if self._showBack:
            fv_indices_flattened_reversed = fv_indices_flattened[::-1]

            reversed_mesh_points = ar_points[fv_indices_flattened_reversed]
            reversed_mesh_points = reversed_mesh_points.flatten()

            reversed_normals = -face_normals_np[::-1]
            reversed_normals = np.repeat(reversed_normals, 3, axis=0)
            reversed_normals = reversed_normals.flatten()

            if cstype == 0:
                reversed_mesh_colors = data_mesh_colors
            elif cstype == 1:
                reversed_mesh_colors = ar_face_colors[::-1]
                reversed_mesh_colors = np.repeat(reversed_mesh_colors, 3, axis=0)
                reversed_mesh_colors = reversed_mesh_colors.flatten()
            elif cstype == 2:
                reversed_mesh_colors = ar_vertex_colors[fv_indices_flattened_reversed]
                reversed_mesh_colors = reversed_mesh_colors.flatten()

            data_mesh_points = np.concatenate([data_mesh_points, reversed_mesh_points])
            data_mesh_normals = np.concatenate([data_mesh_normals, reversed_normals])
            data_mesh_colors = np.concatenate([data_mesh_colors, reversed_mesh_colors])

        vertex_data = np.array(data_mesh_points, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        normal_data = np.array(data_mesh_normals, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        color_data = np.array(data_mesh_colors, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        self.setlistdata_f3xyzf3nf4rgba(key, vertex_data, normal_data, color_data)
        self.setVertexCounter(key, n_faces)
        if __debug__:
            dtAMD = time.perf_counter() - tsAMD
            print("Add mesh data total:", dtAMD)
        return

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

        self.addArrays4oglmdl_poly(key, selected_fv_indices, points, selected_face_normals, cstype, c, None, None)
        return

    def addWFdata4oglmdl(self, key,n_vertices, vertices):
        '''
        Add wireframe data for OpenGL model
        :param key: based on geometry guid
        :param n_vertices: number of vertices
        :param vertices: vertices (coordinates)
        :return:
        '''
        normals = np.array([])
        colors = np.array([])
        if n_vertices > 0:
            self.setlistdata_f3xyzf3nf4rgba(key, vertices, normals, colors)
            self.setVertexCounter_byNum(key, n_vertices)

    def addMeshdata4oglmdl_poly(self, key, geometry):
        """
        Converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL
        :param key: key under which the geometry is saved
        :param geometry: geometry holding the mesh data which is to be converted
        :return:
        """
        if __debug__:
            tsAMD = time.perf_counter()
        mesh = geometry.mesh

        # color data
        cstype = 0  # color source type
        c = None
        ar_face_colors = None
        ar_vertex_colors = None
        if mesh.has_face_colors():
            ar_face_colors = mesh.face_colors()
            cstype = 1
        elif mesh.has_vertex_colors():
            ar_vertex_colors = mesh.vertex_colors()
            cstype = 2
        else:
            c = [0.4, 1.0, 1.0, 1.0]  # default color

        # normals data
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals()

        fv_indices_np = mesh.fv_indices()
        face_normals_np = mesh.face_normals()
        ar_points = mesh.points()

        self.addArrays4oglmdl_poly(key, fv_indices_np, ar_points, face_normals_np, cstype, c, ar_face_colors, ar_vertex_colors)

        if __debug__:
            dtAMD = time.perf_counter() - tsAMD
            print("Add mesh data total:", dtAMD)
        return

    def addArrays4oglmdl_poly(self, key, fv_indices, points, face_normals, cstype, c, face_colors, vertex_colors):
        """
        Utility function which converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL
        :param key: key under which the geometry is saved
        :param fv_indices: face-vertex indices which are drawn in OpenGL
        :param points: array holding the coordinates x, y, and z, of all vertices
        :param face_normals: array holding the normal of each face
        :param cstype: integer variable which indicates how the vertices are colored. 0 assigns constant color for all vertices. 1 assign individual color for each face. 2 assigns individual color for each vertex
        :param c: color for all vertices if cstype = 0
        :param face_colors: array holding the color of each face if cstype = 1
        :param vertex_colors: array holding the color of each vertex if cstype = 2
        :return:
        """
        n_vertices_max = len(fv_indices[0])

        data_mesh_points_list = np.array([])
        data_mesh_normals_list = np.array([])
        data_mesh_colors_list = np.array([])
        n_all_vertices = 0

        max_iter = n_vertices_max - 1

        for corner_idx in range(1, max_iter):
            if n_vertices_max > 3:
                existing_triangles = fv_indices[:, corner_idx + 1] != -1

                if True not in existing_triangles:
                    continue

                fv_indices_to_draw_all_vertices = fv_indices[existing_triangles]
                fv_indices_to_draw = fv_indices_to_draw_all_vertices[:, [0, corner_idx, corner_idx + 1]]
                face_normals_to_draw = face_normals[existing_triangles]
            else:
                fv_indices_to_draw = fv_indices
                face_normals_to_draw = face_normals

            fv_indices_flattened = fv_indices_to_draw.flatten()
            n_all_vertices += len(fv_indices_flattened)

            n_faces = len(fv_indices_to_draw)

            vertexData = self.createVertexData(fv_indices_flattened, points)

            normalData = self.createNormaldata(face_normals_to_draw)

            if cstype == 0:
                colorData = self.createConstantColorData(c, n_faces)
            elif cstype == 1:
                colorData = self.createFaceColorData(face_colors)
            elif cstype == 2:
                colorData = self.createVertexColorData(vertex_colors, fv_indices_flattened)

            if self._showBack:
                fv_indices_flattened_reversed = fv_indices_flattened[::-1]
                n_all_vertices += len(fv_indices_flattened_reversed)

                reversed_mesh_points = self.createVertexData(fv_indices_flattened_reversed, points)

                reversed_normals = self.createNormaldata(-face_normals_to_draw[::-1])

                if cstype == 0:
                    reversed_colors = colorData
                elif cstype == 1:
                    reversed_colors = self.createFaceColorData(face_colors[::-1])
                elif cstype == 2:
                    reversed_colors = self.createVertexColorData(vertex_colors, fv_indices_flattened_reversed)

                data_mesh_points_list = np.concatenate([data_mesh_points_list, vertexData, reversed_mesh_points])
                data_mesh_normals_list = np.concatenate([data_mesh_normals_list, normalData, reversed_normals])
                data_mesh_colors_list = np.concatenate([data_mesh_colors_list, colorData, reversed_colors])
            else:
                data_mesh_points_list = np.concatenate([data_mesh_points_list, vertexData])
                data_mesh_normals_list = np.concatenate([data_mesh_normals_list, normalData])
                data_mesh_colors_list = np.concatenate([data_mesh_colors_list, colorData])

        vertex_data = np.array(data_mesh_points_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        normal_data = np.array(data_mesh_normals_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        color_data = np.array(data_mesh_colors_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        self.setlistdata_f3xyzf3nf4rgba(key, vertex_data, normal_data, color_data)
        self.setVertexCounter_byNum(key, n_all_vertices)
        return
    def get_mesh_outlines(self, mesh:om.TriMesh, max_angle=20,include_boundary=True):  # max angle(in deg) is the maximum angle between two faces for the edge between them to be counted as an outline,       include_boundary (bool) is wether boundary edges are considered outlines
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
        is_outline_edge = cos <= np.cos(max_angle/57.3)
        outline_ei = mesh_closed_ei[is_outline_edge]
        if include_boundary == True:
            outline_ei = np.append(outline_ei, mesh_boundary_ei)
        outline_evi = mesh_evi[outline_ei]
        outline_points = mesh_points[outline_evi]
        vertices = np.array(outline_points, dtype=np.float32).flatten()
        n_vertices=len(outline_evi)*2
        return n_vertices,vertices

    def get_mesh_edges(self,mesh):
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
        return n_vertices,vertices
