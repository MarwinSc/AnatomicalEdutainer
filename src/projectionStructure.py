from enum import Enum
import vtkmodules.all as vtk
import util


class ProjectionStructure(object):
    '''
    Class for a single imported mesh/structure.
    '''
    ProjectionMethod = Enum('ProjectionMethod', 'Inflate Clipping Cube')

    color = [0.0,0.0,0.0]
    opacity = 0.5
    projectionActor = None
    projectionMethod = ProjectionMethod.Inflate
    hierarchicalMesh = None

    def __init__(self,filename,idx):
        self.mesh = util.readStl(filename)
        self.idx = idx
        self.filename = filename
        self.initColor()

    def getActor(self):
        if hasattr(self,"actor"):
            return self.actor
        else:
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(self.mesh)
            self.actor = vtk.vtkActor()
            self.actor.SetMapper(mapper)
            self.actor.GetProperty().SetColor(self.color)
            self.actor.GetProperty().SetOpacity(self.opacity)
            return self.actor

    def setOpacity(self,op):
        self.opacity = op
        self.actor.GetProperty().SetOpacity(op)

    def setColor(self,co):
        self.color = co
        self.actor.GetProperty().SetColor(co)

    def initColor(self):
        if self.idx % 3 == 0:
            self.color = [0.0, 1.0, 1.0]
        elif self.idx % 3 == 1:
            self.color = [1.0, 0.0, 1.0]
        elif self.idx % 3 == 2:
            self.color = [1.0, 1.0, 0.0]
