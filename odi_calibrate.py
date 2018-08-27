#!/usr/bin/env python

""""odi_calibrate.py
Based on a set of sm and cl scripts written by Steven Janowiecki
Intented as an alternative to QuickReduce photometric calibration

based on the images in the working directory, downloads SDSS stars
in the field and uses them to perform photometric calibration

Also uses code from an SDSS provided SQL query script
"""

import os
import sys
import numpy as np

formats = ['csv','xml','html']

astro_url='http://skyserver.sdss3.org/public/en/tools/search/x_sql.aspx'
public_url='http://skyserver.sdss3.org/public/en/tools/search/x_sql.aspx'

default_url=public_url
default_fmt='csv'

def usage(status, msg=''):
    "Error message and usage"
    print(__doc__)
    if msg:
        print('-- ERROR: %s' % msg)
    sys.exit(status)

def filtercomment(sql):
    "Get rid of comments starting with --"
    import os
    fsql = ''
    for line in sql.split('\n'):
        fsql += line.split('--')[0] + ' ' + os.linesep;
    return fsql

def query(sql,url=default_url,fmt=default_fmt):
    "Run query and return file object"
    import urllib.request, urllib.parse, urllib.error
    fsql = filtercomment(sql)
    params = urllib.parse.urlencode({'cmd': fsql, 'format': fmt})
    return urllib.request.urlopen(url+'?%s' % params)    

def write_header(ofp,pre,url,qry):
    import  time
    ofp.write('%s SOURCE: %s\n' % (pre,url))
    ofp.write('%s TIME: %s\n' % (pre,time.asctime()))    
    ofp.write('%s QUERY:\n' % pre)
    for l in qry.split('\n'):
        ofp.write('%s   %s\n' % (pre,l))

def download_sdss(img1, img2, gmaglim = 21, gmagbrlim = 16):
    try: 
        import sys
        import numpy as np
        from astropy.io import fits
        from astropy import wcs
        import os
        import string
    except ImportError:
        print("You should 'pip install astropy' before you try to run this program") 

    print('fetching SDSS data from \n--> '+public_url)
    
    image = img1
    
    # read in the image header and save it to a variable for non-destructive editing
    hdulist = fits.open(image)
    hdr = hdulist[0].header
    hdulist.close()
    # get the image dimensions
    xdim = hdr['NAXIS1']
    ydim = hdr['NAXIS2']

    # and find the image center
    xc = xdim/2.0
    yc = ydim/2.0

    # get the CD matrix keywords
    cd11 = hdr['CD1_1']
    cd22 = hdr['CD2_2']
    # try to load cd12 and cd21, if they don't exist, set them to zero
    try :
        cd12 = hdr['CD1_2']
    except:
        cd12 = 0.0
    try :
        cd21 = hdr['CD2_1']
    except:
        cd21 = 0.0

    # get rid of keywords starting with PV, they don't work with astropy.wcs
    # and steven thinks they are redundant anyway
    pvlist = hdr['PV*']
    for pv in pvlist:
        hdr.remove(pv)
        
    
    # open the second fits image
    hdulist = fits.open(img2)
    hdr_r = hdulist[0].header
    hdulist.close()
    
    pvlist = hdr_r['PV*']
    for pv in pvlist:
        hdr_r.remove(pv)
    
    # Parse the WCS keywords in the primary HDU
    w = wcs.WCS(hdr)
    w_r = wcs.WCS(hdr_r)

    # Some pixel coordinates of interest (these are the image centers)
    pixcrd = np.array([[xc,yc]], np.float_)

    # Convert pixel coordinates to world coordinates
    # The second argument is "origin" -- in this case we're declaring we
    # have 1-based (Fortran-like) coordinates.
    world = w.wcs_pix2world(pixcrd, 1)
    # print(world)    
    rac = world[0][0]
    decc = world[0][1]

    # get the biggest radius of the image in arcminutes
    pixscal1 = 3600*abs(cd11)
    pixscal2 = 3600*abs(cd22)
    xas = pixscal1 * xdim # in arcseconds
    yas = pixscal2 * ydim
    xam = xas/60    # to arcminutes
    yam = yas/60
    #print(xam,yam)
    #radius for query: sqrt2 = 1.414
    sizeam = 1.414*(xam+yam)/4
    # print sizeam

    if not os.path.isfile(image[:-5]+'.sdss'):
        # build the SDSS query
        qry = "select O.ra, O.dec, O.psfMag_u, O.psfMagErr_u, O.psfMag_g, \nO.psfMagErr_g, O.psfMag_r, O.psfMagErr_r, O.psfMag_i, \nO.psfMagErr_i, O.psfMag_z, O.psfMagErr_z, O.probPSF \nfrom \ndbo.fGetNearbyObjEq("+repr(rac)+","+repr(decc)+","+repr(sizeam)+") \nas N inner join PhotoObjAll as O on O.objID = N.objID order by N.distance"
    
        # print it to the terminal
        print('with query\n-->', qry)
        url = default_url
        fmt = default_fmt
        writefirst = 1
        verbose = 0
    
        # actually do the query

        ofp = open(image[:-5]+'.sdss','w+')
        if verbose:
            write_header(ofp,'#',url,qry)
        file_ = query(qry,url,fmt)
        # Output line by line (in case it's big)
        line = file_.readline()
        if line.startswith("ERROR"): # SQL Statement Error -> stderr
            ofp = sys.stderr
        if writefirst:
            ofp.write(string.rstrip(line)+os.linesep)
        line = file_.readline()
        while line:
            ofp.write(string.rstrip(line)+os.linesep)
            line = file_.readline()
        ofp.close()
    
    # read in the results
    ras,decs,psfMag_u,psfMagErr_u,psfMag_g,psfMagErr_g,psfMag_r,psfMagErr_r,psfMag_i,psfMagErr_i,psfMag_z,psfMagErr_z = np.loadtxt(image[:-5]+'.sdss',usecols=(0,1,2,3,4,5,6,7,8,9,10,11), unpack=True, delimiter=',', skiprows=2)
    probPSF = np.loadtxt(image[:-5]+'.sdss', usecols=(12,), dtype=int, unpack=True, delimiter=',', skiprows=2)

    coords2 = list(zip(ras,decs))
    pixcrd2 = w.wcs_world2pix(coords2, 1)
    pixcrd2_r = w_r.wcs_world2pix(coords2, 1)

    # keep things that are actually stars (defined as being psf's) and with the right magnitude range (arbitrary)

    keep_stars = ((probPSF == 1) & (psfMag_g < gmaglim) & (psfMagErr_g <0.1) & (psfMag_g > gmagbrlim))
    print('keeping', len(np.where(keep_stars)[0]), 'stars of', len(psfMag_g), 'sources')
    
    # then write out separate files for g and i
    with open(image[:-5]+'.sdssxy','w+') as f1:
        print("# x_g y_g ra dec u uerr g gerr r rerr i ierr z zerr (all psfmags)", file=f1)
        for i,id in enumerate(np.where(keep_stars)[0]):
            if 100.0 < pixcrd2[id][0] < xdim-100.0 and 100.0 < pixcrd2[id][1] < ydim-100.0:
                print(pixcrd2[id][0], pixcrd2[id][1], ras[id], decs[id], psfMag_u[id], psfMagErr_u[id], psfMag_g[id], psfMagErr_g[id], psfMag_r[id], psfMagErr_r[id], psfMag_i[id], psfMagErr_i[id], psfMag_z[id], psfMagErr_z[id], file=f1)
            
    with open(img2[:-5]+'.sdssxy','w+') as f1:
        print("# x_r y_r ra dec u uerr g gerr r rerr i ierr z zerr (all psfmags)", file=f1)
        for i,id in enumerate(np.where(keep_stars)[0]):
            if 100.0 < pixcrd2_r[id][0] < xdim-100.0 and 100.0 < pixcrd2_r[id][1] < ydim-100.0:
                print(pixcrd2_r[id][0], pixcrd2_r[id][1], ras[id], decs[id], psfMag_u[id], psfMagErr_u[id], psfMag_g[id], psfMagErr_g[id], psfMag_r[id], psfMagErr_r[id], psfMag_i[id], psfMagErr_i[id], psfMag_z[id], psfMagErr_z[id], file=f1)

# def linear(x, m, b):
#     y = m*x + b
#     return y

