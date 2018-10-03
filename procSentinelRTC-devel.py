#!/usr/bin/python


import sys,os,re
import numpy as np
import datetime
import time
import glob
import csv


# You will need to update these paths to your own if you want to use this 
# script
global baseSNAP
baseSNAP = '/home/sarko/snap/bin/gpt -q 16 -c 24576M '
global extDEM
extDEM=''
noOrb = False
cleanTemp = False
procRTC=False
subset = False

if len(sys.argv) == 1:
	print '******************************'
	print ' Usage:  procSentinelTC.py <input file> [-t tempdir] [-dortc] [-noorbit] [-dem demfile] [-subset ullon ullat lrlon lrlat]'
	print ' Note:  All files and tempdir must be absolutely pathed'
	print ' Input file can either be an S-1 zip file or an asf-datapool*.csv file'
	print '******************************'


infiles = []

tdir = './'
if len(sys.argv)>2:
    for i in range(1,len(sys.argv)):
        if sys.argv[i] == '-t':
            tdir = sys.argv[i+1]
            i+=1
        elif sys.argv[i] == '-dem':
            extDEM = sys.argv[i+1]
            i+=1
        elif sys.argv[i]=='-noorbit':
            noOrb = True
        elif sys.argv[i]=='-dortc':
            procRTC = True
	elif sys.argv[i] == '-subset':
		ullon = float(sys.argv[i+1])
		ullat = float(sys.argv[i+2])
		lrlon = float(sys.argv[i+3])
		lrlat = float(sys.argv[i+4])
		subset = True
		i = i+4
        else: 
            infiles.append(sys.argv[i])
            i+=1


# Create temp and geotiff directory if they do not exist

if tdir == './':
    tdir = './temp'
    if not os.path.exists(tdir):
        os.system('mkdir %s' % tdir)

if not os.path.exists('./geotiffs'):
    os.system('mkdir ./geotiffs')


def timestamp(date):
    return time.mktime(date.timetuple())

def tempDir(tdir,ifile):
    td2 = '%s/%s' % (tdir,ifile)
    if not os.path.exists(tdir):
        os.system('mkdir %s' % tdir)
    if not os.path.exists(td2):
        os.system('mkdir %s' % td2)
    return td2

def applyCal(inData,td2):
    calFlag = 'Calibration -PoutputBetaBand=true -PoutputSigmaBand=false '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_CAL'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Calibration'
    os.system(cmd)
    return '%s' % inData.replace('.dim','_CAL.dim')

def removeThermalNoise(inData,td2):
    calFlag = 'ThermalNoiseRemoval '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_NR'))
    inD = '-SsourceProduct=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Thermal Noise Removal'
    os.system(cmd)
    return '%s' % inData.replace('.dim','_NR.dim')

def topsarDeburst(inData,td2):
    calFlag = 'TOPSAR-Deburst '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_DB'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Debursting TOPSAR Data'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_DB.dim')

def topsarDeburst1(granule,td2,baseGran):
    calFlag = 'TOPSAR-Deburst '
    #out = '-t %s/%s ' % (td2,inData.replace('.dim','_DB'))
    out = '-t %s/%s ' % (td2,baseGran+'_DB')
    inD = '-Ssource=%s' % granule
    cmd = baseSNAP + calFlag + out + inD
    print 'Debursting TOPSAR Data'
    print cmd
    os.system(cmd)
    return '%s' % baseGran+'_DB.dim'
    #return '%s' % inData.replace('.dim','_DB.dim')

def applySpeckleFilter(inData,td2):
    calFlag = 'Speckle-Filter  '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_SF'))
    inD = '-Ssource=%s/%s -PwindowSize=\'5x5\'' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Speckle Filter'
    os.system(cmd)
    return '%s' % inData.replace('.dim','_SF.dim')

def applyML(inData,td2):
    calFlag = 'Multilook -PnRgLooks=4 -PnAzLooks=1 '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_ML'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Multilook'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_ML.dim')

def applyOrbit(granule,td2,baseGran):
    aoFlag = 'Apply-Orbit-File '
    #oType = '-PcontinueOnFail=\"true\" -PorbitType=\'Sentinel Restituted (Auto Download)\' '
    oType = '-PcontinueOnFail=\"true\" -PorbitType=\'Sentinel Precise (Auto Download)\' -PpolyDegree=3 '
    out = '-t %s/%s ' % (td2,baseGran+'_OB')

    cmd = baseSNAP + aoFlag + out + oType + granule
    print 'Applying Precise Orbit file'
    print cmd
    os.system(cmd)
    return '%s' % baseGran+'_OB.dim'

