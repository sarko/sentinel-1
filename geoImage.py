#!/opt/local/bin/python2.7


from osgeo import gdal
import numpy as np
from lxml import etree


class geoImage:

    def __init__(self,imName):
        #print imName
        self.imName = imName
        handle = gdal.Open(imName)
        self.numBands = handle.RasterCount
        self.geoTransform = handle.GetGeoTransform()
        self.projection = handle.GetProjection()
        self.x = handle.RasterXSize
        self.y = handle.RasterYSize
       
        banddata = handle.GetRasterBand(1)
        if gdal.GetDataTypeName(banddata.DataType).lower() == 'cfloat32':
            self.data = np.zeros((self.y,self.x,self.numBands),dtype=np.complex64)
        else:
            self.data = np.zeros((self.y,self.x,self.numBands))
        self.min = np.zeros(self.numBands)
        self.max = np.zeros(self.numBands)
        self.bandType = []

        for i in range(0,self.numBands):
            banddata = handle.GetRasterBand(i+1)
            self.data[:,:,i] = banddata.ReadAsArray()
            self.bandType.append(gdal.GetDataTypeName(banddata.DataType).lower())
            self.min[i] = np.min(self.data[:,:,i])
            self.max[i] = np.max(self.data[:,:,i])
            if self.min[i] is None or self.max[i] is None:
                (self.min[i],self.max[i]) = banddata.ComputeRasterMinMax(1)

        self.metadata = handle.GetMetadata()
        self.gcp = handle.GetGCPs()
        self.gcpProj = handle.GetGCPProjection()

    def writeFile(self,filename,format='GTiff',band='all',dt=None,metadata=None,nd=0):
        driver = gdal.GetDriverByName(format)

        if dt == None:
            self.setGDALDataType()
            dt = self.gdalDT
        if band == 'all':
            numBands = self.numBands
        else:
            numBands = 1

        dst_ds = driver.Create(filename,self.x,self.y,numBands,dt,options=["COMPRESS=LZW"])
        if metadata is not None:
            dst_ds.SetMetadata(metadata)

        if band =='all':
            for i in range(0,self.numBands):
                dst_ds.GetRasterBand(i+1).WriteArray(self.data[:,:,i])
        else:
            dst_ds.GetRasterBand(1).WriteArray(band)

        dst_ds.GetRasterBand(1).SetNoDataValue(nd)
        dst_ds.SetGeoTransform(self.geoTransform)
        dst_ds.SetProjection(self.projection)
        return 1

    def setGDALDataType(self):
        np2gdalDT = {'uint8':1,'int8':2,'uint16':3,'uint32':4,'int32':5,'float32':6,'float64':7,'cfloat32':10,'complex64':10,'complex128':11}
        self.gdalDT = np2gdalDT[self.bandType[0]]
        return 1


    def scale2Per(self):
        pass

    # createPhase would be used on a complex SAR interferogram to create the phase portion 
    # of the image
    def createPhase(self):
        if self.bandType[0] != 'cfloat32' or self.numBands != 1:
            print 'Data type must be complex for phase calculation'
            return None
        else:
            phase = np.arctan2(np.imag(self.data[:,:,0]),np.real(self.data[:,:,0]))
            return phase


    def getPlanetMetadata(self):
        mName = self.imName.replace('.tif','_metadata.xml')
        print mName
        meta = etree.parse(mName)
        #for tag in meta.iter():
            #if not len(tag):
                #print tag.tag,tag.text
        rsf = meta.findall('//*/*/*/{http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}radiometricScaleFactor')
        rc = meta.findall('//*/*/*/{http://schemas.planet.com/ps/v1/planet_product_metadata_geocorrected_level}reflectanceCoefficient')
        rSF = []
        rC = []
        for i in range(0,len(rsf)):
            rSF.append(float(rsf[i].text))
            rC.append(float(rc[i].text))
        return rSF,rC




