def getfwhm(image, radius=4.0, buff=7.0, width=5.0, rplot=15.0, center='yes'):
    '''
    Get a fwhm estimate for the image using the SDSS catalog stars and IRAF imexam (SLOW, but works)
    Adapted from Kathy's getfwhm script (this implementation is simpler in practice)
    '''
    from pyraf import iraf
    import numpy as np
    import os
    
    outputfile = image[:-5]+'_fwhmCAL.log'
    coords = image[:-5]+'.sdssxy'
    
    iraf.tv.rimexam.setParam('radius',radius)
    iraf.tv.rimexam.setParam('buffer',buff)
    iraf.tv.rimexam.setParam('width',width)
    iraf.tv.rimexam.setParam('rplot',rplot)
    iraf.tv.rimexam.setParam('center',center)
    # fit a gaussian, rather than a moffat profile (it's more robust for faint sources)
    iraf.tv.rimexam.setParam('fittype','gaussian')
    iraf.tv.rimexam.setParam('iterati',1)
    
    if not os.path.isfile(outputfile):
        iraf.tv.imexamine(image, frame=10, logfile = outputfile, keeplog = 'yes', defkey = "a", nframes=0, imagecur = coords, wcs = "logical", use_display='no',  StdoutG='/dev/null',mode='h')
    outputfile_clean = open(outputfile.replace('.log','_clean.log'),"w")
    for line in open(outputfile,"r"):
        if not 'INDEF' in line:
            outputfile_clean.write(line)
        if 'INDEF' in line:
            outputfile_clean.write(line.replace('INDEF','999'))
    outputfile_clean.close()
    os.rename(outputfile.replace('.log','_clean.log'),outputfile)
    #
    # # unfortunately we have to toss the first measured fwhm value from the median because of the file format
    # # gfwhm = np.genfromtxt(outputfile, usecols=(3,), skip_header=4, skip_footer=3, unpack=True)
    gfwhm = np.loadtxt(outputfile, usecols=(10,), unpack=True)
    # hdulist = ast.io.fits.open(image)
    # seeing = hdulist[0].header['FWHMSTAR']
    # gfwhm = seeing/0.11
    print('median gwfhm in ',image+': ',np.median(gfwhm),'pixels')# (determined via QR)'
    return np.median(gfwhm)

    
def ota_zp(x, y, gi, di, x_ota, y_ota):
    filterName = 'r'
    ota_dict = {2:[350,4500], 3:[4500,8800], 4:[8800,13000]} 
    print(ota_dict[x_ota], ota_dict[y_ota])
    keep_ota = np.where((x>ota_dict[x_ota][0])&(x<ota_dict[x_ota][1])&(y>ota_dict[y_ota][0])&(y<ota_dict[y_ota][1]))
    gi_new = gi[keep_ota]
    di_new = di[keep_ota]
    
    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi_new, di_new, 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    eps_gi, zp_i, std_eps_gi, std_zp_i = p[0], p[1], perr[0], perr[1]
    print('ZP for OTA['+repr(x_ota)+','+repr(y_ota)+']')
    print('eps_g'+filterName+'     std_eps_g'+filterName+' zp_'+filterName+'        std_zp_'+filterName)
    print('{0:10.7f} {1:10.7f} {2:10.7f} {3:10.7f}'.format(eps_gi, std_eps_gi, zp_i, std_zp_i))
    return zp_i
    
