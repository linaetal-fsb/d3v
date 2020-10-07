class pyvector3:
    def __init__(self):
        self._vec3 = [0, 0, 0]

    def setFromQt(self, vecQt):
        self._vec3[0] = vecQt.x()
        self._vec3[1] = vecQt.y()
        self._vec3[2] = vecQt.z()

    def setFromNp(self, vecnp):
        self._vec3[0] = vecnp[0]
        self._vec3[1] = vecnp[1]
        self._vec3[2] = vecnp[2]

    def setFromScalars(self, x, y, z):
        self._vec3[0] = x
        self._vec3[1] = y
        self._vec3[2] = z

    def copyFrom(self, template):
        self._vec3[0] = template._vec3[0]
        self._vec3[1] = template._vec3[1]
        self._vec3[2] = template._vec3[2]

    @property
    def X(self):
        return self._vec3[0]

    @X.setter
    def X(self, newX):
        self._vec3[0] = newX

    @property
    def Y(self):
        return self._vec3[1]

    @property
    def XYZ(self):
        return self._vec3

    @Y.setter
    def Y(self, newY):
        self._vec3[1] = newY

    @property
    def Z(self):
        return self._vec3[2]

    @Z.setter
    def Z(self, newZ):
        self._vec3[2] = newZ