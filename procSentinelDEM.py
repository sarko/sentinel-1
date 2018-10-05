#!/usr/bin/python


import sys,os,re
import numpy as np
import datetime
import time
import glob
import csv
import saa_func_lib as saa
from math import ceil


# You will need to update these paths to your own if you want to use this 
# script
global baseSNAP
baseSNAP = '/home/sarko/snap/bin/gpt -q 14 -c 16G  '
xmlfi = open('/home/sarko/arkobin/mergeDEMgraph.xml','r')


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

global dirDefined
dirDefined = False

if len(sys.argv) == 1:
    print '******************************'
    print ' Usage:  procSentinelDEM.py <master input file> <slave input file> [-utm] [-ss subSwathNumber (default 1)] [-t tempdir] [-noorbit] [-dem demfile] [-subset ullon ullat lrlon lrlat]'
    print ' Note:  All files and tempdir should be absolutely pathed'
    print ' The subset feature currently does not function properly and should not be used '
    print ' Input files must be an S-1 SLC zip file '
    print '******************************'

UTM = False
tdir = './'
if len(sys.argv)>3:
    for i in range(3,len(sys.argv)):
        if sys.argv[i] == '-t':
            tdir = sys.argv[i+1]
            dirDefined = True
            i+=1
        elif sys.argv[i] == '-dem':
            extDEM = sys.argv[i+1]
            i+=1
        elif sys.argv[i] == '-ss':
            subSwath = []
            j = i
            while j<len(sys.argv)-1:
                print j
                if '-' not in sys.argv[j+1]: 
            	    subSwath.append('IW%s' % sys.argv[j+1])
            	    j+=1
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
        elif sys.argv[i] == '-utm':
            UTM=True

# Create geotiffs directory (if not already present)
if not os.path.exists('./geotiffs'):
    os.system('mkdir ./geotiffs')

if dirDefined == False:
    tdir = './temp/'
    if not os.path.exists(tdir):
        os.system('mkdir %s' % tdir)

def timestamp(date):
    return time.mktime(date.timetuple())

def calcUTMZone(x,y,geoTrans):
    cLon = geoTrans[0] + x/2*geoTrans[1]
    zone = int(ceil((-180 - cLon)/6))
    return zone
    


def tempDir(tdir,ifile,sfile,ss):
    td2 = '%s/%s-%s-%s' % (tdir,ifile[0:25],sfile[17:25],ss)
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
    print 'Splitting subswaths'
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
    print 'Performing TOPSAR Deburst'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_DB.dim')

def phaseToElevation(inData,td2):
    calFlag = 'PhaseToElevation ' 
    out = '-t %s/%s -PdemName=\"SRTM 1Sec HGT\" ' % (td2,inData.replace('.dim','_EL'))
    inD = '-Ssource=%s/%s' % (td2,inData)
    cmd = baseSNAP + calFlag + out + inD
    print 'Converting unwrapped phase to elevation'
    print cmd
    os.system(cmd)
    return '%s' % inData.replace('.dim','_EL.dim')

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
        inD = inD + ' -PdemName=\"SRTM 1Sec HGT\" -PalignToStandardGrid=true '
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
    print 'Importing from Snaphu'
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

    children = []
    tdirs = [None]*len(subSwath)
    msubs = [None]*len(subSwath)
    ssubs = [None]*len(subSwath)
    li = [None]*len(subSwath)

    for process in range(1,len(subSwath) + 1):
    	td2 = tempDir(tdir,mbaseGran,sbaseGran,subSwath[process-1])
    	tdirs[process-1] = td2
    	print td2
    	msplit = topsarSplit(master,subSwath[process-1],td2,subs)
    	print '\n\n'
    	ssplit = topsarSplit(slave,subSwath[process-1],td2,subs)
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
    	msubs[process-1] = mobOut
    	ssubs[process-1] = sobOut