def calibrate(img1 = None, img2 = None, podicut = 0.03, sdsscut = 0.03):
    try:
        from pyraf import iraf
        from astropy.io import fits
        import numpy as np
        from scipy import stats
        import scipy.optimize as opt
        import matplotlib.pyplot as plt
    except ImportError:
        print('You need some non-core python packages and a working IRAF to run this program')
        print("Try 'pip install astropy numpy scipy matplotlib pyraf' and try again")

    img_root = img1.split('_')[0]
    
    # values determined by ralf/daniel @ wiyn
    kg = 0.20
    kr = 0.12
    ki = 0.058

    # you're going to need the average stellar fwhm to compute a aperture size
    # ralf or steven probably write one to the image header during QR/etc
    # just use that value here

    # first grab the header and hang on to it so we can use other values
    hdulist = fits.open(img1)
    hdr1 = hdulist[0].header
    hdulist.close()

    # for both images
    hdulist = fits.open(img2)
    hdr2 = hdulist[0].header
    hdulist.close()
    
    # go ahead and just measure the gfwhm in the images (once) so we know for sure
    # we also need to know the "peak" values of the stellar profiles for quality cuts
    fwhm1 = getfwhm(img1)
    fwhm2 = getfwhm(img2)

    # now get the (STEVEN) measure of FWHM and the RALF version otherwise
    # this is a first estimate to set a big aperture
    # if not os.path.isfile(img1[0:-5]+'.sdssphot'):
        # try :
        #     fwhm1 = hdr1['FWHMPSF']
        #     fwhm2 = hdr2['FWHMPSF']
        # except :
        #     # print 'no FWHM info in header!'
        #     fwhm1 = float(raw_input('Enter a guess value for g in pixels: '))
        #     fwhm2 = float(raw_input('Enter a guess value for r/i in pixels: '))
        #     # fwhm1 = hdr1['SEEING']/0.11 # ralf gives the value in arcsec so 
        #     # fwhm2 = hdr2['SEEING']/0.11 # divide by the ODI pixel scale
        #     # fwhm1 = getfwhm(img1)
        #     # fwhm2 = getfwhm(img2)

    # alas, we must use IRAF apphot to do the measuring
    # first set common parameters (these shouldn't change if you're using ODI)
    iraf.unlearn(iraf.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)
    iraf.apphot.phot.setParam('interactive',"no")
    iraf.apphot.phot.setParam('verify',"no")
    iraf.datapars.setParam('datamax',50000.)
    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise") # swarped images don't have this
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass") # swarped images don't have this
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma',"INDEF")
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)

    # print 'pyraf thinks its in', os.getcwd()
    # now phot each image with the individual params
    # use txdump to put things in a nicer format for reading in
    if not os.path.isfile(img1[0:-5]+'_cal.sdssphot'): # only do this once
        print('phot-ing the g image, this might take a while...')
        iraf.datapars.setParam('fwhmpsf',fwhm1)
        iraf.photpars.setParam('apertures',5.*fwhm1) # use a big aperture for this
        iraf.fitskypars.setParam('annulus',6.*fwhm1)
        iraf.apphot.phot(image=img1, coords=img1[0:-5]+'.sdssxy', output=img1[0:-5]+'_cal.phot.1')
        with open(img1[0:-5]+'_cal.sdssphot','w+') as txdump_out :
            iraf.ptools.txdump(textfiles=img1[0:-5]+'_cal.phot.1', fields="id,mag,merr,msky,stdev,rapert,xcen,ycen,ifilter,xairmass,image", expr='MAG != INDEF && MERR != INDEF', headers='no', Stdout=txdump_out)

    if not os.path.isfile(img2[0:-5]+'_cal.sdssphot'):
        print('phot-ing the r/i image, this might take a while...')
        iraf.datapars.setParam('fwhmpsf',fwhm2)
        iraf.photpars.setParam('apertures',5.*fwhm2) # use a big aperture for this
        iraf.fitskypars.setParam('annulus',6.*fwhm2)
        iraf.apphot.phot(image=img2, coords=img2[0:-5]+'.sdssxy', output=img2[0:-5]+'_cal.phot.1')
        with open(img2[0:-5]+'_cal.sdssphot','w+') as txdump_out :
            iraf.ptools.txdump(textfiles=img2[0:-5]+'_cal.phot.1', fields="id,mag,merr,msky,stdev,rapert,xcen,ycen,ifilter,xairmass,image", expr='MAG != INDEF && MERR != INDEF', headers='no', Stdout=txdump_out)

    # read in getfwhm logs
    col1, line1, rmag1, flux1, sky1, n1, rmom1, ellip1, pa1, peak1, gfwhm1 = np.loadtxt(img1[0:-5]+'_fwhmCAL.log', usecols=(0,1,2,3,4,5,6,7,8,9,10), dtype=float, unpack=True)
    col2, line2, rmag2, flux2, sky2, n2, rmom2, ellip2, pa2, peak2, gfwhm2 = np.loadtxt(img2[0:-5]+'_fwhmCAL.log', usecols=(0,1,2,3,4,5,6,7,8,9,10), dtype=float, unpack=True)

    # read in the phot output as a string because we need to get rid of the indefs
    gMAG, gMERR, gSKY, gSERR, gRAPERT, gXPOS, gYPOS = np.loadtxt(img1[0:-5]+'_cal.sdssphot', usecols=(1,2,3,4,5,6,7), dtype=float, unpack=True)
    iMAG, iMERR, iSKY, iSERR, iRAPERT, iXPOS, iYPOS = np.loadtxt(img2[0:-5]+'_cal.sdssphot', usecols=(1,2,3,4,5,6,7), dtype=float, unpack=True)

    # get some auxiliary info from the phot output
    gXAIRMASS = np.loadtxt(img1[0:-5]+'_cal.sdssphot', usecols=(9,), dtype=str, unpack=True)
    iXAIRMASS = np.loadtxt(img2[0:-5]+'_cal.sdssphot', usecols=(9,), dtype=str, unpack=True)
    
    gFILTER = np.loadtxt(img1[0:-5]+'_cal.sdssphot', usecols=(8,), dtype=str, unpack=True)
    iFILTER = np.loadtxt(img2[0:-5]+'_cal.sdssphot', usecols=(8,), dtype=str, unpack=True)

    gID = np.loadtxt(img1[0:-5]+'_cal.sdssphot', usecols=(0,), dtype=int, unpack=True)
    iID = np.loadtxt(img2[0:-5]+'_cal.sdssphot', usecols=(0,), dtype=int, unpack=True)

    # keep the actual ID number to select from SDSS stars
    # need to do this because we already dropped INDEFs
    gID_keep = gID - 1
    iID_keep = iID - 1
    keep = list(set(gID_keep).intersection(iID_keep))

    # and keep the common elements between g and i using their list index
    keepg = [i for i,element in enumerate(gID) if element in iID]
    keepi = [i for i,element in enumerate(iID) if element in gID]

    # read in the the SDSS catalog values
    x, y, ra, dec, u, ue, g, ge, r, re, i, ie, z, ze = np.loadtxt(img1[0:-5]+'.sdssxy', usecols=(0,1,2,3,4,5,6,7,8,9,10,11,12,13), unpack=True)
    
    print("  x gID iID fw1 fw2   k  kg  ki")
    print(len(x), len(gID), len(iID), len(col1), len(col2), len(keep), len(keepg), len(keepi))

    # pick out the ones that match the good phot stars
    g, ge, r, re, i, ie, peak1, peak2, gfwhm1, gfwhm2 = np.array(g[keep]), np.array(ge[keep]), np.array(r[keep]), np.array(re[keep]), np.array(i[keep]), np.array(ie[keep]), np.array(peak1[keep]), np.array(peak2[keep]), np.array(gfwhm1[keep]), np.array(gfwhm2[keep])

    # and reduce the other vectors
    gXPOS, gYPOS, gMAG, gMERR, gSKY, gSERR, iMAG, iMERR, iSKY, iSERR = np.array(gXPOS[keepg]), np.array(gYPOS[keepg]), np.array(gMAG[keepg]), np.array(gMERR[keepg]), np.array(gSKY[keepg]), np.array(gSERR[keepg]), np.array(iMAG[keepi]), np.array(iMERR[keepi]), np.array(iSKY[keepi]), np.array(iSERR[keepi])

    # keep the airmasses and aperture radii as single values
    if gXAIRMASS[0] != 'INDEF':
        gXAIRMASS, iXAIRMASS = gXAIRMASS.astype(float)[0], iXAIRMASS.astype(float)[0]
    else:
        raise Exception
        #gXAIRMASS, iXAIRMASS = 1.054, 1.075
    gRAPERT, iRAPERT = gRAPERT[0], iRAPERT[0]

    # apply airmass extinction correction to instrumental magnitudes
    g0 = gMAG - kg*gXAIRMASS
    if iFILTER[0].endswith('i'):
        print('you gave me an i-band image, proceeding...')
        i0 = iMAG - ki*iXAIRMASS
        filterName = 'i'
        # determine catalog color and error
        gi = g - i
        gie = np.sqrt(ge**2 + ie**2)
    elif iFILTER[0].endswith('r'):
        print('you gave me an r-band image, proceeding...')
        i0 = iMAG - kr*iXAIRMASS    
        filterName = 'r'
        # determine catalog color and error
        i = r
        ie = re
        gi = g - r
        gie = np.sqrt(ge**2 + re**2)

    # from here on, all i variables represent either i or r depending on what the user input
    # determine instrumental color and its associated error
    gi0 = g0 - i0
    giMERR = np.sqrt(gMERR**2 + iMERR**2)

    # find the difference between instrumental i or r and catalog value & error
    di = i - i0
    die = np.sqrt(ie**2 + iMERR**2)

    # podicut, sdsscut = 0.01, 0.03
    print(np.median(gSERR), np.median(iSERR))
    # cuts for better fits go here
    errcut = [j for j in range(len(gMERR)) if (gMERR[j] < podicut and iMERR[j] < podicut and ge[j] < sdsscut and ie[j] < sdsscut and 1000.0 < peak1[j]< 45000.0 and 1000.0 < peak2[j]< 45000.0)]#gSKY[j] > np.median(gSERR) and iSKY[j] > np.median(iSERR))]

    with open('photcal_stars.pos','w+') as f1:
        for i, xp in enumerate(gXPOS[errcut]):
            print(xp, gYPOS[i], file=f1)
            
    print(len(gi0[errcut]))

    # fit color term
    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi0[errcut], gi[errcut], 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    mu_gi, zp_gi, std_mu_gi, std_zp_gi = p[0], p[1], perr[0], perr[1]

    # print mu_gi, zp_gi, std_mu_gi, std_zp_gi

    # do a sigma clip based on the rms of the data from the first fit
    xplt1 = gi0[errcut]
    yplt1 = mu_gi*xplt1 + zp_gi

    dy1 = yplt1 - gi[errcut]

    # print std_zp_i
    # this actually pulls out the clipped values
    gi0_2 = np.array([col for j,col in enumerate(gi0[errcut]) if (abs(dy1[j]) < dy1.std())])
    gi_2 = np.array([col for j,col in enumerate(gi[errcut]) if (abs(dy1[j]) < dy1.std())])

    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi0_2, gi_2, 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    mu_gi, zp_gi, std_mu_gi, std_zp_gi = p[0], p[1], perr[0], perr[1]
    
    # set up 95% confidence interval calculation
    conf = 0.95
    alpha=1.-conf	# significance
    n=gi0_2.size	# data sample size
    x = np.arange(-1.0,3.5,0.025)
    # Auxiliary definitions
    mse=1./(n-2.)* np.sum((gi_2-(mu_gi*gi0_2 + zp_gi))**2)	# Scatter of data about the model (mean square error)
    stdev = np.sqrt(mse)
    sxd=np.sum((gi0_2-gi0_2.mean())**2) # standard deviation of data
    sx=(x-gi0_2.mean())**2	# fit residuals
    
    # Quantile of Student's t distribution for p=1-alpha/2
    q=stats.t.ppf(1.-alpha/2.,n-2)
    
    # 95% Confidence band
    dy=q*np.sqrt(mse*(1./n + sx/sxd ))
    mu_ucb=mu_gi*x + zp_gi +dy	# Upper confidence band
    mu_lcb=mu_gi*x + zp_gi -dy	# Lower confidence band


    print('--------------------------------------------------------------------------')
    print('Here are the fit values:')
    print('mu_g'+filterName+'      std_mu_g'+filterName+'  zp_g'+filterName+'      std_zp_g'+filterName)
    print('{0:10.7f} {1:10.7f} {2:10.7f} {3:10.7f}'.format(mu_gi, std_mu_gi, zp_gi, std_zp_gi))

    # fit zero point
    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi[errcut], di[errcut], 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    eps_gi, zp_i, std_eps_gi, std_zp_i = p[0], p[1], perr[0], perr[1]

    # print eps_gi, zp_i, std_eps_gi, std_zp_i

    # do a sigma clip based on the rms of the data from the first fit
    xplt2 = gi[errcut]
    yplt2 = eps_gi*xplt2 + zp_i

    dy2 = yplt2 - di[errcut]

    # print std_zp_i
    # this actually pulls out the clipped values
    gi_3 = np.array([col for j,col in enumerate(gi[errcut]) if (abs(dy2[j]) < dy2.std())])
    di_3 = np.array([col for j,col in enumerate(di[errcut]) if (abs(dy2[j]) < dy2.std())])
    gX_3 = np.array([col for j,col in enumerate(gXPOS[errcut]) if (abs(dy2[j]) < dy2.std())])
    gY_3 = np.array([col for j,col in enumerate(gYPOS[errcut]) if (abs(dy2[j]) < dy2.std())])

    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi_3, di_3, 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    eps_gi, zp_i, std_eps_gi, std_zp_i = p[0], p[1], perr[0], perr[1]
    print('eps_g'+filterName+'     std_eps_g'+filterName+' zp_'+filterName+'        std_zp_'+filterName)
    print('{0:10.7f} {1:10.7f} {2:10.7f} {3:10.7f}'.format(eps_gi, std_eps_gi, zp_i, std_zp_i))
    
    # zp_check=[]
    # for i in [2,3,4]:
    #     for j in [2,3,4]:
    #         zp_chk = ota_zp(gX_3, gX_3, gi_3, di_3, i, j)
    #         zp_check.append(zp_chk)
    # print np.std(np.array(zp_check))
    # print zp_check
    
    # set up 95% confidence interval calculation
    conf = 0.95
    alpha=1.-conf	# significance
    n=gi_3.size	# data sample size
    x = np.arange(-1.0,3.5,0.025)
    # Auxiliary definitions
    mse=1./(n-2.)* np.sum((di_3-(eps_gi*gi_3 + zp_i))**2)	# Scatter of data about the model (mean square error)
    stdev = np.sqrt(mse)
    sxd=np.sum((gi_3-gi_3.mean())**2) # standard deviation of data
    sx=(x-gi_3.mean())**2	# fit residuals
    
    # Quantile of Student's t distribution for p=1-alpha/2
    q=stats.t.ppf(1.-alpha/2.,n-2)
    
    # 95% Confidence band
    dy=q*np.sqrt(mse*(1./n + sx/sxd ))
    eps_ucb=eps_gi*x + zp_i +dy	# Upper confidence band
    eps_lcb=eps_gi*x + zp_i -dy	# Lower confidence band

    # make a diagnostic plot
    xplt = np.arange(-2,6,0.1)
    yplt = mu_gi*xplt + zp_gi

    plt.subplot(211)
    plt.scatter(gi0[errcut], gi[errcut], facecolor='red', edgecolor='none', s=3)
    plt.scatter(gi0_2, gi_2, facecolor='black', edgecolor='none', s=3)
    plt.plot(xplt, yplt, 'r-', lw=1, alpha=1, label='fit')
    # put 2xRMS on the plot
    plt.fill_between(x, mu_ucb, mu_lcb, facecolor='blue', edgecolor='none', alpha=0.2, label='2x RMS sigma clipping region')
    plt.xlim(-1,3.5)
    plt.xlabel('$g_0 - '+filterName+'_0$ (ODI)')
    plt.ylim(-1,3.5)
    plt.ylabel('$g - '+filterName+'$ (SDSS)')
    plt.text(-0.9, 3.0, '$\mu_{g'+filterName+'} = %.4f \pm %.4f$'%(mu_gi,std_mu_gi))
    plt.text(-0.9, 2.5, '$\mathrm{zp}_{g'+filterName+'} = %.4f \pm %.4f$'%(zp_gi,std_mu_gi))
    # plt.legend(loc=3)

    plt.subplot(212)
    xplt = np.arange(-2,6,0.1)
    yplt = eps_gi*xplt + zp_i
    # plt.plot([-2,-2],[0,0], 'k--')
    plt.scatter(gi[errcut], di[errcut], facecolor='red', edgecolor='none', s=3)
    plt.scatter(gi_3, di_3, facecolor='black', edgecolor='none', s=3)
    plt.plot(xplt, yplt, 'r-', lw=1, alpha=1, label='fit')
    plt.fill_between(x, eps_ucb, eps_lcb, facecolor='blue', edgecolor='none', alpha=0.2, label='2x RMS sigma clipping region')
    plt.xlim(-1,3.5)
    plt.ylim(zp_i+1.0,zp_i-1.0)
    plt.xlabel('$g - '+filterName+'$ (SDSS)')
    plt.ylabel('$'+filterName+' - '+filterName+'_0$ (SDSS - ODI)')
    plt.text(-0.9, zp_i-0.8, '$\epsilon_{g'+filterName+'} = %.4f \pm %.4f$'%(eps_gi,std_eps_gi))
    plt.text(-0.9, zp_i-0.6, '$\mathrm{zp}_{'+filterName+'} = %.4f \pm %.4f$'%(zp_i,std_zp_i))
    plt.tight_layout()
    plt.savefig(img_root+'_photcal.pdf')
    
    plt.clf()
    plt.scatter(gXPOS, gYPOS, c='red', edgecolor='none')
    plt.xlabel('X pixel')
    plt.ylabel('Y pixel')
    plt.xlim(0,13500)
    plt.ylim(0,13500)
    plt.savefig(img_root+'_photmap.pdf')
    
    # make a cmd of the ODI photometry of all the SDSS stars for reference/checking
    # not including other stuff the calibration would need aperture correction, extinction, etc.
    g0 = gMAG - (kg*gXAIRMASS)
    i0 = iMAG - (ki*iXAIRMASS)
    gmi = mu_gi*(g0-i0) + zp_gi
    
    i_mag = i0 + eps_gi*gmi + zp_i #- cal_A_i 
    g_mag = gmi + i_mag
    
    plt.clf()
    plt.scatter(gmi, i_mag, c='red', s=3, edgecolor='none')
    plt.xlabel('$g-r$')
    plt.ylabel('$r$')
    plt.xlim(-1,2)
    plt.ylim(24,14)
    plt.savefig(img_root+'_photcmd.pdf')

    # print out a steven style help file, no writing to headers YET
    with open(img_root+'_help.txt','w+') as f1:
        print("this has some information about the calibration. don't panic.", file=f1)
        print("this is the revised (Feb 2015) version of pODI - SDSS calibrations", file=f1)
        print("   it is run on matched pairs of images (g+i, for UCHVC project)", file=f1)
        print("", file=f1)
        print("it follows the extremely standard method of photometric calibrations:", file=f1)
        print("", file=f1)
        print("g-i = mu_gi ( g0 - i0 ) + ZP_gi", file=f1)
        print("i = i0 + eps_gi ( g - i ) + ZP_i", file=f1)
        print("", file=f1)
        print("   where g0 = g_i - k_g * X_g  include airmass extinction", file=f1)
        print("         i0 = i_i - k_i * X_i", file=f1)
        print("Fits generate errors on mu/eps/ZP and also rms for both", file=f1)
        print("", file=f1)
        print("g_i/i_i are instrumental magnitudes, measured in apertures 5x FWHM", file=f1)
        print("", file=f1)
        print("all of these coefficients are saved to both g&i image headers,", file=f1)
        print("    and are reproduced below.", file=f1)
        print("", file=f1)
        print("in particular, this is the calibration for $!gal", file=f1)
        print("", file=f1)
        print("  name          symbol     IMHEAD     value", file=f1)
        print("----------------------------------------------------", file=f1)
        print("  extn coeff      k_g      F_KG       {0:.7f}".format(kg), file=f1)
        print("  extn coeff      k_g      F_KG       {0:.7f}".format(kg), file=f1)
        print("  extn coeff      k_i      F_KI       {0:.7f}".format(ki), file=f1)
        print("  airmass in g    X_g      F_XG       {0:.7f}".format(gXAIRMASS), file=f1)
        print("  airmass in "+filterName+"    X_"+filterName+"      F_X"+filterName.upper()+"       {0:.7f}".format(iXAIRMASS), file=f1)
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - -", file=f1)
        print("  g-"+filterName+" color term  mu_g"+filterName+"    F_MU_G"+filterName.upper()+"    {0:.7f}".format(mu_gi), file=f1)
        print("  g-"+filterName+" c.t. err    mue_g"+filterName+"   F_MUE_G"+filterName.upper()+"   {0:.7f}".format(std_mu_gi), file=f1)
        print("  g-"+filterName+" zeropoint   ZP_g"+filterName+"    F_ZP_G"+filterName.upper()+"    {0:.7f}".format(zp_gi), file=f1)
        print("  g-"+filterName+" ZP err      ZPE_g"+filterName+"   F_ZPE_G"+filterName.upper()+"   {0:.7f}".format(std_zp_gi), file=f1)
        print("  g-"+filterName+" fit RMS     rms      F_RMS_G"+filterName.upper()+"   {0:.7f}".format(dy1.std()), file=f1)
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - -", file=f1)
        print("  "+filterName+" color term    eps_g"+filterName+"   F_EPS_G"+filterName.upper()+"   {0:.7f}".format(eps_gi), file=f1)
        print("  "+filterName+" c.t. err      epse_g"+filterName+"  F_EPSE_G"+filterName.upper()+"  {0:.7f}".format(std_eps_gi), file=f1)
        print("  "+filterName+" zeropoint     ZP_"+filterName+"     F_ZP_"+filterName.upper()+"     {0:.7f}".format(zp_i), file=f1)
        print("  "+filterName+" ZP err        ZPe_"+filterName+"    F_ZPE_"+filterName.upper()+"    {0:.7f}".format(std_zp_i), file=f1)
        print("  "+filterName+" fit RMS       rms      F_RMS_"+filterName.upper()+"    {0:.7f}".format(dy2.std()), file=f1)
        print("----------------------------------------------------", file=f1)
        print("other details:", file=f1)
        print("  FWHM PSF [px]   fwhm    FWHMPSF    [see header]", file=f1)
        print("  FWHM [arcsec] g fwhm    F_AVGSEE   {0:.5f}".format(0.11*gRAPERT/5), file=f1)
        print("  FWHM [arcsec] "+filterName+" fwhm    F_AVGSEE   {0:.5f}".format(0.11*iRAPERT/5), file=f1)
        print("  phot aperture (5xFWHM) g [arcsec]  {0:.5f}".format(0.11*gRAPERT), file=f1)
        print("  phot aperture (5xFWHM) "+filterName+" [arcsec]  {0:.5f}".format(0.11*iRAPERT), file=f1)
        print("----------------------------------------------------", file=f1)
        print("photometric error cuts:", file=f1)
        print("  maximum acceptable pODI PHOT error: {0:.4f}".format(podicut), file=f1)
        print("  maximum acceptable sdss phot error: {0:.4f}".format(sdsscut), file=f1)
        print("  N_stars surviving error cuts: {0:4d}".format(len(gi[errcut])), file=f1)
        print("  N_stars surviving sigma clip (i-i0 vs g-"+filterName+" plot): {0:4d}".format(len(gi_3)), file=f1)
    print('--------------------------------------------------------------------------')
    print('Done! I saved some important information in the following files for you:')
    print('SDSS raw catalog values (csv):         ', img_root+'.sdss')
    print('SDSS catalog values w/ x,y positions:  ', img_root+'.sdssxy')
    print('Instrumental ODI magnitudes per image: ', img_root+'*_cal.sdssphot')
    print('Calibration fit diagnostic plots:      ', img_root+'_photcal.pdf')
    print('Final calibration values:              ', img_root+'_help.txt')

