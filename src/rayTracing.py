# /*************************************************************************
#  * Copyright (C) 2012-2014 Tavian Barnes <tavianator@tavianator.com>     *
#  * https://github.com/tavianator/dimension                               *
#  * Copyright (C) 2020 Pero Prebeg <Pero.Prebeg@fsb.hr>                   *
#  *                                                                       *
#  * The content of this file is part of The Dimension Library. The        *
#  * original C Code of The Dimensions Library has been translated to      *
#  * Python code, further accomodations have been made to emphasize the    *
#  * purpose of d3v.                                                       *
#  *                                                                       *
#  * The Dimension Library is free software; you can redistribute it and/  *
#  * or modify it under the terms of the GNU Lesser General Public License *
#  * as published by the Free Software Foundation; either version 3 of the *
#  * License, or (at your option) any later version.                       *
#  *                                                                       *
#  * The Dimension Library is distributed in the hope that it will be      *
#  * useful, but WITHOUT ANY WARRANTY; without even the implied warranty   *
#  * of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  *
#  * Lesser General Public License for more details.                       *
#  *                                                                       *
#  * You should have received a copy of the GNU Lesser General Public      *
#  * License along with this program.  If not, see                         *
#  * <http://www.gnu.org/licenses/>.                                       *
#  *************************************************************************/

import math

from bounds import BBox
from pyVector3 import pyvector3


class dmnsn_ray:
    def __init__(self, los):
        self._x0 = pyvector3()
        self._x0.setFromQt(los[0])  # P0
        self._n = pyvector3()
        self._n.setFromQt(los[1])  # K

    @property
    def x0(self):
        return self._x0

    @property
    def n(self):
        return self._n


class dmnsn_optimized_ray:
    def __init__(self, ray: dmnsn_ray):
        self._x0 = ray.x0
        self._n_inv = pyvector3()
        self._n_inv.setFromScalars((1.0 / ray.n.X) if ray.n.X != 0 else math.inf,
                                   (1.0 / ray.n.Y) if ray.n.X != 0 else math.inf,
                                   (1.0 / ray.n.Z) if ray.n.Z != 0 else math.inf)

    @property
    def x0(self):
        return self._x0

    @property
    def n_inv(self):
        return self._n_inv


class dmnsn_aabb:
    def __init__(self):
        self._min = pyvector3()
        self._max = pyvector3()

    def setFromBBox(self, box: BBox):
        self._min.setFromNp(box.minCoord)
        self._max.setFromNp(box.maxCoord)

    def dmnsn_ray_box_intersection(self, optray: dmnsn_optimized_ray, t):
        # This is actually correct, even though it appears not to handle edge cases
        # (ray.n.{x,y,z} == 0).  It works because the infinities that result from
        # dividing by zero will still behave correctly in the comparisons.  Rays
        # which are parallel to an axis and outside the box will have tmin == inf
        # or tmax == -inf, while rays inside the box will have tmin and tmax
        # unchanged.

        tx1 = (self.min.X - optray.x0.X) * optray.n_inv.X
        tx2 = (self.max.X - optray.x0.X) * optray.n_inv.X

        tmin = min(tx1, tx2)
        tmax = max(tx1, tx2)

        ty1 = (self.min.Y - optray.x0.Y) * optray.n_inv.Y
        ty2 = (self.max.Y - optray.x0.Y) * optray.n_inv.Y

        tmin = max(tmin, min(ty1, ty2))
        tmax = min(tmax, max(ty1, ty2))

        tz1 = (self.min.Z - optray.x0.Z) * optray.n_inv.Z
        tz2 = (self.max.Z - optray.x0.Z) * optray.n_inv.Z

        tmin = max(tmin, min(tz1, tz2))
        tmax = min(tmax, max(tz1, tz2))

        return tmax >= max(0.0, tmin) and tmin < t

    def isIn_array(self, points):
        isIn_bool_array0 = (self.min._vec3[0] < points[:, 0]) & (points[:, 0] < self.max._vec3[0])
        isIn_bool_array1 = (self.min._vec3[1] < points[:, 1]) & (points[:, 1] < self.max._vec3[1])
        isIn_bool_array2 = (self.min._vec3[2] < points[:, 2]) & (points[:, 2] < self.max._vec3[2])
        isIn_bool_array_final = isIn_bool_array0 & isIn_bool_array1 & isIn_bool_array2
        return isIn_bool_array_final

    def isIn(self, point: pyvector3):
        """
        Not used anymore, but kept in code for completeness
        """
        for i in range(3):
            if (self.min._vec3[i] > point._vec3[i]):
                return False
            if (self.max._vec3[i] < point._vec3[i]):
                return False

        return True

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max