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
from typing import List,Dict,Set
import uuid

class SelModes(Enum):
    FACET_WF = 1                # Selected Facet marked by wireframe using glPolygonMode
    FULL_FILL_SHADER = 2        # Full geometry, which is is selected, is colored in pink by a second shader
    FULL_WF = 4                 # Full geometry marked by pink wireframe using glPolygonMode
    FACET_FILL_GLOFFSET = 5     # Selected facet is colored in pink with glPolygonOffset to avoid z-fight

FACET_LIST_SEL_GUID = uuid.uuid4()


def get_child_menu(parentQMenu, childName):
    for a in parentQMenu.actions():
        if a.text() == childName:
            return a.parent()
    return None

class BasicPainterBase(Painter):

    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()
        self._do_paint = True
        self._do_process_data = True
        #opengl data
        self._dentsvertsdata = {}  # dictionary that holds vertex data for all primitive and  submodel combinations
        self._multFactor = 1 # maybe not the brighest idea -> this caused problems in memory allocation
        self._showBack = False
        # Shader program data
        self.program = 0
        self.normalMatrixLoc = 0
        self.vertexShader = self._vertex_shader_source()
        self.fragmentShader = self._fragment_shader_source()
        # paint device (e.g. glWin), and coresponding transforamtion matrices
        self.paintDevice = 0
        self.projMatrixLoc = 0
        self.mvMatrixLoc = 0
        # light position
        self.lightPosLoc = 0 # opengl light position
        self._light_position = QVector3D(0, 0, 100000)  # vector
        #geometry manager selected/visible changed  events
        geometry_manager.geometry_state_changing.connect(self.onGeometryStateChanging)
        geometry_manager.visible_geometry_changed.connect(self.onVisibleGeometryChanged)
        self._s_visible_geo_guids: set = set()

        # Add menu items
        self.initialize_painter_menus()
        self._color =[0.4, 1.0, 1.0, 1.0]  # default color



    def initialize_painter_menus(self):
        painters_menu_name = 'Painters'
        app = QApplication.instance()
        mf = app.mainFrame
        tools = app.mainFrame.menuTools
        self._painters_menu = get_child_menu(tools,painters_menu_name)
        if self._painters_menu is None:
            self._painters_menu = QMenu(painters_menu_name, mf)
            tools.addMenu(self._painters_menu)
        self._menu = QMenu(self.name, mf)
        self._painters_menu.addMenu(self._menu)

        self.act_do_process_data = QAction('Use painter', self._menu, checkable=True)
        self.act_do_process_data.triggered.connect(self.on_action_do_process_data)
        self._menu.addAction(self.act_do_process_data)
        self.act_do_process_data.setChecked(True)

        self.act_do_paint = QAction('Show painter', self._menu, checkable=True)
        self.act_do_paint.triggered.connect(self.on_action_do_do_paint)
        self._menu.addAction(self.act_do_paint)
        self.act_do_paint.setChecked(True)

        self._menu.addSeparator()
        self.act_set_color = QAction('Set constant color', self._menu)
        self.act_set_color.triggered.connect(self.on_action_set_color)
        self._menu.addAction(self.act_set_color)




    def on_action_do_process_data(self):
        self.do_process_data = self.act_do_process_data.isChecked()
        self.act_do_paint.setChecked(self.do_process_data)

    def on_action_do_do_paint(self):
        self._do_paint = self.act_do_paint.isChecked()
        self.requestGLUpdate()

    def on_action_set_color(self):
        color = QColor.fromRgbF(self._color[0], self._color[1], self._color[2], self._color[3])
        color = QColorDialog.getColor(color)
        self._color = [color.redF(), color.greenF(), color.blueF(), color.alphaF()]

    @property
    def do_process_data(self):
        return self._do_process_data

    @do_process_data.setter
    def do_process_data(self, value):
        if value != self._do_process_data:
            self._do_process_data = value
            self.on_change_do_process_data()
            self.requestGLUpdate()
        self._do_process_data = value

    def on_change_do_process_data(self):
        pass

    @property
    def name(self):
        return "Basic Painter Base"

    @property
    def showBack(self):
        return self._showBack

    @showBack.setter
    def showBack(self, newShowBack):
        self._showBack = newShowBack
        self._multFactor = 1
        if self._showBack:
            self._multFactor = 2
    def _vertex_shader_source(self):
        pass
    def _fragment_shader_source(self):
        pass
    def initializeGL(self):
        super().initializeGL()
        self.glf.initializeOpenGLFunctions()
        self.paintDevice = QApplication.instance().mainFrame.glWin
        self.width = self.paintDevice.vport.width()
        self.height = self.paintDevice.vport.height()
        self.initializeShaderProgram()

    def initializeShaderProgram(self):
        pass

    #obsolete - will be removed from glwin
    def setprogramvalues(self, proj, mv, normalMatrix, lightpos):
        pass



    def paintGL(self):
        if self._do_paint:
            super().paintGL()
            self.basic_painter_before_paint()
            self.basic_painter_paint()
            self.basic_painter_after_paint()

    def basic_painter_before_paint(self):
        pass

    def basic_painter_paint(self):
        pass

    def basic_painter_after_paint(self):
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
        self.delayed_update_gl_data()


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

    def bind_data(self, key):
        self._dentsvertsdata[key].setupVertexAttribs(self.glf)
        atrList = self._dentsvertsdata[key].GetAtrList()
        for ent in atrList:
            self.program.bindAttributeLocation(ent[0], ent[1])

    # region selection logic implementation


    def is_visible_geo(self,guid):
        return guid in self._s_visible_geo_guids


    # Painter methods implementation code ********************************************************



    @Slot()
    def onGeometryStateChanging(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        pass

    @Slot()
    def onVisibleGeometryChanged(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        self._s_visible_geo_guids.clear()
        for g in visible:
            self._s_visible_geo_guids.add(g.guid)

    def delayed_remove_mesh_data_from_gl_data(self, key):
        self.removeDictItem(key)



    def delayed_update_gl_data(self):
        '''
        Updates painter OpenGL data
        Neads to be implemented in each painter
        :return:
        '''
        pass



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

    def add_line_data_to_gl(self, key, n_vertices, vertices):
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

    def add_tria_mesh_data_to_gl(self, key, mesh:om.TriMesh):
        """
        Converts the mesh data of a geometry to the vertex data necessary for OpenGL.

        :param key: key under which the geometry is saved
        :param mesh: geometry which mesh data is to be converted
        :return:
        """
        if __debug__:
            tsAMD = time.perf_counter()

        # color data
        cstype = 0  # color source type
        if mesh.has_face_colors():
            ar_face_colors = mesh.face_colors()
            cstype = 1
        elif mesh.has_vertex_colors():
            ar_vertex_colors = mesh.vertex_colors()
            cstype = 2
        else:
            c = self._color  # default color

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


    """ 
    Utilities for Polymesh
    """
    def add_poly_mesh_data_to_gl(self, key, mesh:om.PolyMesh):
        """
        Converts the mesh data of a polygon mesh to the vertex data necessary for OpenGL
        :param key: key under which the geometry is saved
        :param mesh:  mesh data which is to be converted
        :return:
        """
        if __debug__:
            tsAMD = time.perf_counter()

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
            c = self._color  # default color
            #c = [0.4, 1.0, 1.0, 1.0]  # default color

        # normals data
        if not mesh.has_face_normals():  # normals are necessary for correct lighting effect
            mesh.request_face_normals()
            mesh.update_face_normals()

        fv_indices_np = mesh.fv_indices()
        face_normals_np = mesh.face_normals()
        ar_points = mesh.points()

        self.add_poly_mesh_arrays_data_to_gl(key, fv_indices_np, ar_points, face_normals_np, cstype, c, ar_face_colors, ar_vertex_colors)

        if __debug__:
            dtAMD = time.perf_counter() - tsAMD
            print("Add mesh data total:", dtAMD)
        return

    def add_poly_mesh_arrays_data_to_gl(self, key, fv_indices, points, face_normals, cstype, c, face_colors, vertex_colors):
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
                if face_colors is not None:
                    face_colors_to_draw = face_colors[existing_triangles]
            else:
                fv_indices_to_draw = fv_indices
                face_normals_to_draw = face_normals
                face_colors_to_draw = face_colors

            fv_indices_flattened = fv_indices_to_draw.flatten()
            n_all_vertices += len(fv_indices_flattened)

            n_faces = len(fv_indices_to_draw)

            vertexData = self.createVertexData(fv_indices_flattened, points)

            normalData = self.createNormaldata(face_normals_to_draw)

            if cstype == 0:
                colorData = self.createConstantColorData(c, n_faces)
            elif cstype == 1:
                colorData = self.createFaceColorData(face_colors_to_draw)
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
                    reversed_colors = self.createFaceColorData(face_colors_to_draw[::-1])
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

    def delayed_add_mesh_to_gl_data(self, key,mesh):
        self.initnewdictitem(key, GLEntityType.TRIA)
        if type(mesh) == om.TriMesh:
            n_triangles = mesh.n_faces()
            self.appenddictitemsize(key, n_triangles)
            self.allocatememory(key)
            self.add_tria_mesh_data_to_gl(key, mesh)

        elif type(mesh) == om.PolyMesh:
            fv_indices = mesh.fv_indices()
            n_possible_triangles = fv_indices.shape[0] * (fv_indices.shape[1] - 2)
            mask_not_triangles = fv_indices == -1
            not_triangles = fv_indices[mask_not_triangles]
            n_not_triangles = len(not_triangles)
            n_triangles = n_possible_triangles - n_not_triangles
            self.appenddictitemsize(key, n_triangles)
            self.allocatememory(key)
            self.add_poly_mesh_data_to_gl(key, mesh)

        else:
            print("Not handled mesh type")
        self.bind_data(key)

    def delayed_add_geometry_to_gl_data(self, geometry: Geometry):
        key = geometry.guid
        mesh = geometry.mesh
        self.delayed_add_mesh_to_gl_data(key,mesh)

    def delayed_remove_item_from_gl_data(self, key):
        self.delayed_remove_mesh_data_from_gl_data(key)

class BasicPainterGeometryBase(BasicPainterBase):

    def __init__(self):
        """
        The type how a selected plane / geometry is visualized can be specified by self.selType
        """
        super().__init__()

        self._dgeos = {}  # dictionary that holds existing geometries
        self._geo2Add:List[Geometry] = []
        self._geoKey2Remove:List[Geometry] = []
        self.__loaded_before_change:Set[Geometry] =set()


    def remove_geometry_item(self, key):
        if key in self._dgeos:
            del self._dgeos[key]

    def add_geometry_iItem(self, geometry:Geometry):
        self._dgeos[geometry.guid] = geometry

    @Slot()
    def onGeometryStateChanging(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        super(BasicPainterGeometryBase, self).onGeometryStateChanging(visible,loaded,selected)
        self.__loaded_before_change = set(loaded)

    @Slot()
    def onVisibleGeometryChanged(self, visible:List[Geometry], loaded:List[Geometry], selected:List[Geometry]):
        super(BasicPainterGeometryBase, self).onVisibleGeometryChanged(visible,loaded,selected)
        # add new geos
        geo_to_add = set(loaded)-self.__loaded_before_change
        if len(geo_to_add)>0:
            self.process_geometries_added(list(geo_to_add))
        geo_to_remove = self.__loaded_before_change - set(loaded)
        if len(geo_to_remove) > 0:
            self.process_geometries_removed(list(geo_to_remove))

    def process_geometries_added(self,geometries:List[Geometry]):
        self._geo2Add.extend(geometries)
        self.requestGLUpdate()

    def process_geometries_removed(self,geometries:List[Geometry]):
        keys = []
        for g in geometries:
            keys.append(g.guid)
        self._geoKey2Remove.extend(keys)
        self.requestGLUpdate()

    def onGeometryCreated(self, geometries:List[Geometry]):
        self._geo2Add.extend(geometries)
        self.requestGLUpdate()

    def onGeometryRemoved(self, geometries:List[Geometry]):
        keys= []
        for g in geometries:
            keys.append(g.guid)
        self._geoKey2Remove.extend(keys)
        self.requestGLUpdate()

    def delayed_add_geometry_to_gl_data(self, geometry: Geometry):
        super().delayed_add_geometry_to_gl_data(geometry)
        self.add_geometry_iItem(geometry)

    def add_geometry_to_all_geo_dictionary(self, geometries:List[Geometry]):
        for geometry in geometries:
            self.add_geometry_iItem(geometry)
    def remove_geometries_from_all_geo_dictionary(self, geometries:List[Geometry]):
        for geometry in geometries:
            self.remove_geometry_item(geometry.guid)
