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
baseSNAP = '/home/sarko/snap/bin/gpt '
global extDEM
extDEM=''
global subSwath
subSwath = 'IW1'
noOrb = False
cleanTemp = True
procRTC=False
subset = False
global subs
subs = ''

if len(sys.argv) == 1:
    print '******************************'
    print ' Usage:  procSentinelIntf.py <master input file> <slave input file> [-ss subSwathNumber (default 1)] [-t tempdir] [-noorbit] [-dem demfile] [-subset ullon ullat lrlon lrlat]'
    print ' Note:  All files and tempdir must be absolutely pathed'
    print ' Input file must be an S-1 zip file '
    print '******************************'



tdir = './'
if len(sys.argv)>3:
    for i in range(3,len(sys.argv)):
        if sys.argv[i] == '-t':
            tdir = sys.argv[i+1]
            i+=1
        elif sys.argv[i] == '-dem':
            extDEM = sys.argv[i+1]
            i+=1
        elif sys.argv[i] == '-ss':
            subSwath = 'IW%s' % sys.argv[i+1]
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
            subs = 'POLYGON((%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f, %3.2f %3.2f))' % (ullon,ullat,lrlon,ullat,lrlon,lrlat,ullon,lrlat,ullon,ullat)
            subset = True
            i = i+4

def timestamp(date):
    return time.mktime(date.timetuple())

def tempDir(tdir,ifile,sfile):
    td2 = '%s/%s-%s' % (tdir,ifile[0:25],sfile[17:25])
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

def topsarSplit(inData,ss,td2,subs):
    calFlag = 'TOPSAR-Split -Psubswath=%s -PselectedPolarisations=VV ' % ss
    if subs != '':
        calFlag = calFlag + '-PwktAoi=\"%s\" ' % subs
    out = '-t %s/%s ' % (td2,inData.replace('.zip','_TS'))
    inD = '-Ssource=%s' % inData
    cmd = baseSNAP + calFlag + out + inD
    print 'Spliting subswaths'
    print cmd
    os.system(cmd)
    #This function uses .zip since it is the first step
    return '%s' % inData.replace('.zip','_TS.dim')

def applyOrbit(inData,td2):
    aoFlag = 'Apply-Orbit-File '
    oType = '-PcontinueOnFail=\"true\" -PorbitType=\'Sentinel Precise (Auto Download)\' '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_OB'))

    cmd = baseSNAP + aoFlag + out + oType + ' -Ssource=%s/%s' % (td2,inData)
    print 'Applying Precise Orbit file'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_OB.dim')

def applyTF(inData,td2,subsetFlag=0):
    calFlag = 'Terrain-Flattening '
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_TF'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    if extDEM != '':
        inD = inD + ' -PdemName=\"External DEM\" -PexternalDEMFile=%s -PexternalDEMNoDataValue=0 ' % extDEM
    else:
        #inD = inD + ' -PdemName=\"SRTM 3Sec\" '
        inD = inD + ' -PdemName=\"SRTM 1Sec HGT\" '
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Terrain Flattening -- This will take some time'
    print cmd
    os.system(cmd)
    if subsetFlag==0:
        #return '%s' % inData.replace('ML','ML_TF')
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

def backGeocoding(inData1,inData2,td2,dem=''):
    calFlag = 'Back-Geocoding ' 
    if dem != '':
        calFlag = calFlag + '-PdemName=\"External DEM\" -PexternalDEMFile=%s ' % dem
    else: 
        calFlag = calFlag + '-PdemName=\"SRTM 1Sec HGT\" ' 

    out = '-t %s/%s ' % (td2,inData1.replace('.dim','_BG'))
    inD = '-SsourceProducts=\"%s/%s\" \"%s/%s\" ' % (td2,inData1,td2,inData2)
    cmd = baseSNAP + calFlag + out + inD
    print 'Back Geocoding'
    print cmd
    os.system(cmd)
    return '%s' % inData1.replace('.dim','_BG.dim')

def applyESD(inData,td2):
    calFlag = 'Enhanced-Spectral-Diversity ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_ESD'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Performing ESD'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_ESD.dim')