def applyOrbit1(inData,td2):
    aoFlag = 'Apply-Orbit-File '
    #oType = '-PcontinueOnFail=\"true\" -PorbitType=\'Sentinel Restituted (Auto Download)\' '
    oType = '-PcontinueOnFail=\"true\" -PorbitType=\'Sentinel Precise (Auto Download)\' '
    #out = '-t %s/%s ' % (td2,baseGran+'_OB')
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_OB'))
    inD = '-Ssource=%s/%s' % (td2,inData)

    cmd = baseSNAP + aoFlag + out + oType + inD
    print 'Applying Precise Orbit file'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_OB.dim')
    #return '%s' % baseGran+'_OB.dim'

def applyTF(inData,td2,subsetFlag=0):
    calFlag = 'Terrain-Flattening '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_TF'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    if extDEM != '':
        inD = inD + ' -PdemName=\"External DEM\" -PexternalDEMFile=%s -PexternalDEMNoDataValue=0 -PreGridMethod=false ' % extDEM
    else:
        #inD = inD + ' -PdemName=\"SRTM 3Sec\" '
        inD = inD + ' -PdemName=\"SRTM 1Sec HGT\" -PreGridMethod=false '
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Terrain Flattening -- This will take some time'
    print cmd
    os.system(cmd)
    if subsetFlag==0:
    	return '%s' % inData.replace('.dim','_TF.dim')
    else:
    	return '%s' % inData.replace('.dim','_TF.dim')

def applySubset(inData,subpoly,td2):
    calFlag = 'Subset -PgeoRegion=\"%s\" -PcopyMetadata=true ' % subpoly
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_SU'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Subsetting'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_SU.dim')

def applyTC(inData,td2):
    calFlag = 'Terrain-Correction -PalignToStandardGrid=true '
    out = '-t %s/%s  ' % (td2,inData.replace('.dim','_TC'))
    #out = '-t %s/%s -f HDF5 ' % (td2,inData.replace('.dim','_TC'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    if extDEM != '':
        inD = inD + ' -PdemName=\"External DEM\" -PexternalDEMFile=%s -PexternalDEMNoDataValue=0 ' % extDEM
    else:
        #inD = inD + ' -PdemName=\"SRTM 3Sec\" '
        #inD = inD + ' -PdemName=\"SRTM 1Sec HGT\" -PimgResamplingMethod=\"NEAREST_NEIGHBOUR\" '
        inD = inD + ' -PdemName=\"SRTM 1Sec HGT\" '
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Terrain Correction -- This will take some time'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_TC.dim')

def parseCSV(csvfile):
	data = open(csvfile,'r').readlines()[1:]
	infiles = []
        t = list(csv.reader(data))
        print len(t)
	for line in t:
                for item in line:
                    if 'datapool' in item:
		        infiles.append(item)
	return infiles

global infile 
infile = sys.argv[1]

if '.zip' in sys.argv[1]:
	#infiles = [sys.argv[1]]
        pass
elif '.csv' in sys.argv[1]:
	infiles = parseCSV(sys.argv[1])
else:
	sys.exit('Did not understand input file')

