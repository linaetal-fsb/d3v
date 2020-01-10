from PySide2.QtWidgets import QApplication, QMenu, QMessageBox
from commands import Command

import openmesh as om
import numpy as np
from signals import Signals
from geometry import Geometry


class TemplateCommand(Command):
    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        tools = app.mainFrame.menuTools

        menu = QMenu("Create ...")

        box = menu.addAction(" ... box")
        sph = menu.addAction(" ... sphere")

        box.triggered.connect(self.onCreateBox)
        sph.triggered.connect(self.onCreateSph)

        tools.addMenu(menu)

    def onCreateBox(self):
        mesh = om.TriMesh()
        # m --> min, M --> max
        # yapf: disable
        p0 = mesh.add_vertex([-1, -1, -1])
        p1 = mesh.add_vertex([-1, -1,  1])
        p2 = mesh.add_vertex([-1,  1, -1])
        p3 = mesh.add_vertex([-1,  1,  1])
        p4 = mesh.add_vertex([ 1, -1, -1])
        p5 = mesh.add_vertex([ 1, -1,  1])
        p6 = mesh.add_vertex([ 1,  1, -1])
        p7 = mesh.add_vertex([ 5,  5,  1])
        # yapf: enable

        mesh.add_face([p0, p6, p4])
        mesh.add_face([p0, p2, p6])
        mesh.add_face([p0, p4, p5])
        mesh.add_face([p0, p5, p1])
        mesh.add_face([p0, p3, p2])
        mesh.add_face([p0, p1, p3])
        mesh.add_face([p6, p2, p3])
        mesh.add_face([p6, p3, p7])
        mesh.add_face([p4, p7, p5])
        mesh.add_face([p4, p6, p7])
        mesh.add_face([p1, p5, p7])
        mesh.add_face([p1, p7, p3])

        g = Geometry()
        g.mesh = mesh
        Signals.get().geometryImported.emit(g)

    def onCreateSph(self):
        fileName='D:\\Development\\d3v\\examples\\cube-minimal-normals.ply'
        g = Geometry()
        try:
            m = om.read_trimesh(fileName)
        except:
            print("File not supported for read with openmesh")
            return
        g.mesh = m
        Signals.get().geometryImported.emit(g)
        QMessageBox.information(None, "Učitavanje", "Učitavanje datoteke preko  Create .. meni")
        return
        QMessageBox.information(None, "Sphere", "Creating sphere")


def createCommand():
    return TemplateCommand()
