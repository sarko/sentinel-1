#!/usr/bin/env python



import numpy as np
from lxml import etree
import os, re, sys
import matplotlib.pyplot as plt
import zipfile 
from scipy.misc import imresize
from osgeo import gdal
import cv2

import saa_func_lib as saa



class s1Safe:

    def __init__(self,fName):
        self.name = fName
        self.base = fName.replace('.zip','')

        if '1SDV' in self.name:
            self.polarization = 'dual'
        else:
            self.polarization = 'single'
        print('Loading file %s as %s polarization' % (self.name,self.polarization))

        self.fi = zipfile.ZipFile(self.name)

        self.fnames = self.fi.namelist()

        for na in self.fnames:
            if 'calibration/calibration' in na and 'grd-vv' in na:
                self.vvcal = na
                print('VV Calibration file is %s' % na)
            elif 'calibration/calibration' in na and 'grd-vh' in na:
                self.vhcal = na
                print('VH Calibration file is %s' % na)

        # Get SigmaNought Cal Matrices
        self.vvSig0 = self.getCalMatrix(self.vvcal)
        if self.polarization == 'dual':
            self.vhSig0 = self.getCalMatrix(self.vhcal)


    def getCalMatrix(self,calFile):
        vvhan = self.fi.open(calFile)
        self.tree = etree.parse(vvhan)
        
        line = self.tree.findall('calibrationVectorList/calibrationVector/line')
        pix = self.tree.findall('calibrationVectorList/calibrationVector/pixel')
        sig = self.tree.findall('calibrationVectorList/calibrationVector/sigmaNought')

        pixels = re.split('\s+',pix[0].text)

        pixels = [float(p) for p in pixels]
        lines = [int(l.text) for l in line]
        
        sig0 = np.empty((len(lines),len(pixels)))
        for i in range(0,len(lines)):
            s0 = re.split('\s+',sig[i].text)
            sig0[i,:] = [float(s) for s in s0]

        #print max(lines),max(pixels)
        sig0 = cv2.resize(sig0,(int(max(lines)),int(max(pixels))+1))

        return sig0


    def calibrate(self):
        for na in self.fnames:
            if 'measurement' in na and 'vv' in na:
                self.vvfile = '/vsizip/%s/%s' % (self.name,na)
            elif 'measurement' in na and 'vh' in na:
                self.vhfile = na

        ds = gdal.Open(self.vvfile)
        bd = ds.GetRasterBand(1)

        data = bd.ReadAsArray()

        # Multiply by cal array
        (h,w) = data.shape
        
        d2 = data.astype(np.float32) / (self.vvSig0[0:w,0:h].astype(np.float32).transpose())
        #d2 = np.sqrt(d2)

        np.putmask(d2,d2>0.8,0.8)
        d2 = ((d2-d2.min())/(d2.max()-d2.min())*255).astype(np.uint8)

        # Write the data to ds2

        driver = gdal.GetDriverByName('MEM')
        (y,x) = d2.shape
        gcps = ds.GetGCPs()
        gcpproj = ds.GetGCPProjection()
        ds2 = driver.Create('',x,y,1,gdal.GDT_Byte)
        ds2.SetGCPs(gcps,gcpproj)
        ds2.GetRasterBand(1).WriteArray(d2)

        outfile = self.name.replace('.zip','-warp.tif')
        print('Writing output file: %s' % outfile)
        gdal.Warp(outfile,ds2,format='GTiff',creationOptions=['COMPRESS=LZW'],tps=True,dstSRS='EPSG:32609')

        ds2 = None
        d2 = None
        self.vvSig = None
        self.vhSig = None

       
    def createColorDecomp(vvfile,vhfile):
    	cutoff = .057
    	outfile = vvfile.replace('1SDV','COLOR')
	
    	v = geoImage(vvfile)
    	h = geoImage(vhfile)
	
    	v.data = v.data.astype(np.complex64)
    	h.data = h.data.astype(np.complex64)
	
    	red = (np.sqrt((v.data)**2 - 3*(h.data)**2)).real
    	green = h.data.real
    	blue = v.data.real
	
    	np.putmask(blue,h.data>cutoff,0)
    	np.putmask(red,h.data<cutoff,0)
	
    	rcut = red.mean() + 2*red.std()
    	gcut = green.mean() + 2*green.std()
    	bcut = blue.mean() + 2*blue.std()
	
    	np.putmask(red,red>rcut,rcut)
    	np.putmask(blue,blue>bcut,bcut)
    	np.putmask(green,green>gcut,gcut)
	
    	redByte = scaleToByte(red[:,:,0])
    	blueByte = scaleToByte(blue[:,:,0])
    	greenByte = scaleToByte(green[:,:,0])
	
    	#for i in range(0,blue.shape[0]):
    	#    for j in range(0,blue.shape[1]):
    	#        if blueByte[i,j] == 0 and redByte[i,j] == 0 and greenByte[i,j] < 75:
    	#            blueByte[i,j] = 3*greenByte[i,j]
	
    	saa.write_gdal_file_rgb(outfile,v.geoTransform,v.projection,redByte,greenByte,blueByte)


        