for infile in infiles:
        fin = infile
        infile = re.split('/',infile)[-1]
        print 'Infile is: %s' % infile
	# Need to figure out where input file is
        baseSen = os.getcwd()
        print fin
        print '%s/%s' % (baseSen,infile)

        if os.path.exists('%s/%s' % (baseSen,infile)):
                pass
        else:
                cmd = 'wget -c %s' % fin
                print cmd
                os.system(cmd) 

        #if 'S1A' in infile:
	        #baseSen = '/hugeslice/datapool/prod/data/GRD/SA/'
        #else:
	        #baseSen = '/hugeslice/datapool/prod/data/GRD/SB/'
	#if 'SLC' in infile:
		#infile = re.split('/',infile.replace('SLC_','GRDH'))[-1]
		#inf = infile.split('_')
		#inf[4] = '*'
		#inf[5] = '*'
		#inf[8] = '*'
		#infile = '_'.join(inf)
		#orbit = int(re.split('_',infile)[6])
		#orbit = str(orbit - orbit%1000)
		#inf = baseSen + orbit + '/' + infile
		#infile = glob.glob(inf)[0]
		#print infile
        if '.zip' in infile: 
		#orbit = int(re.split('_',infile)[6])
		#orbit = str(orbit - orbit%1000)
		infile = baseSen + '/' + infile
	else:
		orbit = int(re.split('_',infile)[6])
		orbit = str(orbit - orbit%1000)
		infile = baseSen + orbit + '/' + infile

        print 'Fully pathed infile is: %s' % infile
	if os.path.exists(infile):
		print infile
		baseGran = re.split('/',infile.replace('.zip',''))[-1]
		start = datetime.datetime.now()
		td2 = tempDir(tdir,baseGran)
		print td2
                #if 'SLC' in infile:
                    #print 'Debursting SLC product'
                    #calOut = topsarDeburst1(infile,td2,baseGran)

		if noOrb == False:
    			obOut = applyOrbit(infile,td2,baseGran)
    			#obOut = applyOrbit1(calOut,td2)
    			print obOut
    			print 'Time to fix orbit: ',
    			lasttime = datetime.datetime.now()
    			print(timestamp(datetime.datetime.now())-timestamp(start))
			nrOut = removeThermalNoise(obOut,td2)
    			calOut = applyCal(nrOut,td2)
		else:
    			calOut = applyCal(infile,td2)
		
		print calOut
		print 'Time to calibrate: ',
		print(timestamp(datetime.datetime.now())-timestamp(lasttime))
		lasttime = datetime.datetime.now()

                if 'SLC' in infile:
                    print 'Debursting SLC product'
                    calOut = topsarDeburst(calOut,td2)

		if subset == True:
			subs = 'POLYGON((%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f, %3.2f %3.2f))' % (ullon,ullat,lrlon,ullat,lrlon,lrlat,ullon,lrlat,ullon,ullat)
			print subs
			subOut = applySubset(calOut,subs,td2)
		else:
			subOut = calOut 

                # This is really speckle filtering even though it looks like calibration
		lasttime = datetime.datetime.now()
                print 'Speckle filtering'
                #subOut = applySpeckleFilter(subOut,td2)
		print 'Time to Speckle Filter ',
		print(timestamp(datetime.datetime.now())-timestamp(lasttime))

		lasttime = datetime.datetime.now()
                if 'SLC' in infile:
                    print 'Multilooking SLC product'
		    subOut = applyML(subOut,td2) 

		print 'Time to multilook ',
		print(timestamp(datetime.datetime.now())-timestamp(lasttime))

		lasttime = datetime.datetime.now()

		if procRTC == True:
                        if subset == True:
				tfOut = applyTF(subOut,td2,1)
			else:
				tfOut = applyTF(subOut,td2)
			print tfOut
			print 'Time to terrain flatten: ',
			print(timestamp(datetime.datetime.now())-timestamp(lasttime))
			lasttime = datetime.datetime.now()
			tcOut = applyTC(tfOut,td2)
		else:
			tcOut = applyTC(subOut,td2)

		print tcOut
		print 'Time to terrain correct: ',
		print(timestamp(datetime.datetime.now())-timestamp(lasttime))
		print 'Total processing time: ',
		print(timestamp(datetime.datetime.now())-timestamp(start))
		
		if cleanTemp == True:
    			cmd = 'cd %s; rm -r *OB.* *CAL.* *TF.*' % td2
    			print cmd
    			os.system(cmd)

		if procRTC == True and 'IW' in infile:
			ifile = 'Gamma0_VV.img'
			ifile2 = 'Gamma0_VH.img'
                        bgran2 = baseGran.replace('1SDV','1SDH')
                elif procRTC == True and '1SDH' in infile:
			ifile = 'Gamma0_VV.img'
			ifile2 = 'Gamma0_VH.img'
                        bgran2 = baseGran.replace('1SDV','1SDH')
		else:
			ifile = 'Beta0_VV.img'
			ifile2 = 'Beta0_VH.img'
			#ifile = 'Sigma0_VV.img'
			#ifile2 = 'Sigma0_VH.img'
                        bgran2 = baseGran.replace('1SDV','1SDH')
                    

		# This line is for Cleveland Volcano
		#cmd = 'cd %s/%s*TC.data;gdal_translate -projwin -170.2 52.94 -169.8 52.7 Gamma0_VV.img %s.tif' % (td2,baseGran,baseGran)
		# This line is for Calbuco
		if subset==True:
			cmd = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS -projwin %f %f %f %f  %s %s.tif' % (td2,baseGran,ullon,ullat,lrlon,lrlat,ifile,baseGran)
			cmd2 = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS -projwin %f %f %f %f  %s %s.tif' % (td2,baseGran,ullon,ullat,lrlon,lrlat,ifile2,bgran2)
		else:
			cmd = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS  %s %s.tif' % (td2,baseGran,ifile,baseGran)
			cmd2 = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS  %s %s.tif' % (td2,baseGran,ifile2,bgran2)

		print cmd
		os.system(cmd)
		print cmd2
		os.system(cmd2)

                cmd = 'mv %s/*/*.tif geotiffs; rm -r %s' % (td2,td2)
                #cmd = 'mv %s/*/*.tif geotiffs' % td2
                print cmd
                os.system(cmd)

	else: 
		print('Input file could not be found')


