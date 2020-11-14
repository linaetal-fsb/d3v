from enum import Enum
from PySide2.QtCore import Slot
from PySide2.QtGui import QVector4D
from PySide2.QtGui import QOpenGLShaderProgram, QOpenGLShader
from PySide2.QtGui import QOpenGLVersionProfile, QOpenGLContext
from PySide2.QtGui import QSurfaceFormat
from PySide2.QtWidgets import QMessageBox
from painters import Painter
from signals import Signals, DragInfo
from glvertdatasforhaders import VertDataCollectorCoord3fNormal3fColor4f, VertDataCollectorCoord3fColor4f
from glhelp import GLEntityType, GLHelpFun, GLDataType
from OpenGL import GL
from PySide2.QtCore import QCoreApplication
from geometry import Geometry
import openmesh as om
import numpy as np
from selinfo import SelectionInfo
from PySide2.QtGui import QBrush, QPainter, QPen, QPolygon, QColor, QFont
from PySide2.QtCore import QRect, Qt
from PySide2.QtWidgets import QApplication
import time


class SelModes(Enum):
    FULL_FILL_NEWMESH = 0       # Selected Mesh drawn fully by adding a new mesh with a new color
    FACET_WF = 1                # Selected Facet marked by wireframe using glPolygonMode
    FULL_FILL_SHADER = 2        # Full geometry, which is is selected, is colored in pink by a second shader
    FACET_FILL = 3              # Selected facet is colored in pink with a manual added offset to avoid z-fight
    FULL_WF = 4                 # Full geometry marked by pink wireframe using glPolygonMode
    FACET_FILL_GLOFFSET = 5     # Selected facet is colored in pink with glPolygonOffset to avoid z-fight


