import sys
import os

sys.path.append(os.path.dirname(__file__))

from a_painterbasic.basicpainter import BasicPainter



def createPainter():
    return BasicPainter()