def createInterferogram(inData,td2):
    calFlag = 'Interferogram ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_INT'))
    inD = '-SsourceProduct=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Creating Interferogram'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_INT.dim')

def topsarDeburst(inData,td2):
    calFlag = 'TOPSAR-Deburst ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_DB'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Creating Interferogram'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_DB.dim')

def topoPhaseRemoval(inData,td2,dem=''):
    calFlag = 'TopoPhaseRemoval ' 
    if dem != '':
        calFlag = calFlag + '-PdemName=\"External DEM\" -PexternalDEMFile=%s ' % dem
    else: 
        calFlag = calFlag + '-PdemName=\"SRTM 1Sec HGT\" ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_Topo'))
    inD = '-SsourceProduct=\"%s/%s\" ' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Removing Topographic Phase'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_Topo.dim')

def goldsteinFilter(inData,td2):
    calFlag = 'GoldsteinPhaseFiltering -PcoherenceThreshold=0.2 ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_GF'))
    inD = '-SsourceProduct=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Goldstein Phase Filtering'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_GF.dim')

def applyTC(inData,td2,dem):
    calFlag = 'Terrain-Correction '
    out = '-t %s/%s  ' % (td2,inData.replace('.dim','_TC'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    if extDEM != '':
        inD = inD + ' -PoutputComplex=true -PdemName=\"External DEM\" -PexternalDEMFile=%s -PexternalDEMNoDataValue=0 ' % extDEM
    else:
        #inD = inD + ' -PdemName=\"SRTM 3Sec\" '
        inD = inD + ' -PoutputComplex=true -PdemName=\"SRTM 1Sec HGT\" -PimgResamplingMethod=\"NEAREST_NEIGHBOUR\" '
    cmd = baseSNAP + calFlag + out + inD
    print 'Applying Terrain Correction -- This will take some time'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_TC.dim')

def phaseUnwrap(inData,td2):
    # First export to SNAPHU format
    calFlag = 'SnaphuExport ' 
    out = '-PtargetFolder=%s ' % td2
    inD = '-SsourceProduct=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Exporting for Snaphu'
    print cmd
    os.system(cmd)

    # Actually call snaphu
    snaphuDir = '%s/%s' % (td2,inData.replace('.dim',''))
    snaphuConf = '%s/snaphu.conf' % snaphuDir
    han = open(snaphuConf,'r')
    sData = han.readlines()
    han.close()
    han = open(snaphuConf,'w')
    for i in range(0,len(sData)):
        if 'LOGFILE' in sData[i]:
            print 'Found logfile in snaphu.conf'
            sData[i] = sData[i].replace('LOGFILE','#LOGFILE')
        if i==6:
            snaphuCmd = sData[i].replace('#   ','')
        han.write(sData[i])
    han.close()
    cmd = 'cd %s;%s' % (snaphuDir,snaphuCmd)
    print cmd
    os.system(cmd)

    # Import from SNAPHU format
    calFlag = 'SnaphuImport ' 
    out = '-t %s/%s ' % (td2,inData.replace('.dim','_UNW'))
    snaphuFile = glob.glob('%s/Unw*.hdr' % snaphuDir)[0]
    inD = '-SsourceProducts=\"%s/%s\" \"%s\" ' % (td2,inData,snaphuFile)
    cmd = baseSNAP + calFlag + out + inD
    print 'Exporting for Snaphu'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_UNW.dim')

def parseCSV(csvfile):
    data = open(csvfile,'r').readlines()[1:]
    infiles = []
    t = list(csv.reader(data))
    print len(t)
    for line in t:
        #infiles.append(re.split(',',line)[0].replace('\"','')+'.zip')
        infiles.append(line[26])
    return infiles

global infile 
master = sys.argv[1]
slave = sys.argv[2]

if '.zip' in sys.argv[1]:
    infiles = [sys.argv[1]]
elif '.csv' in sys.argv[1]:
    infiles = parseCSV(sys.argv[1])
else:
    sys.exit('Did not understand input file')

if os.path.exists(master) and os.path.exists(slave):
    print 'Processing interferogram for %s and %s' % (master, slave)
    mbaseGran = re.split('/',master.replace('.zip',''))[-1]
    sbaseGran = re.split('/',slave.replace('.zip',''))[-1]

    start = datetime.datetime.now()
    td2 = tempDir(tdir,mbaseGran,sbaseGran)

    print td2

    msplit = topsarSplit(master,subSwath,td2,subs)
    print '\n\n'
    ssplit = topsarSplit(slave,subSwath,td2,subs)
    print '\n\n'

    print msplit,ssplit

    mobOut = applyOrbit(msplit,td2)
    print '\n\n'
    sobOut = applyOrbit(ssplit,td2)
    print '\n\n'
    print mobOut,sobOut
    print 'Time to fix orbit: ',
    lasttime = datetime.datetime.now()
    print(timestamp(datetime.datetime.now())-timestamp(start))
    print '\n\n'
    
    #if subset == True:
        #subs = 'POLYGON((%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f, %3.2f %3.2f))' % (ullon,ullat,lrlon,ullat,lrlon,lrlat,ullon,lrlat,ullon,ullat)
        #print subs
        #msubOut = applySubset(mobOut,subs,td2)
        #ssubOut = applySubset(sobOut,subs,td2)
    #else:
    msubOut = mobOut 
    ssubOut = sobOut 

    gcOut = backGeocoding(msubOut,ssubOut,td2,extDEM)
    print 'Time to Back Geocode: ',
    print(timestamp(datetime.datetime.now())-timestamp(lasttime))
    lasttime = datetime.datetime.now()

    print '\n\n'
    esdOut = applyESD(gcOut,td2)

    print '\n\n'
    intOut = createInterferogram(esdOut,td2)
    print '\n\n'
    dbOut = topsarDeburst(intOut,td2)
    print '\n\n'
    topoOut = topoPhaseRemoval(dbOut,td2,extDEM)
    print '\n\n'
    gfOut = goldsteinFilter(topoOut,td2)
    print '\n\n'
    mlOut = applyML(gfOut,td2)
    print '\n\n'
    unwOut = phaseUnwrap(mlOut,td2)
    print '\n\n'
    tcOut = applyTC(unwOut,td2,extDEM)
    print '\n\n'

    cmd = 'cd %s/%s*TC.data;makeSNAPIntf.py i*.img q*.img ' % (td2,mbaseGran)
    print cmd
    os.system(cmd)

    cmd = 'cd %s/%s*TC.data;gdal_translate coh*.img coh-%s.tif ' % (td2,mbaseGran,re.split('/',td2)[-1])
    print cmd
    os.system(cmd)

    cmd = 'cd %s/%s*TC.data;gdal_translate Unw*.img unwrapped-%s.tif ' % (td2,mbaseGran,re.split('/',td2)[-1])
    print cmd
    os.system(cmd)

    cmd = 'cd %s/%s*TC.data;mv phase.tif phase-%s.tif ' % (td2,mbaseGran,re.split('/',td2)[-1])
    print cmd
    os.system(cmd)
    cmd = 'cd %s/%s*TC.data;mv amplitude.tif amp-%s.tif ' % (td2,mbaseGran,re.split('/',td2)[-1])
    print cmd
    os.system(cmd)
    
    #if subset==True:
        #cmd = 'cd %s/%s*TC.data;makeSNAPIntf.py i*.img q*.img ' % (td2,baseGran)
        #cmd2 = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS -projwin %f %f %f %f  %s %s.tif' % (td2,baseGran,ullon,ullat,lrlon,lrlat,ifile2,bgran2)
    #else:
        #cmd = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS  %s %s.tif' % (td2,baseGran,ifile,baseGran)
        #cmd2 = 'cd %s/%s*TC.data;gdal_translate -co COMPRESS=PACKBITS  %s %s.tif' % (td2,baseGran,ifile2,bgran2)
    #print cmd
    #os.system(cmd)
    #print cmd2
    #os.system(cmd2)

    cmd = 'mv %s/*/*.tif geotiffs; rm -r %s' % (td2,td2)
    #cmd = 'mv %s/*/*.tif geotiffs' % td2
    print cmd
    #os.system(cmd)

else: 
    print('Input file could not be found')