def js_calibrate(img1 = None, img2 = None, podicut = 0.03, sdsscut = 0.03, verbose=False):
    try:
        from pyraf import iraf
        from astropy.io import fits
        import astropy as ast
        from astropy.wcs import WCS
        import numpy as np
        from scipy import stats
        import scipy.optimize as opt
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
    except ImportError:
        print('You need some non-core python packages and a working IRAF to run this program')
        print("Try 'pip install astropy numpy scipy matplotlib pyraf' and try again")

    img_root = img1.split('_')[0]

    # values determined by ralf/daniel @ wiyn
    kg = 0.20
    kr = 0.12
    ki = 0.058

    iraf.ptools(_doprint=0)

    # you're going to need the average stellar fwhm to compute a aperture size
    # ralf or steven probably write one to the image header during QR/etc
    # just use that value here

    # first grab the header and hang on to it so we can use other values
    hdulist = fits.open(img1)
    hdr1 = hdulist[0].header
    hdulist.close()

    # for both images
    hdulist = fits.open(img2)
    hdr2 = hdulist[0].header
    hdulist.close()

    # go ahead and just measure the gfwhm in the images (once) so we know for sure
    # we also need to know the "peak" values of the stellar profiles for quality cuts
    fwhm1 = getfwhm(img1)
    fwhm2 = getfwhm(img2)
    
    # now get the (STEVEN) measure of FWHM and the RALF version otherwise
    # this is a first estimate to set a big aperture
    # if not os.path.isfile(img1[0:-5]+'.sdssphot'):
        # try :
        #     fwhm1 = hdr1['FWHMPSF']
        #     fwhm2 = hdr2['FWHMPSF']
        # except :
        #     # print 'no FWHM info in header!'
        #     fwhm1 = float(raw_input('Enter a guess value for g in pixels: '))
        #     fwhm2 = float(raw_input('Enter a guess value for r/i in pixels: '))
        #     # fwhm1 = hdr1['SEEING']/0.11 # ralf gives the value in arcsec so 
        #     # fwhm2 = hdr2['SEEING']/0.11 # divide by the ODI pixel scale
        #     # fwhm1 = getfwhm(img1)
        #     # fwhm2 = getfwhm(img2)
    
    # alas, we must use IRAF apphot to do the measuring
    # first set common parameters (these shouldn't change if you're using ODI)
    iraf.unlearn(iraf.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)
    iraf.apphot.phot.setParam('interactive',"no")
    iraf.apphot.phot.setParam('verify',"no")
    iraf.datapars.setParam('datamax',50000.)
    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise") # swarped images don't have this
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass") # swarped images don't have this
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma',"INDEF")
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)
    
    # print 'pyraf thinks its in', os.getcwd()
    # now phot each image with the individual params
    # use txdump to put things in a nicer format for reading in
    if not os.path.isfile(img1[0:-5]+'_cal_js.sdssphot'): # only do this once
        print('phot-ing the g image, this might take a while...')
        iraf.datapars.setParam('fwhmpsf',fwhm1)
        iraf.photpars.setParam('apertures',5.*fwhm1) # use a big aperture for this
        iraf.fitskypars.setParam('annulus',6.*fwhm1)
        iraf.apphot.phot(image=img1, coords=img1[0:-5]+'.sdssxy', output=img1[0:-5]+'_cal_js.phot.1')
        with open(img1[0:-5]+'_cal_js.sdssphot','w+') as txdump_out :
            iraf.ptools.txdump(textfiles=img1[0:-5]+'_cal_js.phot.1', fields="id,mag,merr,msky,stdev,rapert,xcen,ycen,ifilter,xairmass,image", expr='MAG != INDEF && MERR != INDEF', headers='no', Stdout=txdump_out)
    
    if not os.path.isfile(img2[0:-5]+'_cal_js.sdssphot'):
        print('phot-ing the r/i image, this might take a while...')
        iraf.datapars.setParam('fwhmpsf',fwhm2)
        iraf.photpars.setParam('apertures',5.*fwhm2) # use a big aperture for this
        iraf.fitskypars.setParam('annulus',6.*fwhm2)
        iraf.apphot.phot(image=img2, coords=img2[0:-5]+'.sdssxy', output=img2[0:-5]+'_cal_js.phot.1')
        with open(img2[0:-5]+'_cal_js.sdssphot','w+') as txdump_out :
            iraf.ptools.txdump(textfiles=img2[0:-5]+'_cal_js.phot.1', fields="id,mag,merr,msky,stdev,rapert,xcen,ycen,ifilter,xairmass,image", expr='MAG != INDEF && MERR != INDEF', headers='no', Stdout=txdump_out)
    
    # read in getfwhm logs
    col1, line1, rmag1, flux1, sky1, n1, rmom1, ellip1, pa1, peak1, gfwhm1 = np.loadtxt(img1[0:-5]+'_fwhmCAL.log', usecols=(0,1,2,3,4,5,6,7,8,9,10), dtype=float, unpack=True)
    col2, line2, rmag2, flux2, sky2, n2, rmom2, ellip2, pa2, peak2, gfwhm2 = np.loadtxt(img2[0:-5]+'_fwhmCAL.log', usecols=(0,1,2,3,4,5,6,7,8,9,10), dtype=float, unpack=True)
    
    # read in the phot output as a string because we need to get rid of the indefs
    gMAG, gMERR, gSKY, gSERR, gRAPERT, gXPOS, gYPOS = np.loadtxt(img1[0:-5]+'_cal_js.sdssphot', usecols=(1,2,3,4,5,6,7), dtype=float, unpack=True)
    iMAG, iMERR, iSKY, iSERR, iRAPERT, iXPOS, iYPOS = np.loadtxt(img2[0:-5]+'_cal_js.sdssphot', usecols=(1,2,3,4,5,6,7), dtype=float, unpack=True)
    
    # get some auxiliary info from the phot output
    gXAIRMASS = np.loadtxt(img1[0:-5]+'_cal_js.sdssphot', usecols=(9,), dtype=str, unpack=True)
    iXAIRMASS = np.loadtxt(img2[0:-5]+'_cal_js.sdssphot', usecols=(9,), dtype=str, unpack=True)
    
    gFILTER = np.loadtxt(img1[0:-5]+'_cal_js.sdssphot', usecols=(8,), dtype=str, unpack=True)
    iFILTER = np.loadtxt(img2[0:-5]+'_cal_js.sdssphot', usecols=(8,), dtype=str, unpack=True)
    
    gID = np.loadtxt(img1[0:-5]+'_cal_js.sdssphot', usecols=(0,), dtype=int, unpack=True)
    iID = np.loadtxt(img2[0:-5]+'_cal_js.sdssphot', usecols=(0,), dtype=int, unpack=True)
    
    # keep the actual ID number to select from SDSS stars
    # need to do this because we already dropped INDEFs
    gID_keep = gID - 1
    iID_keep = iID - 1
    keep = list(set(gID_keep).intersection(iID_keep))
    
    # and keep the common elements between g and i using their list index
    keepg = [i for i,element in enumerate(gID) if element in iID]
    keepi = [i for i,element in enumerate(iID) if element in gID]
    
    # read in the the SDSS catalog values
    x, y, ra, dec, u, ue, g, ge, r, re, i, ie, z, ze = np.loadtxt(img1[0:-5]+'.sdssxy', usecols=(0,1,2,3,4,5,6,7,8,9,10,11,12,13), unpack=True)
    
    # pick out the ones that match the good phot stars
    g, ge, r, re, i, ie, peak1, peak2, gfwhm1, gfwhm2 = np.array(g[keep]), np.array(ge[keep]), np.array(r[keep]), np.array(re[keep]), np.array(i[keep]), np.array(ie[keep]), np.array(peak1[keep]), np.array(peak2[keep]), np.array(gfwhm1[keep]), np.array(gfwhm2[keep])
    
    # and reduce the other vectors
    gXPOS, gYPOS, gMAG, gMERR, gSKY, gSERR, iMAG, iMERR, iSKY, iSERR = np.array(gXPOS[keepg]), np.array(gYPOS[keepg]), np.array(gMAG[keepg]), np.array(gMERR[keepg]), np.array(gSKY[keepg]), np.array(gSERR[keepg]), np.array(iMAG[keepi]), np.array(iMERR[keepi]), np.array(iSKY[keepi]), np.array(iSERR[keepi])

    # keep the airmasses and aperture radii as single values
    if gXAIRMASS[0] != 'INDEF':
        gXAIRMASS, iXAIRMASS = gXAIRMASS.astype(float)[0], iXAIRMASS.astype(float)[0]
    else:
        gXAIRMASS, iXAIRMASS = 1.054, 1.075
    gRAPERT, iRAPERT = gRAPERT[0], iRAPERT[0]

    # apply airmass extinction correction to instrumental magnitudes
    g0 = gMAG - kg*gXAIRMASS
    if iFILTER[0].endswith('i'):
        print('you gave me an i-band image, proceeding...')
        i0 = iMAG - ki*iXAIRMASS
        filterName = 'i'
        # determine catalog color and error
        gi = g - i
        gie = np.sqrt(ge**2 + ie**2)
    elif iFILTER[0].endswith('r'):
        print('you gave me an r-band image, proceeding...')
        i0 = iMAG - kr*iXAIRMASS    
        filterName = 'r'
        # determine catalog color and error
        i = r
        ie = re
        gi = g - r
        gie = np.sqrt(ge**2 + re**2)

    # from here on, all i variables represent either i or r depending on what the user input
    # determine instrumental color and its associated error
    gi0 = g0 - i0
    giMERR = np.sqrt(gMERR**2 + iMERR**2)

    # find the difference between instrumental i or r and catalog value & error
    di = i - i0
    die = np.sqrt(ie**2 + iMERR**2)
    dsgi = np.absolute((di - np.median(di))/np.std(di))
    
    dg = g - g0
    dge = np.sqrt(ge**2 + gMERR**2)
    dsgg = np.absolute((dg - np.median(dg))/np.std(dg))

    # podicut, sdsscut = 0.03, 0.03
    # print np.median(gSERR), np.median(iSERR)
    # cuts for better fits go here
    errcut = [j for j in range(len(gMERR)) if (gMERR[j] < podicut and iMERR[j] < podicut and ge[j] < sdsscut and ie[j] < sdsscut and dsgi[j] < 1.0 and dsgg[j] < 1.0)]
    # and 1000.0 < peak1[j]< 45000.0 and 1000.0 < peak2[j]< 45000.0
    #errcut = [j for j in range(len(gMERR)) if (gMERR[j] < podicut and iMERR[j] < podicut and ge[j] < sdsscut and ie[j] < sdsscut and gSKY[j] > np.median(gSERR) and iSKY[j] > np.median(iSERR) and di[j] > 25.5)]

    if verbose:
        for j in range(len(gi[errcut])):
            print(gXPOS[errcut][j], gYPOS[errcut][j], ra[errcut][j], dec[errcut][j], gMAG[errcut][j], gMERR[errcut][j], iMAG[errcut][j], iMERR[errcut][j], di[errcut][j], dg[errcut][j], gi[errcut][j])

    print('fitting wtih '+repr(len(gi0[errcut]))+' stars...')

    # fit zero point
    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi[errcut], dg[errcut], 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    eps_g, zp_g, std_eps_g, std_zp_g = p[0], p[1], perr[0], perr[1]

    
    # set up 95% confidence interval calculation
    conf = 0.95
    alpha=1.-conf	# significance
    n=gi[errcut].size	# data sample size
    x = np.arange(-1.0,3.5,0.025)
    # Auxiliary definitions
    mse=1./(n-2.)* np.sum((dg[errcut]-(eps_g*gi[errcut] + zp_g))**2)	# Scatter of data about the model (mean square error)
    stdev = np.sqrt(mse)
    sxd=np.sum((gi-gi.mean())**2) # standard deviation of data
    sx=(x-gi.mean())**2	# fit residuals
    
    # Quantile of Student's t distribution for p=1-alpha/2
    q=stats.t.ppf(1.-alpha/2.,n-2)
    
    # 95% Confidence band
    dy=q*np.sqrt(mse*(1./n + sx/sxd ))
    dy1 = dy
    epsg_ucb=eps_g*x + zp_g +dy	# Upper confidence band
    epsg_lcb=eps_g*x + zp_g -dy	# Lower confidence band

    print('--------------------------------------------------------------------------')
    print('Here are the fit values:')
    print('eps_g'+'      std_eps_g'+'  zp_g'+'         std_zp_g')
    print('{0:10.7f} {1:10.7f} {2:10.7f} {3:10.7f}'.format(eps_g, std_eps_g, zp_g, std_zp_g))
    star_zp_g = g - g0 - eps_g*gi
    print('std. dev. in ZP per star (not fit): {0:10.7f}'.format(np.std(star_zp_g[errcut])))

    # fit zero point
    # linear lsq with numpy.polyfit
    p, pcov = np.polyfit(gi[errcut], di[errcut], 1, cov=True)
    perr = np.sqrt(np.diag(pcov))
    eps_i, zp_i, std_eps_i, std_zp_i = p[0], p[1], perr[0], perr[1]
        
    # set up 95% confidence interval calculation
    conf = 0.95
    alpha=1.-conf	# significance
    n=gi[errcut].size	# data sample size
    x = np.arange(-1.0,3.5,0.025)
    # Auxiliary definitions
    mse=1./(n-2.)* np.sum((di[errcut]-(eps_i*gi[errcut] + zp_i))**2)	# Scatter of data about the model (mean square error)
    stdev = np.sqrt(mse)
    sxd=np.sum((gi-gi.mean())**2) # standard deviation of data
    sx=(x-gi.mean())**2	# fit residuals
    
    # Quantile of Student's t distribution for p=1-alpha/2
    q=stats.t.ppf(1.-alpha/2.,n-2)
    
    # 95% Confidence band
    dy=q*np.sqrt(mse*(1./n + sx/sxd ))
    dy2 = dy
    epsi_ucb=eps_i*x + zp_i +dy	# Upper confidence band
    epsi_lcb=eps_i*x + zp_i -dy	# Lower confidence band

    print('eps_'+filterName+'      std_eps_'+filterName+'   zp_'+filterName+'        std_zp_'+filterName)
    print('{0:10.7f} {1:10.7f} {2:10.7f} {3:10.7f}'.format(eps_i, std_eps_i, zp_i, std_zp_i))
    star_zp_i = i - i0 - eps_i*gi
    print('std. dev. in ZP per star (not fit): {0:10.7f}'.format(np.std(star_zp_i[errcut])))

    plt.figure(1)
    plt.subplot(211)
    xplt = np.arange(-2,6,0.1)
    yplt = eps_g*xplt + zp_g
    # plt.plot([-2,-2],[0,0], 'k--')
    plt.scatter(gi[errcut], dg[errcut], facecolor='black', edgecolor='none', s=3)
    # plt.scatter(gi_3, di_3, facecolor='black', edgecolor='none', s=3)
    # plt.plot(xplt, yplt, 'r-', lw=1, alpha=1, label='fit')
    plt.fill_between(x, epsg_ucb, epsg_lcb, facecolor='red', edgecolor='none', alpha=0.9)
    plt.xlim(-1,3.5)
    plt.ylim(zp_g+1.0,zp_g-1.0)
    plt.xlabel('$g - '+filterName+'$ (SDSS)')
    plt.ylabel('$g - g_0$ (SDSS - ODI)')
    plt.text(-0.9, zp_g-0.8, '$\epsilon_{g} = %.4f \pm %.4f$'%(eps_g,std_eps_g))
    plt.text(-0.9, zp_g-0.6, '$\mathrm{zp}_{g} = %.4f \pm %.4f$'%(zp_g,std_zp_g))
    # plt.legend(loc=3)
    
    plt.subplot(212)
    xplt = np.arange(-2,6,0.1)
    yplt = eps_i*xplt + zp_i
    # plt.plot([-2,-2],[0,0], 'k--')
    plt.scatter(gi[errcut], di[errcut], facecolor='black', edgecolor='none', s=3)
    # plt.scatter(gi_3, di_3, facecolor='black', edgecolor='none', s=3)
    # plt.plot(xplt, yplt, 'r-', lw=1, alpha=1, label='fit')
    plt.fill_between(x, epsi_ucb, epsi_lcb, facecolor='red', edgecolor='none', alpha=0.9)
    plt.xlim(-1,3.5)
    plt.ylim(zp_i+1.0,zp_i-1.0)
    plt.xlabel('$g - '+filterName+'$ (SDSS)')
    plt.ylabel('$'+filterName+' - '+filterName+'_0$ (SDSS - ODI)')
    plt.text(-0.9, zp_i-0.8, '$\epsilon_{'+filterName+'} = %.4f \pm %.4f$'%(eps_i,std_eps_i))
    plt.text(-0.9, zp_i-0.6, '$\mathrm{zp}_{'+filterName+'} = %.4f \pm %.4f$'%(zp_i,std_zp_i))
    
    # plt.subplot(222)
    # plt.scatter(gYPOS[errcut], dg[errcut], facecolor='black', edgecolor='none', s=3)
    # plt.xlim(0,20)
    # plt.ylim(zp_g+1.0,zp_g-1.0)
    # plt.xlabel('$g - '+filterName+'$ (SDSS)')
    # plt.ylabel('$'+filterName+' - '+filterName+'_0$ (SDSS - ODI)')
    
    # plt.subplot(224)
    # plt.scatter(gYPOS[errcut], di[errcut], facecolor='black', edgecolor='none', s=3)
    # plt.xlim(0,20)
    # plt.ylim(zp_i+1.0,zp_i-1.0)
    # plt.xlabel('$g - '+filterName+'$ (SDSS)')
    # plt.ylabel('$'+filterName+' - '+filterName+'_0$ (SDSS - ODI)')
    
    plt.tight_layout()
    plt.savefig(img_root+'_photcal_js.pdf')
    
    # podicut, sdsscut = 0.003, 0.04
    errcutzp = np.where((ge < 0.05) & (gMERR <0.05))
    # print np.median(gSERR), np.median(iSERR)
    # cuts for better fits go here
    # errcut = [j for j in range(len(gMERR)) if (gMERR[j] < podicut and iMERR[j] < podicut and ge[j] < sdsscut and ie[j] < sdsscut and gSKY[j] > np.median(gSERR) and iSKY[j] > np.median(iSERR))]
    plt.clf()
    hdulist1 = ast.io.fits.open(img1)
    hdulist2 = ast.io.fits.open(img2)
    xmax = hdulist1[0].header['naxis1']
    ymax = hdulist1[0].header['naxis2']
    ax1 = plt.subplot(2,2,1, projection=WCS(hdulist1[0].header))
    # plt.imshow(hdulist[0].data, origin='lower', cmap='Greys_r', vmin=500., vmax=2000.)
    plt.scatter(gXPOS[errcut], gYPOS[errcut], c=(star_zp_g[errcut]-np.median(star_zp_g[errcut])), edgecolor='none', alpha=1.0, cmap=cm.rainbow)
    
    plt.xlabel('ra (SDSS $g$)')
    plt.ylabel('dec')
    plt.xlim(0,xmax)
    plt.ylim(0,ymax)
    cb = plt.colorbar()
    sig = np.std(star_zp_g[errcut])
    cb.set_label('diff.from median ZP ({0:5.2f})'.format(np.median(star_zp_g[errcut])))
    # cb.set_ticks([-7.0*sig,-6.0*sig,-5.0*sig,-4.0*sig,-3.0*sig,-2.0*sig,-1.0*sig,0.0,sig,2.0*sig,3.0*sig,4.0*sig,5.0*sig,6.0*sig,7.0*sig,8.0*sig])
    # cb.set_ticklabels(['{0:5.2f}'.format(-7.0*sig),'{0:5.2f}'.format(-6.0*sig),'{0:5.2f}'.format(-5.0*sig),'{0:5.2f}'.format(-4.0*sig),'{0:5.2f}'.format(-3.0*sig),'{0:5.2f}'.format(-2.0*sig),'{0:5.2f}'.format(-1.0*sig),'{0:5.2f}'.format(0.0),'{0:5.2f}'.format(sig), '{0:5.2f}'.format(2.0*sig), '{0:5.2f}'.format(3.0*sig), '{0:5.2f}'.format(4.0*sig), '{0:5.2f}'.format(5.0*sig), '{0:5.2f}'.format(6.0*sig), '{0:5.2f}'.format(7.0*sig), '{0:5.2f}'.format(8.0*sig)])
    
    ax2 = plt.subplot(2,2,2)
    ax2.get_xaxis().set_visible(False)
    ax2.get_yaxis().set_visible(False)
    ota_mean, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_g[errcut], statistic='mean', bins=[3,3])
    ota_median, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_g[errcut], statistic='median', bins=[3,3])
    ota_count, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_g[errcut], statistic='count', bins=[3,3])
    ota_std, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_g[errcut], statistic=np.std, bins=[3,3])
    # print ota_mean, ota_median, ota_count, ota_std
    
    for j in range(3):
        for k in range(3):
            plt.text(ota_x[j]+300, ota_y[k]+3100, 'mean = {0:5.2f}'.format(ota_mean[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+2400, 'median = {0:5.2f}'.format(ota_median[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+1700, 'ota - global = {0:5.2f}'.format(ota_median[j,k]-np.median(star_zp_g[errcut])), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+1000, 'std = {0:5.2f}'.format(ota_std[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+300,  'N = {0:5d}'.format(int(ota_count[j,k])), fontsize=6)
    
    plt.hlines(ota_y[1:3],0,xmax,linestyles='dashed')
    plt.vlines(ota_x[1:3],0,ymax,linestyles='dashed')
    plt.xlim(0,xmax)
    plt.ylim(0,ymax)
    
    ax3 = plt.subplot(2,2,3, projection=WCS(hdulist2[0].header))
    # plt.imshow(hdulist[0].data, origin='lower', cmap='Greys_r', vmin=500., vmax=2000.)
    plt.scatter(gXPOS[errcut], gYPOS[errcut], c=(star_zp_i[errcut]-np.median(star_zp_i[errcut])), edgecolor='none', alpha=1.0, cmap=cm.rainbow)
    
    plt.xlabel('ra (SDSS $i$)')
    plt.ylabel('dec')
    plt.xlim(0,xmax)
    plt.ylim(0,ymax)
    cb = plt.colorbar()
    sig = np.std(star_zp_i[errcut])
    cb.set_label('diff.from median ZP ({0:5.2f})'.format(np.median(star_zp_i[errcut])))
    # cb.set_ticks([-1.0*sig,0.0,sig,2.0*sig,3.0*sig,4.0*sig,5.0*sig,6.0*sig,7.0*sig,8.0*sig])
    # cb.set_ticklabels(['{0:5.2f}'.format(-1.0*sig),'{0:5.2f}'.format(0.0),'{0:5.2f}'.format(sig), '{0:5.2f}'.format(2.0*sig), '{0:5.2f}'.format(3.0*sig), '{0:5.2f}'.format(4.0*sig), '{0:5.2f}'.format(5.0*sig), '{0:5.2f}'.format(6.0*sig), '{0:5.2f}'.format(7.0*sig), '{0:5.2f}'.format(8.0*sig)])
    
    ax4 = plt.subplot(2,2,4)
    ax4.get_xaxis().set_visible(False)
    ax4.get_yaxis().set_visible(False)
    ota_mean, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_i[errcut], statistic='mean', bins=[3,3])
    ota_median, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_i[errcut], statistic='median', bins=[3,3])
    ota_count, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_i[errcut], statistic='count', bins=[3,3])
    ota_std, ota_x, ota_y, ota_id = stats.binned_statistic_2d(gXPOS[errcut], gYPOS[errcut], star_zp_i[errcut], statistic=np.std, bins=[3,3])
    
    for j in range(3):
        for k in range(3):
            plt.text(ota_x[j]+300, ota_y[k]+3100, 'mean = {0:5.2f}'.format(ota_mean[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+2400, 'median = {0:5.2f}'.format(ota_median[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+1700, 'ota - global = {0:5.2f}'.format(ota_median[j,k]-np.median(star_zp_i[errcut])), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+1000, 'std = {0:5.2f}'.format(ota_std[j,k]), fontsize=6)
            plt.text(ota_x[j]+300, ota_y[k]+300,  'N = {0:5d}'.format(int(ota_count[j,k])), fontsize=6)
    
    plt.hlines(ota_y[1:3],0,xmax,linestyles='dashed')
    plt.vlines(ota_x[1:3],0,ymax,linestyles='dashed')
    plt.xlim(0,xmax)
    plt.ylim(0,ymax)
    # plt.tight_layout()
    
    
    plt.savefig(img_root+'_photmap_js.pdf')
    hdulist1.close()
    hdulist2.close()
    
    # print out a steven style help file, no writing to headers YET
    with open(img_root+'_help_js.txt','w+') as f1:
        print("#  name           symbol   IMHEAD    value", file=f1)
        print("----------------------------------------------------", file=f1)
        print("  extn coeff      k_g      F_KG      {0:.7f}".format(kg), file=f1)
        print("  extn coeff      k_r      F_KR      {0:.7f}".format(kr), file=f1)
        print("  extn coeff      k_i      F_KI      {0:.7f}".format(ki), file=f1)
        print("  airmass in g    X_g      F_XG      {0:.7f}".format(gXAIRMASS), file=f1)
        print("  airmass in "+filterName+"    X_"+filterName+"     F_X"+filterName.upper()+"      {0:.7f}".format(iXAIRMASS), file=f1)
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - -", file=f1)
        print("  g color term    eps_g    F_EPS_G   {0:.7f}".format(eps_g), file=f1)
        print("  g c.t. err      epse_g   F_EPSE_G  {0:.7f}".format(std_eps_g), file=f1)
        print("  g zeropoint     ZP_g     F_ZP_G    {0:.7f}".format(zp_g), file=f1)
        print("  g ZP err        ZPE_g    F_ZPE_G   {0:.7f}".format(std_zp_g), file=f1)
        print("  g fit RMS       rms      F_RMS_G   {0:.7f}".format(dy1.std()), file=f1)
        print(" - - - - - - - - - - - - - - - - - - - - - - - - - -", file=f1)
        print("  "+filterName+" color term    eps_"+filterName+"   F_EPS_"+filterName.upper()+"   {0:.7f}".format(eps_i), file=f1)
        print("  "+filterName+" c.t. err      epse_"+filterName+"  F_EPSE_"+filterName.upper()+"  {0:.7f}".format(std_eps_i), file=f1)
        print("  "+filterName+" zeropoint     ZP_"+filterName+"    F_ZP_"+filterName.upper()+"    {0:.7f}".format(zp_i), file=f1)
        print("  "+filterName+" ZP err        ZPe_"+filterName+"   F_ZPE_"+filterName.upper()+"   {0:.7f}".format(std_zp_i), file=f1)
        print("  "+filterName+" fit RMS       rms      F_RMS_"+filterName.upper()+"   {0:.7f}".format(dy2.std()), file=f1)
        print("----------------------------------------------------", file=f1)
        print("other details:", file=f1)
        print("  FWHM PSF [px] g fwhm     FWHMPSF   {0:6.5f}".format(gRAPERT/5), file=f1)
        print("  FWHM PSF [px] "+filterName+" fwhm     FWHMPSF   {0:6.5f}".format(iRAPERT/5), file=f1)
        print("  FWHM [arcsec] g fwhm     F_AVGSEE  {0:.5f}".format(0.11*gRAPERT/5), file=f1)
        print("  FWHM [arcsec] "+filterName+" fwhm     F_AVGSEE  {0:.5f}".format(0.11*iRAPERT/5), file=f1)
        print("  phot aperture (5xFWHM) g [arcsec]  {0:.5f}".format(0.11*gRAPERT), file=f1)
        print("  phot aperture (5xFWHM) "+filterName+" [arcsec]  {0:.5f}".format(0.11*iRAPERT), file=f1)
        print("----------------------------------------------------", file=f1)
        print("photometric error cuts:", file=f1)
        print("  maximum acceptable pODI PHOT error: {0:.4f}".format(podicut), file=f1)
        print("  maximum acceptable sdss phot error: {0:.4f}".format(sdsscut), file=f1)
        print("  N_stars surviving error cuts:       {0:4d}".format(len(gi[errcut])), file=f1)
        # print >> f1, "  N_stars surviving sigma clip (i-i0 vs g-i plot): {0:4d}".format(len(gi_3))
    print('--------------------------------------------------------------------------')
    print('Done! I saved some important information in the following files for you:')
    print('SDSS raw catalog values (csv):         ', img_root+'*.sdss')
    print('SDSS catalog values w/ x,y positions:  ', img_root+'*.sdssxy')
    print('Instrumental ODI magnitudes per image: ', img_root+'*_cal.sdssphot')
    print('Calibration fit diagnostic plots:      ', img_root+'_photcal_js.pdf')
    print('Zero Point map:                        ', img_root+'_photmap_js.pdf')
    print('Final calibration values:              ', img_root+'_help_js.txt')

    
    return eps_g, std_eps_g, zp_g, std_zp_g, eps_i, std_eps_i, zp_i, std_zp_i

def get_calibration():
    path = os.getcwd()
    steps = path.split('/')
    objname = steps[-1].upper()
    photcalFile = open(objname+'_help_js.txt')
    photcal = photcalFile.read()
    photcalLines = photcal.splitlines()
    eps_g = float(photcalLines[8].split()[5])
    std_eps_g = float(photcalLines[9].split()[5])
    zp_g = float(photcalLines[10].split()[4])
    std_zp_g = float(photcalLines[11].split()[5])
    eps_i = float(photcalLines[14].split()[5])
    std_eps_i = float(photcalLines[15].split()[5])
    zp_i = float(photcalLines[16].split()[4])
    std_zp_i = float(photcalLines[17].split()[5])
    photcalFile.close()
    return eps_g, std_eps_g, zp_g, std_zp_g, eps_i, std_eps_i, zp_i, std_zp_i

def main():
    # ask user input on which files to run on
    print('This is a program to do SDSS-based photometric calibration on QR-ed pODI images.')
    print("I'm going to do all of the hard work for you and make some helpful files. ")
    print('--------------------------------------------------------------------------')
    # if not os.path.isfile('m13-se.g.phot.1'):
    #     g_img = raw_input('Enter the g image file name: \n')
    # else:
    path = os.getcwd()
    steps = path.split('/')
    folder = steps[-1].upper()
    
    g_img = folder+'_g.fits'
    i_img = folder+'_i.fits'
    
    # print '--------------------------------------------------------------------------'
    # if not os.path.isfile(g_img.nofits()+'.sdss'):        
    download_sdss(g_img, i_img)
    # calibrate(img1=g_img, img2=i_img, podicut = 0.03, sdsscut = 0.03)
    js_calibrate(img1=g_img, img2=i_img, podicut = 0.03, sdsscut = 0.03)

if __name__ == '__main__':
    main()
