import sys
import os
from painters import Painter
sys.path.append(os.path.dirname(__file__))

class DummyPainter(Painter):
    def __init__(self):
        pass

# Create Dummy Painter to avoid painter import error for parent directory
def createPainter():
    return DummyPainter()
