from enum import Enum
from PySide2.QtCore import Slot
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
import os
import time
# from multiprocessing.pool import Pool
from multiprocessing import Pool, Process, Manager, Queue, Array
import multiprocessing


class SelModes(Enum):
    FULL_FILL_NEWMESH = 0  # Selected Mesh drawn fully by adding a new mesh with a new color
    FACET_WF = 1    # Facet by wireframe using glPolygonMode
    FULL_FILL_SHADER = 2   # Full geometry drawn fully in pink by second shader
    FACET_FILL = 3     # improve with glOffset
    FULL_WF = 4    # Full geometry by wireframe by glPolygonMode
    FACET_FILL_GLOFFSET = 5


class BasicPainter(Painter):
    def __init__(self):
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
        # self.selType = SelModes.FULL_FILL_NEWMESH  # 0 - full geometry by addMeshData
        # self.selType = SelModes.FACET_WF  # 1 - facet by wireframe
        # self.selType = SelModes.FULL_FILL_SHADER # 2 - full geometry by shader2
        # self.selType = SelModes.FACET_FILL  # Facet by filled triangle with z-fight compensation
        self.selType = SelModes.FULL_WF  # Full geometry by PolygonMode
        # self.selType = SelModes.FACET_FILL_GLOFFSET
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

        self.lineWidth = 3.0
        self.polyOffsetFactor = 1.0
        self.polyOffsetUnits = 1.0

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
        if self.selType in [SelModes.FACET_WF, SelModes.FULL_WF, SelModes.FACET_FILL_GLOFFSET]:
            self.wireframeProgram = QOpenGLShaderProgram()
            self.wireframeProgram.addShaderFromSourceCode(QOpenGLShader.Vertex, self.vertexWireframeShader)
            self.wireframeProgram.addShaderFromSourceCode(QOpenGLShader.Fragment, self.fragmentWireframeShader)
            self.wireframeProgram.link()
            self.wireframeProgram.bind()
            self.projMatrixLoc_wireframe = self.wireframeProgram.uniformLocation("projMatrix")
            self.mvMatrixLoc_wireframe = self.wireframeProgram.uniformLocation("mvMatrix")
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

        if self.selType in [SelModes.FACET_WF, SelModes.FULL_WF, SelModes.FACET_FILL_GLOFFSET]:
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
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)

            elif (key == 0) and (self.selType == SelModes.FACET_FILL_GLOFFSET):
                GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
                self.wireframeProgram.bind()
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
                value.drawvao(self.glf)
                self.wireframeProgram.release()
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
                self.program.bind()
                value.drawvao(self.glf)
                self.program.release()

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

    def appendlistdata_f3xyzf4rgba(self, key, x, y, z, r, g, b, a):
        return self._dentsvertsdata[key].appendlistdata_f3xyzf4rgba(x, y, z, r, g, b, a)

    def setlistdata_f3xyzf3nf4rgba(self, key, vertex_data, normal_data, color_data):
        self._dentsvertsdata[key].setlistdata_f3xyzf3nf4rgba(vertex_data, normal_data, color_data)

    def setVertexCounter(self, key, n_faces):
        if self._showBack:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3 * 2)
        else:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3)

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
                attribute vec3 normal;
                attribute vec4 color;
                varying vec3 vert;
                varying vec3 vertNormal;
                varying vec4 colorV;
                uniform mat4 projMatrix;
                uniform mat4 mvMatrix;
                void main() {
                   // vert: necessary that edges of triangle show up at all
                   vert = vertex.xyz;
                   // vertNormal: necessary that edges of triangle appear in the correct coloring
                   vertNormal = normal;
                   // vertNormal = vec3(1.0, 1.0, 1.0);
                   gl_Position = projMatrix * mvMatrix * vertex;
                   colorV = color;
                }"""

    def fragmentWireframeShaderSource(self):
        return """
                const highp vec4 wireframeColor = vec4(1.0, 0.0, 1.0, 1.0);
                void main() {
                gl_FragColor = wireframeColor;
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
        nf = geometry.mesh.n_faces()
        self.appenddictitemsize(key, nf)
        self.allocatememory(key)
        # tsAG1 = time.perf_counter()
        self.addMeshdata4oglmdl(key, geometry)
        # dtAG1 = time.perf_counter() - tsAG1
        self.bindData(key)

        # dtAG = time.perf_counter() - tsAG
        # print("Add geometry time, s:", dtAG)
        # print("addMeshdata4oglmdl time, s:", dtAG)

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
                nf = self._si.nFaces() * 2
                self.appenddictitemsize(key, nf)
                self.allocatememory(key)
                if self.selType == SelModes.FACET_WF:
                    self.addSelData4oglmdl(key, self._si, self._si.geometry)
                elif self.selType == SelModes.FACET_FILL:  # self.selType == SelModes.FACET_FILL:
                    self.addSelData4oglmdl_withOffset(key, self._si, self._si.geometry)
                elif self.selType == SelModes.FACET_FILL_GLOFFSET:
                    self.addSelData4oglmdl(key, self._si, self._si.geometry)
                else:
                    raise Exception("Unhandled Selection Type!")
                    # self.addSelData4oglmdl(key, self._si, self._si.geometry)
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
        mesh = geometry.mesh
        normals = mesh.face_normals().tolist()
        points = mesh.points().tolist()
        face_indices = mesh.fv_indices().tolist()
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
        mesh_points = ar_points[fv_indices_flattened]
        data_mesh_points = mesh_points.flatten()

        mesh_normals = np.repeat(face_normals_np, 3, axis=0)
        data_mesh_normals = mesh_normals.flatten()

        if cstype == 0:
            mesh_colors = np.tile(c, n_faces * 3)
            data_mesh_colors = mesh_colors.flatten()
        elif cstype == 1:
            mesh_colors = np.repeat(ar_face_colors, 3, axis=0)
            data_mesh_colors = mesh_colors.flatten()
        elif cstype == 2:
            # Vertex colors has not been tested and is only implemented from context.
            # --> Errors can occur.
            data_mesh_colors = ar_vertex_colors[fv_indices_flattened]

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

    def addMeshdata4oglmdl_bkp_silvio(self, key, geometry):
        tsAMD = time.perf_counter()
        mesh = geometry.mesh
        ar_fv_indices = mesh.fv_indices().tolist()
        ar_points = mesh.points().tolist()

        # color data
        cstype = 0  # color source type
        useMeshColor = True
        if self.selType == 0:
            if self._si.geometry.guid == geometry.guid:
                c = [1.0, 0.0, 1.0, 1.0]
                useMeshColor = False
            else:
                c = [0.4, 1.0, 1.0, 1.0]  # default color
        elif useMeshColor and mesh.has_face_colors():
            ar_face_colors = mesh.face_colors()
            cstype = 1
        elif useMeshColor and mesh.has_vertex_colors():
            ar_vertex_colors = mesh.vertex_colors()
            cstype = 2
        else:
            c = [0.4, 1.0, 1.0, 1.0]  # default color

        # normals data
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals()
        ar_face_normals = mesh.face_normals()

        nf = mesh.n_faces()

        ifh = 0
        for ifh in range(nf):
            fv = ar_fv_indices[ifh]
            pp = []
            cc = []
            nn = []
            n = ar_face_normals[ifh]
            if cstype == 1:
                c = ar_face_colors[ifh]

            for iv in fv:
                p = ar_points[iv]
                if cstype == 2:
                    c = ar_vertex_colors[iv]

                if self._showBack:
                    pp.append(p)
                    nn.append(n)
                    cc.append(c)

                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0], p[1], p[2],
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])

            if self._showBack:
                nv = len(pp)
                for iv in range(nv):
                    ivi = nv - 1 - iv
                    self.appendlistdata_f3xyzf3nf4rgba(key,
                                                       pp[ivi][0], pp[ivi][1], pp[ivi][2],
                                                       -nn[ivi][0], -nn[ivi][1], -nn[ivi][2],
                                                       cc[ivi][0], cc[ivi][1], cc[ivi][2], cc[ivi][3])
        dtAMD = time.perf_counter() - tsAMD
        print("Add mesh data total:", dtAMD)
        return

        for fh in mesh.faces():
            pp = []
            cc = []
            nn = []

            n = mesh.normal(fh)

            if useMeshColor and mesh.has_face_colors():
                c = mesh.color(fh)
            for vh in mesh.fv(fh):  # vertex handle
                vit = mesh.vv(vh)  # iterator
                p = mesh.point(vh)
                if useMeshColor and mesh.has_vertex_colors():
                    c = mesh.color(vh)
                iv = 0
                if self._showBack:
                    pp.append(p)
                    nn.append(n)
                    cc.append(c)
                self.appendlistdata_f3xyzf3nf4rgba(key,
                                                   p[0], p[1], p[2],
                                                   n[0], n[1], n[2],
                                                   c[0], c[1], c[2], c[3])
            if self._showBack:
                nv = len(pp)
                for iv in range(nv):
                    ivi = nv - 1 - iv
                    self.appendlistdata_f3xyzf3nf4rgba(key,
                                                       pp[ivi][0], pp[ivi][1], pp[ivi][2],
                                                       -nn[ivi][0], -nn[ivi][1], -nn[ivi][2],
                                                       cc[ivi][0], cc[ivi][1], cc[ivi][2], cc[ivi][3])

        return

    def addMeshdata4oglmdl_bkp(self, key, geometry):
        isGeometrySelected = not self._si.isEmpty()
        if isGeometrySelected:
            isGeometrySelected = self._si.geometry is geometry
        mesh = geometry.mesh
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals();
        nf = mesh.n_faces()
        verts = mesh.vertices()
        if not mesh.has_face_colors() and not mesh.has_vertex_colors():
            c = [0.4, 1.0, 1.0, 1.0]  # default color
        for fh in mesh.faces():
            n = mesh.normal(fh)
            if isGeometrySelected and self._si.getFace() is fh:
                c1 = [1.0, 0.0, 1.0, 1.0]
                for vh in mesh.fv(fh):  # vertex handle
                    vit = mesh.vv(vh)  # iterator
                    p = mesh.point(vh)
                    if mesh.has_vertex_colors():
                        c = mesh.color(vh)
                    iv = 0
                    self.appendlistdata_f3xyzf3nf4rgba(key,
                                                       p[0], p[1], p[2],
                                                       n[0], n[1], n[2],
                                                       c1[0], c1[1], c1[2], c1[3])
                isGeometrySelected = False
            else:
                if mesh.has_face_colors():
                    c = mesh.color(fh)
                for vh in mesh.fv(fh):  # vertex handle
                    vit = mesh.vv(vh)  # iterator
                    p = mesh.point(vh)
                    if mesh.has_vertex_colors():
                        c = mesh.color(vh)
                    iv = 0
                    self.appendlistdata_f3xyzf3nf4rgba(key,
                                                       p[0], p[1], p[2],
                                                       n[0], n[1], n[2],
                                                       c[0], c[1], c[2], c[3])
        return

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
    Below are the old multiprocessing addMeshdata4oglmdl functions. These functions are not used anymore since a bigger
    performance increase is obtained by using numpy array operations. However, the functions are kept for completeness. 
    
    The function add_faces_multicore has a parameter multi_mode, with which the type of multiprocessing can be chosen. 
    The 2 process options differ by the way the results are obtained from the individual Python processes. 
    Note, none of these functions are finally refactored and tested.
    multi_mode = 'pool':                Fastest option. Empirically found to be better than Process.
    multi_mode = 'process_queue':       2nd fastest option.
    multi_mode = 'process_dict':        3rd fastest option.
    """

    def addMeshdata4oglmdl_multiprocessing(self, key, geometry):
        tsAMD = time.perf_counter()
        mesh = geometry.mesh

        # color data
        cstype = 0  # color source type
        useMeshColor = True
        ar_face_colors, ar_vertex_colors = None, None
        if self.selType == 0:
            if self._si.geometry.guid == geometry.guid:
                c = [1.0, 0.0, 1.0, 1.0]
                useMeshColor = False
            else:
                c = [0.4, 1.0, 1.0, 1.0]  # default color
        elif useMeshColor and mesh.has_face_colors():
            ar_face_colors = mesh.face_colors()
            cstype = 1
        elif useMeshColor and mesh.has_vertex_colors():
            ar_vertex_colors = mesh.vertex_colors()
            cstype = 2
        else:
            c = [0.4, 1.0, 1.0, 1.0]  # default color

        # normals data
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals()
        ar_face_normals = mesh.face_normals()

        ar_fv_indices = mesh.fv_indices().tolist()
        ar_points = mesh.points().tolist()

        n_faces = mesh.n_faces()
        ifhs = range(n_faces)

        self.addFaces_multiCore(key, ar_fv_indices, ifhs, cstype, c, ar_points,
                                ar_face_normals, ar_face_colors, ar_vertex_colors, multi_mode='pool')

        dtAMD = time.perf_counter() - tsAMD
        print("Add mesh data total:", dtAMD)
        return

    def addFaces_multiCore(self, key, fvs, ifhs, cstype, c, ar_points, ar_face_normals,
                           ar_face_colors, ar_vertex_colors, multi_mode):
        n_faces = len(ifhs)
        n_cores = multiprocessing.cpu_count()
        chunksize = int(n_faces / n_cores)

        ifhs_sublists = [ifhs[core_idx * chunksize: (core_idx + 1) * chunksize] for core_idx in range(n_cores)]
        fv_sublists = [fvs[core_idx * chunksize: (core_idx + 1) * chunksize] for core_idx in range(n_cores)]
        pool_args = []

        if multi_mode == 'pool':
            for ifhs_sublist, fv_sublist in zip(ifhs_sublists, fv_sublists):
                arg = [fv_sublist, ifhs_sublist, cstype, c, ar_points, ar_face_normals, ar_face_colors,
                       ar_vertex_colors, self._showBack]
                pool_args.append(arg)

            with Pool(processes=n_cores) as p:
                array_results = p.map(BasicPainter.addFacesToArray_wrapped, pool_args)

            vertex_array, normal_array, color_array = self.distribute_array_results(array_results)

        elif multi_mode == 'process_queue':
            processes = []
            process_args = []
            queue = Queue()
            for core_idx, (ifhs_sublist, fv_sublist) in enumerate(zip(ifhs_sublists, fv_sublists)):
                arg = [fv_sublist, ifhs_sublist, cstype, c, ar_points, ar_face_normals, ar_face_colors,
                       ar_vertex_colors, self._showBack, queue, core_idx]
                process_args.append(arg)

            for args in process_args:
                p = Process(target=BasicPainter.addFacesToArray_ProcessQueue_wrapped, args=(args,))
                p.start()
                processes.append(p)

            array_results = [None for core_idx in range(n_cores)]
            for run_idx in range(n_cores):
                core_results = queue.get()
                core_idx = core_results[0]
                values = core_results[1]
                array_results[core_idx] = values

            for p in processes:
                p.join()

            vertex_array, normal_array, color_array = self.distribute_array_results(array_results)

        elif multi_mode == 'process_dict':
            process_args = []
            manager = Manager()
            return_dict = manager.dict()
            for core_idx, (ifhs_sublist, fv_sublist) in enumerate(zip(ifhs_sublists, fv_sublists)):
                arg = [fv_sublist, ifhs_sublist, cstype, c, ar_points, ar_face_normals, ar_face_colors,
                       ar_vertex_colors, self._showBack, return_dict, core_idx]
                process_args.append(arg)

            processes = []
            for args in process_args:
                p = Process(target=BasicPainter.addFacesToArray_ProcessDict_wrapped, args=(args,))
                p.start()
                processes.append(p)

            for p in processes:
                p.join()

            array_results = [None for core_idx in range(n_cores)]
            for core_idx, values in return_dict.items():
                array_results[core_idx] = values

            vertex_array, normal_array, color_array = self.distribute_array_results(array_results)

        self._dentsvertsdata[key].setlistdata_f3xyzf3nf4rgba(vertex_array, normal_array, color_array)
        if self._showBack:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3 * 2)
        else:
            self._dentsvertsdata[key].setVertexCounter(n_faces * 3)

    @staticmethod
    def distribute_array_results(array_results):
        array_results = np.array(array_results)

        vertex_array = np.concatenate(array_results[:, 0])
        vertex_array = np.array(vertex_array, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        normal_array = np.concatenate(array_results[:, 1])
        normal_array = np.array(normal_array, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        color_array = np.concatenate(array_results[:, 2])
        color_array = np.array(color_array, dtype=GLHelpFun.numpydatatype(GLDataType.FLOAT))

        return vertex_array, normal_array, color_array

    @staticmethod
    def addFacesToArray(fvs, ifhs, cstype, c, ar_points, ar_face_normals, ar_face_colors, ar_vertex_colors,
                          show_back):
        mult_factor = 1
        if show_back:
            mult_factor = 2
        vertex_data, normal_data, color_data = np.empty(len(fvs) * 9 * mult_factor, dtype=np.float), \
                                               np.empty(len(fvs) * 9 * mult_factor, dtype=np.float), \
                                               np.empty(len(fvs) * 12 * mult_factor, dtype=np.float)
        data3_idx = 0
        data4_idx = 0
        t_start = time.perf_counter()
        if show_back:
            data3_idx_back = 15
            data4_idx_back = 20

            for ifh, fv in zip(ifhs, fvs):
                n = ar_face_normals[ifh]
                if cstype == 1:
                    c = ar_face_colors[ifh]

                for run_idx, iv in enumerate(fv):
                    p = ar_points[iv]
                    if cstype == 2:
                        c = ar_vertex_colors[iv]

                    vertex_data[data3_idx] = p[0]
                    vertex_data[data3_idx + 1] = p[1]
                    vertex_data[data3_idx + 2] = p[2]

                    normal_data[data3_idx] = n[0]
                    normal_data[data3_idx + 1] = n[1]
                    normal_data[data3_idx + 2] = n[2]

                    color_data[data4_idx] = c[0]
                    color_data[data4_idx + 1] = c[1]
                    color_data[data4_idx + 2] = c[2]
                    color_data[data4_idx + 3] = c[3]

                    data3_idx += 3
                    data4_idx += 4

                    vertex_data[data3_idx_back] = p[0]
                    vertex_data[data3_idx_back + 1] = p[1]
                    vertex_data[data3_idx_back + 2] = p[2]

                    normal_data[data3_idx_back] = -n[0]
                    normal_data[data3_idx_back + 1] = -n[1]
                    normal_data[data3_idx_back + 2] = -n[2]

                    color_data[data4_idx_back] = c[0]
                    color_data[data4_idx_back + 1] = c[1]
                    color_data[data4_idx_back + 2] = c[2]
                    color_data[data4_idx_back + 3] = c[3]

                    data3_idx_back -= 3
                    data4_idx_back -= 4

                data3_idx += 9
                data4_idx += 12

                data3_idx_back += 27
                data4_idx_back += 36
        else:
            for ifh, fv in zip(ifhs, fvs):
                n = ar_face_normals[ifh]
                if cstype == 1:
                    c = ar_face_colors[ifh]

                for run_idx, iv in enumerate(fv):
                    p = ar_points[iv]
                    if cstype == 2:
                        c = ar_vertex_colors[iv]

                    vertex_data[data3_idx: data3_idx + 3] = p[0], p[1], p[2]
                    normal_data[data3_idx: data3_idx + 3] = n[0], n[1], n[2]
                    color_data[data4_idx: data4_idx + 4] = c[0], c[1], c[2], c[3]
                    data3_idx += 3
                    data4_idx += 4

        print("Process needed: {}".format(time.perf_counter() - t_start))
        return vertex_data, normal_data, color_data

    @staticmethod
    def addFacesToArray_wrapped(args):
        return BasicPainter.addFacesToArray(*args)

    @staticmethod
    def addFacesToArray_ProcessQueue_wrapped(args):
        q = args[-2]
        q.put((args[-1], BasicPainter.addFacesToArray(*args[:-2])))

    @staticmethod
    def addFacesToArray_ProcessDict_wrapped(args):
        args[-2][args[-1]] = BasicPainter.addFacesToArray(*args[:-2])