class BasicPainter(Painter):
    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self._dentsvertsdata = {}  # dictionary that holds vertex data for all primitive and  submodel combinations
        self._geo2Add = []
        self._geo2Rebuild = []
        self._geo2Remove = []
        self._doSelection = False
        self._si = SelectionInfo()
        self.program = 0
        self.projMatrixLoc = 0
        self.mvMatrixLoc = 0
        self.normalMatrixLoc = 0
        self.lightPosLoc = 0
        # self.vertexShader = self.vertexShaderSourceCore()
        # self.fragmentShader = self.fragmentShaderSourceCore()
        self.vertexShader = self.vertexShaderSource()
        self.fragmentShader = self.fragmentShaderSource()
        # model / geometry
        self.addGeoCount = 0
        Signals.get().selectionChanged.connect(self.onSelected)
        self.paintDevice = 0
        # self.selType = SelModes.FULL_FILL_NEWMESH     # Full geometry by addMeshData
        # self.selType = SelModes.FULL_FILL_SHADER      # Full geometry by shader2
        # self.selType = SelModes.FACET_FILL              # Facet by filled triangle with z-fight compensation
        self.selType = SelModes.FACET_FILL_GLOFFSET   # Facet by filled triangle with glPolygonOffset to avoid z-fight
        # self.selType = SelModes.FACET_WF              # Facet by wireframe
        # self.selType = SelModes.FULL_WF               # Full geometry by PolygonMode
        # Note: _WF selection modes are not reasonable for everything bigger than triangles, because the wireframe
        # is applied by ogl shader and all geometries are drawn as triangles
        self._showBack = False
        self._multFactor = 1
        self.showBack = True

        self.selectionProgram = 0
        self.vertexSelectionShader = self.vertexSelectionShaderSource()
        self.fragmentSelectionShader = self.fragmentSelectionShaderSource()
        self.projMatrixLoc_selection = 0
        self.mvMatrixLoc_selection = 0
        self.normalMatrixLoc_selection = 0
        self.lightPosLoc_selection = 0

        self.wireframeProgram = 0
        self.vertexWireframeShader = self.vertexWireframeShaderSource()
        self.fragmentWireframeShader = self.fragmentWireframeShaderSource()
        self.projMatrixLoc_wireframe = 0
        self.mvMatrixLoc_wireframe = 0
        self.wfColor_wireframe = 0

        self.lineWidth = 3.0
        self.polyOffsetFactor = 1.0
        self.polyOffsetUnits = 1.0

        self.selectionColor = QVector4D(1.0, 0.0, 1.0, 1.0)

        self.showModelWireframe = True
        if self.showModelWireframe:
            self.line_indices = []
            self.polygonWFColor = QVector4D(1.0, 0.0, 0.0, 1.0)

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
        paintDevice = QApplication.instance().mainFrame.glWin
        self.width = paintDevice.vport.width()
        self.height = paintDevice.vport.height()
        super().initializeGL()
        self.program = QOpenGLShaderProgram()
        # profile = QOpenGLVersionProfile()
        # profile.setVersion(2, 0)
        # context = QOpenGLContext.currentContext()
        # print("paintr init "+str(context))
        # self.glf = context.versionFunctions(profile)
        # if not self.glf:
        #     QMessageBox.critical(None, "Failed to Initialize OpenGL",
        #                          "Could not initialize OpenGL. This program requires OpenGL x.x or higher. Please check your video card drivers.")
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

        # Shader for selection
        if self.selType == SelModes.FULL_FILL_SHADER:
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

        # Shader for wireframe
        if (self.selType in [SelModes.FACET_WF, SelModes.FULL_WF, SelModes.FACET_FILL_GLOFFSET]) or self.showModelWireframe:
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

    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        self.program.bind()
        self.program.setUniformValue(self.lightPosLoc, lightpos)
        self.program.setUniformValue(self.projMatrixLoc, proj)
        self.program.setUniformValue(self.mvMatrixLoc, mv)
        self.program.setUniformValue(self.normalMatrixLoc, normalMatrix)
        self.program.release()

        if self.selType == SelModes.FULL_FILL_SHADER:
            self.selectionProgram.bind()
            self.selectionProgram.setUniformValue(self.lightPosLoc_selection, lightpos)
            self.selectionProgram.setUniformValue(self.projMatrixLoc_selection, proj)
            self.selectionProgram.setUniformValue(self.mvMatrixLoc_selection, mv)
            self.selectionProgram.setUniformValue(self.normalMatrixLoc_selection, normalMatrix)
            self.selectionProgram.release()

        if (self.selType in [SelModes.FACET_WF, SelModes.FULL_WF, SelModes.FACET_FILL_GLOFFSET]) or self.showModelWireframe:
            # GL.glLineWidth(3.0)
            self.wireframeProgram.bind()
            self.wireframeProgram.setUniformValue(self.projMatrixLoc_wireframe, proj)
            self.wireframeProgram.setUniformValue(self.mvMatrixLoc_wireframe, mv)
            self.wireframeProgram.release()

    def paintGL(self):
        super().paintGL()
        self.glf.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        self.glf.glEnable(GL.GL_DEPTH_TEST)
        self.glf.glEnable(GL.GL_CULL_FACE)
        # self.glf.glDisable(GL.GL_CULL_FACE)

        for key, value in self._dentsvertsdata.items():
            if (key == self._si.geometry._guid) and (self.selType == SelModes.FULL_FILL_SHADER):
                self.selectionProgram.bind()
                value.drawvao(self.glf)
                self.selectionProgram.release()

            elif (key == 0) and (self.selType == SelModes.FACET_WF):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

            elif (key == 0) and (self.selType == SelModes.FACET_FILL_GLOFFSET):
                GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                GL.glPolygonOffset(-self.polyOffsetFactor, -self.polyOffsetUnits)
                value.drawvao(self.glf)
                GL.glPolygonOffset(self.polyOffsetFactor, self.polyOffsetUnits)
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                # GL.glPolygonOffset(0.0, 0.0)  # not necessary?!
                GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)

            elif (key == self._si.geometry._guid) and (self.selType == SelModes.FULL_WF):
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                self.wireframeProgram.bind()
                self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.selectionColor)
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                self.program.bind()
                value.drawvao(self.glf)
                self.program.release()

            elif type(key) == str:
                if "_wf" in key:
                    self.wireframeProgram.bind()
                    self.wireframeProgram.setUniformValue(self.wfColor_wireframe, self.polygonWFColor)
                    value.drawvao(self.glf)
                    self.wireframeProgram.release()

            else:
                self.program.bind()
                value.drawvao(self.glf)
                self.program.release()

    def resizeGL(self, w: int, h: int):
        super().resizeGL(w, h)

    def updateGL(self):
        super().updateGL()
        self.updateGeometry()

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
            self._dentsvertsdata.pop(key, None)

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

    # Shader code ********************************************************
    def vertexShaderSourceCore(self):
        return """#version 150
                in vec4 vertex;
                in vec3 normal;
                out vec3 vert;
                out vec3 vertNormal;
                out vec4 colorV;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                uniform mat3 normalMatrix;
                void main() {
                   vert = vertex.xyz;
                   vertNormal = normalMatrix * normal;
                   gl_Position = projMatrix * mvMatrix * vertex;
                   colorV = color;
                }"""

    def fragmentShaderSourceCore(self):
        return """#version 150
                in highp vec3 vert;
                in highp vec3 vertNormal;
                in highp vec4 colorV; 
                out highp vec4 fragColor;
                uniform highp vec3 lightPos;
                void main() {
                   highp vec3 L = normalize(lightPos - vert);
                   highp float NL = max(dot(normalize(vertNormal), L), 0.0);
                   highp vec3 col = clamp(colorV.rgb * 0.8 + colorV.rgb * 0.2 * NL, 0.0, 1.0);
                   fragColor = vec4(col, colorV.a);
                }"""

    def vertexShaderSource(self):
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

    def fragmentShaderSource(self):
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

    def vertexSelectionShaderSource(self):
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

    def fragmentSelectionShaderSource(self):
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

    def vertexWireframeShaderSource(self):
        return """attribute vec4 vertex;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                uniform vec4 wfColor;
                void main() {
                   gl_Position = projMatrix * mvMatrix * vertex;
                   // colorV = color;
                }"""

    def fragmentWireframeShaderSource(self):
        return """
                uniform vec4 wfColor;
                void main() {
                gl_FragColor = wfColor;
                }
               """

    # Painter methods implementation code ********************************************************

    def addGeometry(self, geometry: Geometry):
        self._geo2Add.append(geometry)
        self.requestGLUpdate()

    def removeGeometry(self, geometry: Geometry):
        self._geo2Remove.append(geometry)
        self.requestGLUpdate()
        pass

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

        if self.showModelWireframe:
            self.addGeoCount = self.addGeoCount + 1
            key = str(key) + "_wf"
            self.initnewdictitem(key, GLEntityType.LINE)
            fv_indices = geometry.mesh.fv_indices()
            n_possible_lines = fv_indices.shape[0] * fv_indices.shape[1]
            mask_not_lines = fv_indices == -1
            not_lines = fv_indices[mask_not_lines]
            n_not_lines = len(not_lines)
            n_lines = n_possible_lines - n_not_lines

            self.appenddictitemsize(key, n_lines)
            self.allocatememory(key)

            self.addWFdata4oglmdl(key, geometry)

            self.bindData(key)


    def delayedRebuildGeometry(self, geometry: Geometry):
        key = geometry.guid
        self.removeDictItem(key)
        self.initnewdictitem(key, GLEntityType.TRIA)
        nf = geometry.mesh.n_faces()
        self.appenddictitemsize(key, nf)
        self.allocatememory(key)
        self.addMeshdata4oglmdl(key, geometry)
        self.bindData(key)

    def delayedRemoveGeometry(self, geometry: Geometry):
        key = geometry.guid
        self.removeDictItem(key)

    def addSelection(self):
        if (self.selType == 0) or (self.selType == 2):
            pass
        else:
            key = 0
            self.removeDictItem(key)
            if self._si.haveSelection():
                self.initnewdictitem(key, GLEntityType.TRIA)

                if type(self._si.geometry.mesh) == om.TriMesh:
                    nf = self._si.nFaces() * 2
                    self.appenddictitemsize(key, nf)
                    self.allocatememory(key)

                    if self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL_GLOFFSET]:
                        self.addSelData4oglmdl(key, self._si, self._si.geometry)
                    elif self.selType == SelModes.FACET_FILL:
                        self.addSelData4oglmdl_withOffset(key, self._si, self._si.geometry)
                    else:
                        raise Exception("Unhandled Selection Type!")

                elif type(self._si.geometry.mesh) == om.PolyMesh:
                    fv_indices = self._si.geometry.mesh.fv_indices()
                    n_possible_triangles = fv_indices.shape[0] * (fv_indices.shape[1] - 2)
                    mask_not_triangles = fv_indices == -1
                    not_triangles = fv_indices[mask_not_triangles]
                    n_not_triangles = len(not_triangles)
                    n_triangles = n_possible_triangles - n_not_triangles

                    if self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL_GLOFFSET]:
                        self.appenddictitemsize(key, n_triangles)
                        self.allocatememory(key)
                        self.addSelData4oglmdl_poly(key, self._si, self._si.geometry)
                    elif self.selType == SelModes.FACET_FILL:
                        self.appenddictitemsize(key, n_triangles * 2)
                        self.allocatememory(key)
                        self.addSelData4oglmdl_withOffset_poly(key, self._si, self._si.geometry)
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
        if self._doSelection:
            self.addSelection()
            self._doSelection = False

    def addSelData4oglmdl_withOffset(self, key, si, geometry):
        """
        Converts the vertices of the selected triangle to OpenGL data. Adds an offset to the vertex position to
        compensate z-fight.

        :param key: key under which the selected triangle is saved.
        :param si: SelectionInfo holding the indices of the selected faces
        :param geometry: geometry holding the mesh data
        :return:
        """
        mesh = geometry.mesh
        normals = mesh.face_normals().tolist()
        points = mesh.points().tolist()
        face_indices = mesh.fv_indices().tolist()
        for fh in si.allfaces:
            n = normals[fh]
            c = [1.0, 0.0, 1.0, 1.0]
            for vh in face_indices[fh]:
                p = points[vh]
                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0] + n[0] / 100, p[1] + n[1] / 100, p[2] + n[2] / 100,
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])
            for vh in face_indices[fh]:
                p = points[vh]
                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0] - n[0] / 100, p[1] - n[1] / 100, p[2] - n[2] / 100,
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])
        return

    def addSelData4oglmdl(self, key, si, geometry):
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

    def addMeshdata4oglmdl(self, key, geometry):
        """
        Converts the mesh data of a geometry to the vertex data necessary for OpenGL.

        :param key: key under which the geometry is saved
        :param geometry: geometry which mesh data is to be converted
        :return:
        """
        tsAMD = time.perf_counter()
        mesh = geometry.mesh

        # color data
        cstype = 0  # color source type
        if self.selType == SelModes.FULL_FILL_NEWMESH:
            if self._si.geometry.guid == geometry.guid:
                c = [1.0, 0.0, 1.0, 1.0]
            else:
                c = [0.4, 1.0, 1.0, 1.0]  # default color
        elif mesh.has_face_colors():
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

        dtAMD = time.perf_counter() - tsAMD
        print("Add mesh data total:", dtAMD)
        return

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

    @Slot()
    def onSelected(self, si: SelectionInfo):
        if self.selType == SelModes.FULL_FILL_NEWMESH:  # whole geometry selection
            if self._si.haveSelection() and si.haveSelection():
                if self._si.geometry._guid != si.geometry._guid:
                    self._geo2Remove.append(si.geometry)
                    self._geo2Remove.append(self._si.geometry)
                    self._geo2Add.append(self._si.geometry)
                    self._geo2Add.append(si.geometry)
                    self.requestGLUpdate()

            elif si.haveSelection():
                self._geo2Remove.append(si.geometry)
                self._geo2Add.append(si.geometry)
                self.requestGLUpdate()

            elif self._si.haveSelection():
                self._geo2Remove.append(self._si.geometry)
                self._geo2Add.append(self._si.geometry)
                self.requestGLUpdate()

            self._si = si

        elif self.selType in [SelModes.FACET_WF, SelModes.FACET_FILL, SelModes.FACET_FILL_GLOFFSET]:
            self._doSelection = True
            self._si = si
            self.requestGLUpdate()

        elif self.selType in [SelModes.FULL_FILL_SHADER, SelModes.FULL_WF]:
            self._si = si

        pass

    """ 
    Utilities for Polymesh
    """
    def addSelData4oglmdl_poly(self, key, si, geometry):
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

    def addWFdata4oglmdl(self, key, geometry):
        """
        Converts the mesh data of a geometry to the wireframe vertex data necessary for OpenGL.
        :param key: key under which the geometry is saved
        :param geometry: geometry holding the mesh which is to be converted
        :return:
        """
        mesh = geometry.mesh
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
        normals = np.array([])
        colors = np.array([])

        self.setlistdata_f3xyzf3nf4rgba(key, vertices, normals, colors)
        self.setVertexCounter_byNum(key, n_vertices)

        print("BP")

    def addMeshdata4oglmdl_poly(self, key, geometry):
        """
        Converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL
        :param key: key under which the geometry is saved
        :param geometry: geometry holding the mesh data which is to be converted
        :return:
        """
        tsAMD = time.perf_counter()
        mesh = geometry.mesh

        # color data
        cstype = 0  # color source type
        c = None
        ar_face_colors = None
        ar_vertex_colors = None
        if self.selType == SelModes.FULL_FILL_NEWMESH:
            if self._si.geometry.guid == geometry.guid:
                c = [1.0, 0.0, 1.0, 1.0]
            else:
                c = [0.4, 1.0, 1.0, 1.0]  # default color
        elif mesh.has_face_colors():
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

    def addSelData4oglmdl_withOffset_poly(self, key, si, geometry):
        """
        Creates a flattened array holding the vertex data necessary for OpenGL. An offset is added to each polygon. The offset is equal to corresponding normal divided by 100
        :param key: key under which the geometry is saved
        :param si: SelectionInfo object holding the face indices which are selected
        :param geometry: geometry holding the mesh data which is converted
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

        self.addArrays4oglmdl_withOffset_poly(key, selected_fv_indices, points, selected_face_normals, cstype, c, None, None)
        return

    def addArrays4oglmdl_withOffset_poly(self, key, fv_indices, points, face_normals, cstype, c, face_colors, vertex_colors):
        """
        Utility function which converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL. An offset is added to each vertex. The offset is equal to the corresponding normal divided by 100
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

        data_mesh_points_list = []
        data_mesh_normals_list = []
        data_mesh_colors_list = []
        n_all_vertices = 0
        for corner_idx in range(1, n_vertices_max - 1):
            existing_triangles = fv_indices[:, corner_idx + 1] != -1

            if True not in existing_triangles:
                continue

            fv_indices_to_draw_all_vertices = fv_indices[existing_triangles]
            fv_indices_to_draw = fv_indices_to_draw_all_vertices[:, [0, corner_idx, corner_idx + 1]]

            n_faces = len(fv_indices_to_draw_all_vertices)

            fv_indices_flattened = fv_indices_to_draw.flatten()
            mesh_points = points[fv_indices_flattened]
            data_mesh_points = mesh_points.flatten()

            n_all_vertices += len(fv_indices_flattened)

            face_normals_to_draw = face_normals[existing_triangles]
            data_mesh_normals = self.createNormaldata(face_normals_to_draw)

            if cstype == 0:
                data_mesh_colors = self.createConstantColorData(c, n_faces)
            elif cstype == 1:
                data_mesh_colors = self.createFaceColorData(face_colors)
            elif cstype == 2:
                data_mesh_colors = self.createVertexColorData(vertex_colors, fv_indices_flattened)

            data_mesh_points1 = data_mesh_points + data_mesh_normals / 100
            data_mesh_points2 = data_mesh_points - data_mesh_normals / 100
            data_mesh_points = np.concatenate([data_mesh_points1, data_mesh_points2])

            data_mesh_normals = np.concatenate([data_mesh_normals, data_mesh_normals])

            data_mesh_colors = np.concatenate([data_mesh_colors, data_mesh_colors])

            if self._showBack:
                fv_indices_flattened_reversed = fv_indices_flattened[::-1]
                n_all_vertices += len(fv_indices_flattened_reversed)

                reversed_mesh_points = self.createVertexData(fv_indices_flattened_reversed, points)

                reversed_normals = -face_normals_to_draw[::-1]
                reversed_normals = self.createNormaldata(reversed_normals)

                if cstype == 0:
                    reversed_mesh_colors = data_mesh_colors
                elif cstype == 1:
                    reversed_mesh_colors = self.createFaceColorData(face_colors[::-1])
                elif cstype == 2:
                    reversed_mesh_colors = self.createVertexColorData(vertex_colors, fv_indices_flattened_reversed)

                reversed_mesh_points1 = reversed_mesh_points + reversed_normals / 100
                reversed_mesh_points2 = reversed_mesh_points - reversed_normals / 100
                reversed_mesh_points = np.concatenate([reversed_mesh_points1, reversed_mesh_points2])

                reversed_normals = np.concatenate([reversed_normals, reversed_normals])

                reversed_mesh_colors = np.concatenate([reversed_mesh_colors, reversed_mesh_colors])

                data_mesh_points = np.concatenate([data_mesh_points, reversed_mesh_points])
                data_mesh_normals = np.concatenate([data_mesh_normals, reversed_normals])
                data_mesh_colors = np.concatenate([data_mesh_colors, reversed_mesh_colors])

            data_mesh_points_list.append(data_mesh_points)
            data_mesh_normals_list.append(data_mesh_normals)
            data_mesh_colors_list.append(data_mesh_colors)

        data_mesh_points_list = np.concatenate([*data_mesh_points_list])
        data_mesh_normals_list = np.concatenate([*data_mesh_normals_list])
        data_mesh_colors_list = np.concatenate([*data_mesh_colors_list])

        vertex_data = np.array(data_mesh_points_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        normal_data = np.array(data_mesh_normals_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))
        color_data = np.array(data_mesh_colors_list, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        self.setlistdata_f3xyzf3nf4rgba(key, vertex_data, normal_data, color_data)
        self.setVertexCounter_byNum(key, n_all_vertices)
        return