# Need to fix this to complete the processing.  Need to know teh various outfiles
# that are resulting from fork above.
    dbouts = []
    dbouts = [None]*len(subSwath)
    for i in range(0,len(subSwath)):
        gcOut = backGeocoding(msubs[i],ssubs[i],tdirs[i],extDEM)
        print 'Time to Back Geocode: ',
        print(timestamp(datetime.datetime.now())-timestamp(lasttime))
        lasttime = datetime.datetime.now()
        print '\n\n'
        esdOut = applyESD(gcOut,tdirs[i])
        print '\n\n'
        intOut = createInterferogram(esdOut,tdirs[i])
        print '\n\n'
        dbouts[i] = topsarDeburst(intOut,tdirs[i])
        print '\n\n'

    #if subset == True:
        #subs = 'POLYGON((%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f,%3.2f %3.2f, %3.2f %3.2f))' % (ullon,ullat,lrlon,ullat,lrlon,lrlat,ullon,lrlat,ullon,ullat)
        #print subs
        #msubOut = applySubset(mobOut,subs,td2)
        #ssubOut = applySubset(sobOut,subs,td2)
    #else:

    print 'Processing TOPSAR Merge, Goldstein, and Multilook'
    mlOut = dbouts[0].replace('DB','DB_ML')
    
    fid = xmlfi.readlines()
    for i in range(0,len(fid)):
        if '<fileList>' in fid[i]:
            print 'identified file list'
            fid[i]  = '<fileList>'
            count = 0
            for x,y in zip(dbouts,tdirs):
                if count >0:
                    fid[i] = fid[i] + ','
                fid[i] = fid[i]+ '%s/%s' % (y,x)
                count += 1
            fid[i] = fid[i] + '</fileList>\n' 
        if '<file>' in fid[i]:
            print 'identified file tag'
            fid[i]  = '<file>'+tdirs[0]+'/'+mlOut+'</file>\n' 

    outfile = './temp.xml'
    of = open('temp.xml','w')
    for x in fid:
        of.write(x)
    of.close()

    # Process the temporary xml file using gpt
    os.system('%s %s' % (baseSNAP,outfile))

    unwOut = phaseUnwrap(mlOut,tdirs[0])
    print '\n\n'

    elOut = phaseToElevation(unwOut,tdirs[0])
    print '\n\n'

    tcCoh = applyTC(unwOut,tdirs[0],extDEM)
    print '\n\n'

    tcOut = applyTC(elOut,tdirs[0],extDEM)
    print '\n\n'

    # Convert the final elevation and coherence products to geotiffs
    startDir = os.getcwd()
    dDir = '%s/%s*EL_TC' % (tdirs[0],mbaseGran)
    dDir = glob.glob(dDir)[0]
    elFile = 'elevation-%s.tif ' % re.split('/',tdirs[0])[-1]
    coFile = 'coherence-%s.tif ' % re.split('/',tdirs[0])[-1]

    os.chdir(dDir)
    cmd = 'gdal_translate el*.img %s ' % elFile
    print cmd
    os.system(cmd)

    cmd = 'gdal_translate coh*.img %s ' % coFile
    print cmd
    os.system(cmd)

    if UTM:
        # Convert 4326 files to appropriate UTM zone
        (x,y,trans,proj) = saa.read_gdal_file_geo(saa.open_gdal_file('elevation-%s.tif' % re.split('/',tdirs[0])[-1]))
        z = calcUTMZone(x,y,trans)
        print('Converting products to UTM Zone %02d' % zone)
        cmd = 'gdalwarp -t_srs EPSG:326%02d %s temp.tif' % (zone,elFile)
        os.system(cmd)
        os.system('mv temp.tif %s' % elFile)
        cmd = 'gdalwarp -t_srs EPSG:326%02d %s temp.tif' % (zone,coFile)
        os.system(cmd)
        os.system('mv temp.tif %s' % coFile)

    #cmd = 'mv %s/*/*.tif geotiffs; rm -r %s' % (td2,td2)
    cmd = 'mv *.tif %s/geotiffs' % startDir
    print cmd
    os.system(cmd)
    os.chdir(startDir)
    # End of geotiff creation

else: 
    print('Input file could not be found')


