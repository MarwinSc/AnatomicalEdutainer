import vtkmodules.all as vtk
from vtkmodules.numpy_interface.dataset_adapter import numpy_support
import numpy as np
import os
import util

class Projector:
    '''
    Class to handle projecting the rendered structures onto a texture image.
    '''

    dirname = os.path.dirname(__file__)

    def projectPerTriangle(self,dedicatedPaperMesh, structure ,meshNr = 0, resolution = [500,500]):
        '''
        Rendering method that produces a long texture image of concatenated renderings of the triangles from the papermesh.
        :param dedicatedPaperMesh: the projection mesh.
        :param structure: the structure to project on the mesh.
        :param meshNr: index used only for the filename.
        :param resolution: resolution for the rendering of each triangle.
        :return: the projection mesh with the created texture assigned.
        '''
        paper = dedicatedPaperMesh.GetMapper().GetInput()

        centersFilter = vtk.vtkCellCenters()
        centersFilter.SetInputData(paper)
        centersFilter.VertexCellsOn()
        centersFilter.Update()

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(paper)

        normals.ComputePointNormalsOff()
        normals.ComputeCellNormalsOn()
        normals.SplittingOff()
        normals.FlipNormalsOn()
        normals.Update()

        array = normals.GetOutput()
        normalDataDouble = array.GetCellData().GetArray("Normals")

        # -----------------

        camera = vtk.vtkCamera()
        #        camera.SetViewUp(0, 1, 0)
        camera.ParallelProjectionOn()
        camera.Zoom(0.01)
        camera.SetClippingRange(0.0001, 300.01)
        #TODO reimplement with hierachical Mesh
        #if inflateStruc:
        #    if not inflateStruc[meshNr]:
        #        camera.SetClippingRange(0.0001, 60.01)

        depthPeeling = True
        occlusion = 0.1
        numberOfPeels = 10

        buffer = vtk.vtkRenderer()
        buffer.SetBackground(255.0, 255.0, 255.0)
        buffer.SetActiveCamera(camera)
        buffer.SetLayer(0)

        bufferPaper = vtk.vtkRenderer()
        buffer.SetBackground(255.0, 255.0, 255.0)
        buffer.SetActiveCamera(camera)
        bufferPaper.SetLayer(1)

        bufferPoints = vtk.vtkRenderer()
        bufferPoints.SetBackground(255.0, 255.0, 255.0)
        bufferPoints.SetActiveCamera(camera)
        bufferPoints.SetLayer(0)

        bufferWin = vtk.vtkRenderWindow()
        bufferWin.SetNumberOfLayers(2)
        bufferWin.SetSize(resolution[0], resolution[1])
        bufferWin.AddRenderer(buffer)
        bufferWin.AddRenderer(bufferPaper)
        bufferWin.SetOffScreenRendering(True)

        bufferWinPoints = vtk.vtkRenderWindow()
        bufferWinPoints.SetNumberOfLayers(1)
        bufferWinPoints.SetSize(resolution[0], resolution[1])
        bufferWinPoints.AddRenderer(bufferPoints)
        bufferWinPoints.SetOffScreenRendering(True)

        bufferIren = vtk.vtkRenderWindowInteractor()
        bufferIren.SetRenderWindow(bufferWin)

        if depthPeeling:
            buffer.SetUseDepthPeeling(True)
            buffer.SetOcclusionRatio(occlusion)
            buffer.SetMaximumNumberOfPeels(numberOfPeels)
        else:
            buffer.SetUseDepthPeeling(False)

        #-----------------
        transparent = [0.0, 0.0, 0.0, 0.0]
        cellData = vtk.vtkUnsignedCharArray()
        cellData.SetNumberOfComponents(4)
        cellData.SetNumberOfTuples(centersFilter.GetOutput().GetNumberOfPoints())
        for i in range(centersFilter.GetOutput().GetNumberOfPoints()):
            cellData.InsertTuple(i, transparent)

        paper.GetCellData().SetScalars(cellData)
        paper.GetCellData().Modified()
        paper.Modified()
        #-----------------

        uvArray = vtk.vtkDoubleArray()
        uvArray.SetNumberOfComponents(2)
        newGeometry = vtk.vtkPolyData()
        newPoints = vtk.vtkPoints()
        newCells = vtk.vtkCellArray()

        img = np.array([[],[],[]])

        for i in range(centersFilter.GetOutput().GetNumberOfPoints()):
            p = [0.0, 0.0, 0.0]
            centersFilter.GetOutput().GetPoint(i, p)

            p2 = normalDataDouble.GetTuple3(i)
            normalScale = -5
            #+0.01 because of the lighting, which renders everything white if viewed parallel to the z-axis
            position = [p[0]+0.01 + (p2[0] * normalScale), p[1]+0.01 + (p2[1] * normalScale), p[2]+0.01 + (p2[2] * normalScale)]

            camera.SetPosition(position)
            camera.SetFocalPoint(p)
            points = paper.GetCell(i).GetPoints()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(paper)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            bufferPaper.AddActor(actor)

            bufferPoints.RemoveAllViewProps()

            self.drawPoints(points,bufferPoints)

            # render frame
            triangle, pointsImg = self.renderHelper(camera, buffer, bufferPaper, bufferPoints, bufferWin, bufferWinPoints, i, structure)

            # --------------
            #dy, dx, dz = triangle.shape
            print(i)
            #filename = os.path.join(self.dirname, "../out/2D/triangle{}.png".format(i))
            #util.writeImage(util.NpToVtk(triangle,dx,dy,dz),filename)

            #filename = os.path.join(self.dirname, "../out/2D/triangle{}_points.png".format(i))
            #util.writeImage(util.NpToVtk(pointsImg, dx, dy, dz), filename)
            # ---------------

            blue = pointsImg[:, :, 2]
            red = pointsImg[:, :, 0]
            green = pointsImg[:, :, 1]
            maskBlue = np.logical_and(np.logical_and(blue > 250, red < 1), green < 1)
            maskRed = np.logical_and(np.logical_and(red > 250, blue < 1), green < 1)
            maskGreen = np.logical_and(np.logical_and(green > 250, red < 1), blue < 1)

            if np.size(np.where(maskRed))!=0 and np.size(np.where(maskGreen))!=0 and np.size(np.where(maskBlue)) != 0:

                uvArray.InsertNextTuple2(np.where(maskRed)[1][0] + img.shape[1],np.where(maskRed)[0][0])
                uvArray.InsertNextTuple2(np.where(maskGreen)[1][0] + img.shape[1],np.where(maskGreen)[0][0])
                uvArray.InsertNextTuple2(np.where(maskBlue)[1][0] + img.shape[1],np.where(maskBlue)[0][0])

                #potential problems here that large triangles after the first one could be to big for the image shape todo
                if len(img[0]) == 0:
                    img = triangle
                    black = np.zeros((resolution[0], img.shape[1], img.shape[2]))
                    img = np.vstack((img, black))
                else:
                    black = np.zeros((img.shape[0] - triangle.shape[0], triangle.shape[1], triangle.shape[2]))
                    triangle = np.vstack((triangle, black))
                    img = np.hstack((img, triangle))

                triCell = vtk.vtkTriangle()

                pointId = newPoints.InsertNextPoint(points.GetPoint(0))
                triCell.GetPointIds().SetId(0,pointId)

                pointId = newPoints.InsertNextPoint(points.GetPoint(1))
                triCell.GetPointIds().SetId(1,pointId)

                pointId = newPoints.InsertNextPoint(points.GetPoint(2))
                triCell.GetPointIds().SetId(2,pointId)

                newCells.InsertNextCell(triCell)

                bufferPaper.RemoveAllViewProps()
                buffer.RemoveAllViewProps()

        #todo cutting away the black area at the top of the images.

        dy, dx, dz = img.shape
        filename = os.path.join(self.dirname, "../out/2D/texture/texture{}.png".format(meshNr))

        writtenImg = util.writeImage(util.NpToVtk(img,dx,dy,dz),filename)

        for i in range(uvArray.GetNumberOfTuples()):
            uvArray.SetTuple2(i,uvArray.GetTuple2(i)[0]/img.shape[1],uvArray.GetTuple2(i)[1]/img.shape[0])

        #creating the deadicated papermesh with multiple vertices and texture
        #uv coordinates are mapped onto the created long texture
        newGeometry.SetPoints(newPoints)
        newGeometry.SetPolys(newCells)
        newGeometry.GetPointData().SetTCoords(uvArray)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(newGeometry)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        texture = vtk.vtkTexture()
        texture.SetInputData(writtenImg)
        actor.SetTexture(texture)

        dedicatedPaperMesh = actor

        return dedicatedPaperMesh

    def drawPoints(self,points,bufferPoints):
        '''
        Draws the points used for cropping the rendered triangles and uv mapping onto the long texture image.
        :param points: the vtk points.
        :param bufferPoints: the renderer for the points.
        :return:
        '''
        pointActor = vtk.vtkActor()

        colors = vtk.vtkNamedColors()
        Colors = vtk.vtkUnsignedCharArray()
        Colors.SetNumberOfComponents(3)
        Colors.SetName("Colors")
        Colors.InsertNextTuple3(*colors.GetColor3ub('Red'))
        Colors.InsertNextTuple3(*colors.GetColor3ub('Lime'))
        Colors.InsertNextTuple3(*colors.GetColor3ub('Blue'))

        # Create the topology of the point (a vertex)
        new_points = vtk.vtkPoints()
        vertices = vtk.vtkCellArray()
        scalars = vtk.vtkDoubleArray()
        scalars.SetNumberOfComponents(3)

        id = new_points.InsertNextPoint(points.GetPoint(0))
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(id)

        id = new_points.InsertNextPoint(points.GetPoint(1))
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(id)

        id = new_points.InsertNextPoint(points.GetPoint(2))
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(id)

        # Create a polydata object
        point = vtk.vtkPolyData()

        # Set the points and vertices we created as the geometry and topology of the polydata
        point.SetPoints(new_points)
        point.SetVerts(vertices)
        point.GetPointData().SetScalars(Colors)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(point)

        pointActor.SetMapper(mapper)
        pointActor.GetProperty().SetPointSize(2)
        bufferPoints.AddActor(pointActor)

    def renderHelper(self, camera, buffer, bufferPaper, bufferPoints, bufferWin, bufferWinPoints, count, actor):
        ##Was necessary at some stage of programming, could be removed later on.
        buffer.AddActor(actor)

        buffer.SetActiveCamera(camera)
        bufferPaper.SetActiveCamera(camera)
        bufferPoints.SetActiveCamera(camera)

        bufferWin.Render()

        wti = vtk.vtkWindowToImageFilter()
        wti.SetInput(bufferWin)
        wti.SetInputBufferTypeToRGB()
        wti.Update()

        bufferWinPoints.Render()

        wti2 = vtk.vtkWindowToImageFilter()
        wti2.SetInput(bufferWinPoints)
        wti2.SetInputBufferTypeToRGB()
        wti2.Update()

        triangleImg, pointsImg = self.cropRenderedTriangle(wti.GetOutput(), wti2.GetOutput(), bufferWin.GetSize(), count)

        return triangleImg, pointsImg

    def cropRenderedTriangle(self, image, pointsImage, resolution, count = 1):
        '''
        Receives the image of a single triangle and the dedicated image of corner points and crops it to the bounds of the triangle, based on the pointsImage.
        :param image: rendered triangle as vtk image.
        :param pointsImage: rendered points as vtk image.
        :param resolution: resolution of the rendering.
        :param count:
        :return: returns both images cropped to the axis aligned bounds.
        '''
        img = numpy_support.vtk_to_numpy(image.GetPointData().GetScalars())[:, 0:3]
        points = numpy_support.vtk_to_numpy(pointsImage.GetPointData().GetScalars())[:, 0:3]

        img.astype(float)
        img = np.reshape(np.ravel(img), (resolution[0], resolution[1], 3))
        points.astype(float)
        points = np.reshape(np.ravel(points), (resolution[0], resolution[1], 3))

        blue = points[:,:,2]
        green = points[:,:,1]
        red = points[:,:,0]

        maskBlue = np.logical_and(np.logical_and(blue > 250, red < 50), green < 50)
        maskRed = np.logical_and(np.logical_and(red > 250, blue < 50), green < 50)
        maskGreen = np.logical_and(np.logical_and(green > 250, red < 50), blue < 50)
        mask = np.where((maskBlue+maskGreen+maskRed))

        if len(mask[0]) > 0 and len(mask[1]) > 0:
            result = img[mask[0].min()-2:mask[0].max()+2, mask[1].min()-2 : mask[1].max()+2, :]
            pointsResult = points[mask[0].min()-2:mask[0].max()+2, mask[1].min()-2 : mask[1].max()+2, :]
        else:
            #could be removed for better error handling todo
            result = [[[1.0,0.0,0.0],[1.0,0.0,0.0],[1.0,0.0,0.0]],[[1.0,0.0,0.0],[1.0,0.0,0.0],[1.0,0.0,0.0]],[[1.0,0.0,0.0],[1.0,0.0,0.0],[1.0,0.0,0.0]]]
            result = np.array(result)
            pointsResult = result

        return result, pointsResult

    def createUnfoldedPaperMesh(self,dedicatedPaperMesh, originalPaperMesh, idx):
        '''
        Method that maps the created texture to an mesh which is created according to the unfolded uv layout,
        interpreted as 2D coordinates,  thus creating the final rendering for the printable paper template.
        :param dedicatedPaperMesh: the created paperMesh with uvs mapped to the created long texture.
        :param originalPaperMesh: the general papermesh with unfolded uv layout for this structure that is imported.
        :param idx: number for the filename.
        :return:
        '''
        mesh = originalPaperMesh.GetMapper().GetInput()

        # TODO Set automatically based on the relative size of the uv grid
        width = 400

        textureCoordinates = mesh.GetPointData().GetTCoords()

        points = vtk.vtkPoints()
        cells = vtk.vtkCellArray()

        widthMarker = [0.0, 0.0]
        heightMarker = [0.0, 0.0]

        # creating a mesh according to the uv layout
        for i in range(mesh.GetNumberOfCells()):
            uvs = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
            textureCoordinates.GetTuple(mesh.GetCell(i).GetPointId(0), uvs[0])
            textureCoordinates.GetTuple(mesh.GetCell(i).GetPointId(1), uvs[1])
            textureCoordinates.GetTuple(mesh.GetCell(i).GetPointId(2), uvs[2])

            cells.InsertNextCell(3)

            for j in range(len(uvs)):
                x = (uvs[j][0] * width) - (width / 2.0)
                y = (uvs[j][1] * width) - (width / 2.0)

                point = [x, -1.0, y]

                if x > widthMarker[1]:
                    widthMarker[1] = x
                elif x < widthMarker[0]:
                    widthMarker[0] = x
                if y > heightMarker[1]:
                    heightMarker[1] = y
                elif y < heightMarker[0]:
                    heightMarker[0] = y

                id = points.InsertNextPoint(point)
                cells.InsertCellPoint(id)

        textureCoordinates = dedicatedPaperMesh.GetMapper().GetInput().GetPointData().GetTCoords()

        unfoldedPaper = vtk.vtkPolyData()

        unfoldedPaper.SetPoints(points)
        unfoldedPaper.SetPolys(cells)
        unfoldedPaper.GetPointData().SetTCoords(textureCoordinates)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(unfoldedPaper)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        # ----------------------

        filename = os.path.join(self.dirname, "../out/2D/texture/texture{}.png".format(idx))
        readerFac = vtk.vtkImageReader2Factory()
        imageReader = readerFac.CreateImageReader2(filename)
        imageReader.SetFileName(filename)

        texture = vtk.vtkTexture()
        texture.SetInputConnection(imageReader.GetOutputPort())

        actor.SetTexture(texture)

        camera = vtk.vtkCamera()
        camera.SetPosition(0, -600, 0)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(500.0)
        ren, iren, renWin, wti = util.getbufferRenIntWin(camera, width=5000, height=5000)
        renWin.SetOffScreenRendering(1)

        ren.AddActor(actor)
        renWin.Render()

        wti.Update()

        imgWidth = wti.GetOutput().GetExtent()[1] + 1
        imgHeight = wti.GetOutput().GetExtent()[3] + 1

        img = self.vtkToNpHelper(wti.GetOutput(), imgWidth, imgHeight)

        dy, dx, dz = img.shape
        filename = os.path.join(self.dirname, "../out/2D/unfolding{}.png".format(idx))
        util.writeImage(util.NpToVtk(img,dx,dy,dz),filename)

    def vtkToNpHelper(self, img, width, height):
        img = numpy_support.vtk_to_numpy(img.GetPointData().GetScalars())[:, 0:3]
        img.astype(float)

        img = np.reshape(np.ravel(img), (width, height, 3))

        mask = np.where(img != 255)
        width = mask[0].max() - mask[0].min()
        height = mask[1].max() - mask[1].min()
        if width > height:
            img = img[mask[0].min():mask[0].max(), mask[1].min(): mask[1].min() + width, :]
        else:
            img = img[mask[0].min():mask[0].min() + height, mask[1].min(): mask[1].max(), :]

        return img

