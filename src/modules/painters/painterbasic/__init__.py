import sys
import os

sys.path.append(os.path.dirname(__file__))

from basicpainter import BasicPainter



def createPainter():
    return BasicPainter()
