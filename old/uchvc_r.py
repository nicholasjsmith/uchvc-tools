#! /usr/local/bin/python
import os, sys, time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
# import matplotlib.pyplot as plt
from subprocess import call
# from astropy import wcs
from astropy.io import fits
from pyraf import iraf

home_root = os.environ['HOME']
funpack_path = home_root+'/bin/funpack'
iraf.images(_doprint=0)
iraf.tv(_doprint=0)
iraf.ptools(_doprint=0)
iraf.noao(_doprint=0)
iraf.digiphot(_doprint=0)
iraf.photcal(_doprint=0)
iraf.apphot(_doprint=0)  
iraf.imutil(_doprint=0)

# check to see if files have been unpacked
unpacked = False
for file_ in os.listdir("./"):
    if file_.endswith(".fits"):
        unpacked = True
        
# unpack all *.fz
if not unpacked :
    funpack_cmd = funpack_path+' *.fz'
    call(funpack_cmd, shell=True)

for file_ in os.listdir("./"):
    # if file_.endswith("i_match.fits"):
    #     fits_file_i = file_
    # if file_.endswith("g.fits"):
    #     fits_file_g = file_
    if file_.endswith("g_sh.fits"):    # get the title string from the zipped g image 
        title_string = file_[0:9]        # which should always exist in the directory
        
# copy the good region (no cell gaps) to a new file        
fits_g = title_string+'_g_sh.fits'
# if not os.path.isfile(fits_g) :
#     iraf.images.imcopy(fits_file_g+'[3000:14000,3000:14000]',fits_g,verbose="yes")
    
fits_i = title_string+'_r_sh.fits'
# if not os.path.isfile(fits_i) :
#     iraf.images.imcopy(fits_file_i+'[3000:14000,3000:14000]',fits_i,verbose="yes")

# remove the unpacked fits file to save space, keep the .fz
# try:
#     if os.path.isfile(fits_file_i) :    
#         os.remove(fits_file_i)
#     if os.path.isfile(fits_file_g) :
#         os.remove(fits_file_g)
# except:
#     time.sleep(0.1)
    
# make an imsets file
if not os.path.isfile(title_string+'.imsets') :
    imset_file = open(title_string+'.imsets', 'w+')
    print >> imset_file, title_string, ':', fits_i, fits_g
    imset_file.close()

# call('ds9x11 &')
# only open the images in ds9 and 
# if not (os.path.isfile('background_regions.txt') or os.path.isfile('mask.reg')):
# iraf.tv.display(image=fits_g, frame=1)
# iraf.tv.display(=fits_i, frame=1)

kg = 0.15
ki = 0.10

# get the photometric calibration coefficients from Steven's help file <--
# or from the image header/fits table/ whatever
photcalFile = open(title_string+'_help.txt')
photcal = photcalFile.read()
photcalLines = photcal.splitlines()

mu_gi = float(photcalLines[28].split()[5])
zp_gi = float(photcalLines[30].split()[4])
eps_gi = float(photcalLines[34].split()[5])
zp_i = float(photcalLines[36].split()[4])
amg = float(photcalLines[25].split()[5])
ami = float(photcalLines[26].split()[5])
photcalFile.close()

print mu_gi, zp_gi, eps_gi, zp_i, amg, ami

fits_h_i = fits.open(fits_i)
fits_h_g = fits.open(fits_g)

# fwhm_i = fits_h_i[0].header['F_AVGSEE']/0.11
# fwhm_g = fits_h_g[0].header['F_AVGSEE']/0.11

# get steven's/QR's estimate of the image FWHMPSF
# fwhm_i = fits_h_i[0].header['FWHMPSF']
# fwhm_g = fits_h_g[0].header['FWHMPSF']

fwhm_i = 14.33
fwhm_g = 14.57

print 'Target Coordinates :: ',fits_h_i[0].header['RA'],fits_h_i[0].header['DEC']
print 'Image header FWHM :: g = {0:5.3f} : i = {1:5.3f}'.format(fwhm_g,fwhm_i)

# background sigma calculation
# put down boxes to measure it. QR should give a reasonable estimate as well, maybe use that? (simpler)
if not os.path.isfile('background_regions.txt') :
    print 'To continue you must select 12 to 15 empty rectangular regions in'
    print 'DS9 and export to an IRAF PROS file named background_regions.txt'
    raw_input("Press Enter when finished:")


if not os.path.isfile('bgvals_i.txt'):
    bg_file_g = open("bgvals_g.txt", 'w+')
    bg_file_i = open("bgvals_i.txt", 'w+')

    b3,b4,b5,b6 = np.loadtxt('background_regions.txt',usecols=(2,3,4,5),unpack=True)
    for i in range(len(b3)) :
        bx1 = b3[i] - (b5[i]/2.)
        bx2 = b3[i] + (b5[i]/2.)
        by1 = b4[i] - (b6[i]/2.)
        by2 = b4[i] + (b6[i]/2.)
        
        iraf.images.imstat(fits_g+'['+repr(int(bx1))+':'+repr(int(bx2))+','+repr(int(by1))+':'+repr(int(by2))+']', fields="image,npix,mean,midpt,stddev,min,max", Stdout=bg_file_g)
        iraf.images.imstat(fits_i+'['+repr(int(bx1))+':'+repr(int(bx2))+','+repr(int(by1))+':'+repr(int(by2))+']', fields="image,npix,mean,midpt,stddev,min,max", Stdout=bg_file_i)
        
    bg_file_g.close()
    bg_file_i.close()
    
bgmean_g, bgsig_g = np.loadtxt('bgvals_g.txt',usecols=(3,4),unpack=True)
bgmean_i, bgsig_i = np.loadtxt('bgvals_i.txt',usecols=(3,4),unpack=True)

# yes, use the QR measured background values (get them from the image headers!) 
# bg_i = fits_h_i[0].header['SKY_STD']
# bg_g = fits_h_g[0].header['SKY_STD']
# bgm_i = fits_h_i[0].header['SKY_MEDI']
# bgm_g = fits_h_g[0].header['SKY_MEDI']

bg_g = np.mean(bgsig_g)
bg_i = np.mean(bgsig_i)
bgm_g = np.mean(bgmean_g)
bgm_i = np.mean(bgmean_i)
print 'Image mean BG sigma value :: g = {0:5.3f} : i = {1:5.3f}'.format(bg_g,bg_i)
print 'Image mean BG median value :: g = {0:5.3f} : i = {1:5.3f}'.format(bgm_g,bgm_i)

# daofind steps
# find all the sources in the image (threshold value will be data dependent, 4.0 is good for UCHVCs)
# g image
if not os.path.isfile(fits_g+'.coo.1') :
    iraf.datapars.setParam('fwhmpsf',fwhm_g,check=1)
    iraf.datapars.setParam('sigma',bg_g,check=1)
    
    iraf.findpars.setParam('threshold',4.0)
    iraf.daofind(image=fits_g, verbose="no")
    
    # i image
if not os.path.isfile(fits_i+'.coo.1') :
    iraf.datapars.setParam('fwhmpsf',fwhm_i,check=1)
    iraf.datapars.setParam('sigma',bg_i,check=1)
    
    iraf.findpars.setParam('threshold',4.0)
    iraf.daofind(image=fits_i, verbose="no")


# now phot the stars found in daofind
if not os.path.isfile(fits_g+'.mag.1') :
    print 'phot-ing g band daofind stars. This is going to take a while...'
    iraf.unlearn(iraf.apphot.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)
    iraf.apphot.phot.setParam('interactive',"no")
    iraf.apphot.phot.setParam('verify',"no")
    iraf.datapars.setParam('datamax',50000.)
    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise")
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass")
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma',"INDEF")
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)
    
    iraf.datapars.setParam('fwhmpsf',fwhm_g)
    iraf.photpars.setParam('apertures',2.*fwhm_g)
    iraf.fitskypars.setParam('annulus',4.*fwhm_g)

    iraf.apphot.phot(image=fits_g, coords=fits_g+'.coo.1')

if not os.path.isfile(fits_i+'.mag.1') :
    print 'phot-ing i band daofind stars. This is going to take a while...'
    iraf.unlearn(iraf.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)
    iraf.apphot.phot.setParam('interactive',"no")
    iraf.apphot.phot.setParam('verify',"no")
    iraf.datapars.setParam('datamax',50000.)
    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise")
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass")
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma',"INDEF")
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)
    iraf.datapars.setParam('fwhmpsf',fwhm_i)
    iraf.photpars.setParam('apertures',2.*fwhm_i)
    iraf.fitskypars.setParam('annulus',4.*fwhm_i)

    iraf.apphot.phot(image=fits_i, coords=fits_i+'.coo.1')

# get rid of regions you don't want using pselect    
if not os.path.isfile('mask.reg'):
    print 'To continue you should mask out bright stars, galaxies, etc.'
    print 'in DS9 and export to an IRAF PROS file named mask.reg'
    raw_input("Press Enter when finished:")


m3,m4,m5,m6 = np.loadtxt('mask.reg',usecols=(2,3,4,5),unpack=True)
# g image pselects
if not os.path.isfile(fits_g+'.mag.1a') :
    if os.path.isfile('temp2') :    
        os.remove('temp2')
    iraf.ptools.pselect(infi=fits_g+'.mag.1', outfi='temp1', expr="MAG != INDEF")
    for i in range(len(m3)) :
        mx1 = m3[i] - (m5[i]/2.)
        mx2 = m3[i] + (m5[i]/2.)
        my1 = m4[i] - (m6[i]/2.)
        my2 = m4[i] + (m6[i]/2.)
        iraf.ptools.pselect(infi='temp1', outfi='temp2', expr='(XCE < '+repr(int(mx1))+' || XCE > '+repr(int(mx2))+') || (YCE < '+repr(int(my1))+' || YCE > '+repr(int(my2))+')')
        os.rename('temp2', 'temp1')
    os.rename('temp1', fits_g+'.mag.1a')
    if os.path.isfile('temp1') :    
        os.remove('temp1')

# i image pselects
if not os.path.isfile(fits_i+'.mag.1a') :
    if os.path.isfile('temp2') :    
        os.remove('temp2')
    iraf.ptools.pselect(infi=fits_i+'.mag.1', outfi='temp1', expr="MAG != INDEF")
    for i in range(len(m3)) :
        mx1 = m3[i] - (m5[i]/2.)
        mx2 = m3[i]+ (m5[i]/2.)
        my1 = m4[i] - (m6[i]/2.)
        my2 = m4[i] + (m6[i]/2.)
        iraf.ptools.pselect(infi='temp1', outfi='temp2', expr='(XCE < '+repr(int(mx1))+' || XCE > '+repr(int(mx2))+') || (YCE < '+repr(int(my1))+' || YCE > '+repr(int(my2))+')')
        os.rename('temp2', 'temp1')
    os.rename('temp1', fits_i+'.mag.1a')
    if os.path.isfile('temp1') :    
        os.remove('temp1')

# mkobsfile stuff
# mkobsfile MATCHES sources between images to get rid of random sources, things that are masked in one or the other, etc.
iraf.mkobsfile.setParam('photfiles',title_string+'_*_sh.fits.mag.1a')
iraf.mkobsfile.setParam('idfilters','r,g')
iraf.mkobsfile.setParam('imsets',title_string+'.imsets')
iraf.mkobsfile.setParam('obscolumns','2 3 4 5')
iraf.mkobsfile.setParam('shifts',None)
iraf.mkobsfile.setParam('apercors',None)
iraf.mkobsfile.setParam('allfilters','yes')

# if not os.path.isfile('ifirst_tol6.out') :
#     iraf.mkobsfile.setParam('observations','ifirst_tol6.out')
#     iraf.mkobsfile.setParam('tolerance',6.)
#     iraf.mkobsfile()

if not os.path.isfile('ifirst_tol7.out') :
    iraf.mkobsfile.setParam('observations','ifirst_tol7.out')
    iraf.mkobsfile.setParam('tolerance',7.) # number of pixels away matched source can be, DATA DEPENDENT!
    iraf.mkobsfile()

# if not os.path.isfile('ifirst_tol8.out') :
#     iraf.mkobsfile.setParam('observations','ifirst_tol8.out')
#     iraf.mkobsfile.setParam('tolerance',8.)
#     iraf.mkobsfile()
# call("awk '{ if ($2 ~ "odi_i") print $5, $6 }' ifirst_tol7.dat > tol7_i.pos")

# print matched sources to a file suitable for marking
if os.path.isfile('ifirst_tol7.out') :
    mx,my = np.loadtxt('ifirst_tol7.out',usecols=(4,5),unpack=True)
    mfilter = np.loadtxt('ifirst_tol7.out',usecols=(1,),dtype=str,unpack=True)
    match_pos_file_g = open("tol7_g.pos", 'w+')
    match_pos_file_i = open("tol7_i.pos", 'w+')
    for i in range(len(mx)) :
        if mfilter[i]== 'g' :
            print >> match_pos_file_g, mx[i], my[i]
        if mfilter[i] == 'r' :
            print >> match_pos_file_i, mx[i], my[i]
    match_pos_file_g.close()
    match_pos_file_i.close()
    
# import the getfwhm task as a pyraf task
iraf.task(getfwhm = "home$scripts/getfwhm.cl")
# print iraf.getfwhm.getCode()

# you might want to remeasure the FWHMs to get a better global estimate now that we (should) only have good sources in the image
# use getfwhm, which is just a loop on imexam. (try to improve this with ralf's qr code)
if not os.path.isfile('getfwhm_g.log') :
    iraf.unlearn(iraf.imexamine, iraf.rimexam)
    iraf.getfwhm.setParam('images',fits_g)
    iraf.getfwhm.setParam('coordlist','tol7_g.pos')
    iraf.getfwhm.setParam('outfile','getfwhm_g.log')
    iraf.getfwhm.setParam('center','no')
    iraf.imexamine.setParam('frame',1)
    iraf.getfwhm()

if not os.path.isfile('getfwhm_i.log') :
    iraf.getfwhm.setParam('images',fits_i)
    iraf.getfwhm.setParam('coordlist','tol7_i.pos')
    iraf.getfwhm.setParam('outfile','getfwhm_i.log')
    iraf.getfwhm.setParam('center','no')
    iraf.imexamine.setParam('frame',2)
    iraf.getfwhm()
    
# determine the aperture correction needed--this is actually an extremely important step. uses 4.5x the measured FWHM as the aperture DATA DEPENDENT 
ap_gx,ap_gy = np.loadtxt('getfwhm_g.log',usecols=(0,1),unpack=True)
ap_mag_g = np.loadtxt('getfwhm_g.log',usecols=(5,),dtype=str,unpack=True)
ap_peak_g = np.loadtxt('getfwhm_g.log',usecols=(8,),dtype=str,unpack=True)
ap_fwhm_g = np.loadtxt('getfwhm_g.log',usecols=(12,),dtype=str,unpack=True)
ap_ix,ap_iy = np.loadtxt('getfwhm_i.log',usecols=(0,1),unpack=True)
ap_mag_i = np.loadtxt('getfwhm_i.log',usecols=(5,),dtype=str,unpack=True)
ap_peak_i = np.loadtxt('getfwhm_i.log',usecols=(8,),dtype=str,unpack=True)
ap_fwhm_i = np.loadtxt('getfwhm_i.log',usecols=(12,),dtype=str,unpack=True)

ap_cand1_g = [(ap_gx[i],ap_gy[i],float(ap_fwhm_g[i]),float(ap_peak_g[i]),float(ap_mag_g[i])) for i in range(len(ap_gx)) if (ap_peak_g[i] != 'INDEF' and ap_fwhm_g[i] != 'INDEF' and ap_mag_g[i] != 'INDEF')]
ap_cand1_i = [(ap_ix[i],ap_iy[i],float(ap_fwhm_i[i]),float(ap_peak_i[i]),float(ap_mag_i[i])) for i in range(len(ap_ix)) if (ap_peak_i[i] != 'INDEF' and ap_fwhm_i[i] != 'INDEF' and ap_mag_i[i] != 'INDEF')]

if fwhm_i < 20.0 :
    ap_cand_g = [ap_cand1_g[i] for i in range(len(ap_cand1_g)) if (5000. < ap_cand1_g[i][3] < 15000.)]
    ap_cand_i = [ap_cand1_i[i] for i in range(len(ap_cand1_i)) if (5000. < ap_cand1_i[i][3] < 15000.)]
    # print ap_cand_g, ap_cand_i
    ap_avg_g1 = np.mean([ap_cand_g[i][2] for i in range(len(ap_cand_g))])
    ap_avg_i1 = np.mean([ap_cand_i[i][2] for i in range(len(ap_cand_i))])

    ap_std_g1 = np.std([ap_cand_g[i][2] for i in range(len(ap_cand_g))])
    ap_std_i1 = np.std([ap_cand_i[i][2] for i in range(len(ap_cand_i))])
    # print ap_avg_g1,ap_avg_i1,ap_std_g1,ap_std_i1
    ap_stars_g = [ap_cand_g[i] for i in range(len(ap_cand_g))]# if ((ap_avg_g1-ap_std_g1) < ap_cand_g[i][2] < (ap_avg_g1+ap_std_g1))]
    ap_stars_i = [ap_cand_i[i] for i in range(len(ap_cand_i))]# if ((ap_avg_i1-ap_std_i1) < ap_cand_i[i][2] < (ap_avg_i1+ap_std_i1))]
    # print len(ap_stars_g), len(ap_stars_i)
    ap_avg_g = np.mean([ap_stars_g[i][2] for i in range(len(ap_stars_g))])
    ap_avg_i = np.mean([ap_stars_i[i][2] for i in range(len(ap_stars_i))])

    ap_std_g = np.std([ap_stars_g[i][2] for i in range(len(ap_stars_g))])
    ap_std_i = np.std([ap_stars_i[i][2] for i in range(len(ap_stars_i))])
    print 'Measured image FWHM :: g = {0:5.3f} : i = {1:5.3f}'.format(ap_avg_g,ap_avg_i)

    ap_file_g = open('apcor_stars_g.txt','w+')
    ap_file_i = open('apcor_stars_i.txt','w+')

    for i in range(len(ap_stars_g)) :
        print >> ap_file_g, ap_stars_g[i][0], ap_stars_g[i][1], ap_stars_g[i][2], ap_stars_g[i][3]
    for i in range(len(ap_stars_i)) :
        print >> ap_file_i, ap_stars_i[i][0], ap_stars_i[i][1], ap_stars_i[i][2], ap_stars_i[i][3]

    ap_file_g.close()
    ap_file_i.close()

    # iraf.unlearn(iraf.tv.tvmark)
    # iraf.tv.tvmark.setParam('label',"no")
    # iraf.tv.tvmark.setParam('pointsize',7)
    # iraf.tv.tvmark.setParam('mark',"circle")
    # # iraf.tv.tvmark(frame=1, coords='apcor_stars_g.txt', radii="98,99,100,101,102,103", color=208)
    # iraf.tv.tvmark(frame=2, coords='apcor_stars_i.txt', radii="98,99,100,101,102,103", color=208)

    # iraf.getfwhm.setParam('images',fits_g)
    # iraf.getfwhm.setParam('coordlist','apcor_stars_g.txt')
    # iraf.getfwhm.setParam('outfile','apcorfwhmcheck_g.log')
    # iraf.getfwhm()
    # 
    # iraf.getfwhm.setParam('images',fits_i)
    # iraf.getfwhm.setParam('coordlist','apcor_stars_i.txt')
    # iraf.getfwhm.setParam('outfile','apcorfwhmcheck_i.log')
    # iraf.getfwhm()

    iraf.unlearn(iraf.apphot.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)

    iraf.apphot.phot.setParam('interactive','no')
    iraf.apphot.phot.setParam('verify','no')

    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise")
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass")
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma','INDEF')
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)

    iraf.datapars.setParam('fwhmpsf',ap_avg_g)
    iraf.photpars.setParam('apertures',str('"'+repr(ap_avg_g)+','+repr(5.0*ap_avg_g)+'"'))
    iraf.fitskypars.setParam('annulus',6.5*ap_avg_g)

    iraf.apphot.phot(image=fits_g, coords='apcor_stars_g.txt', output="g.apcor.mag.1")

    iraf.datapars.setParam('fwhmpsf',ap_avg_i)
    iraf.photpars.setParam('apertures',str('"'+repr(ap_avg_i)+','+repr(5.0*ap_avg_i)+'"'))
    iraf.fitskypars.setParam('annulus',6.5*ap_avg_i)
    iraf.apphot.phot(image=fits_i, coords='apcor_stars_i.txt', output="i.apcor.mag.1")

    apt_file_g = open("apcor_table_g.txt", 'w+')
    apt_file_i = open("apcor_table_i.txt", 'w+')

    iraf.ptools.txdump(textfiles='g.apcor.mag.1', fields="ID,XCEN,YCEN,MAG", expr='yes', Stdout=apt_file_g)
    iraf.ptools.txdump(textfiles='i.apcor.mag.1', fields="ID,XCEN,YCEN,MAG", expr='yes', Stdout=apt_file_i)
    apt_file_g.close()
    apt_file_i.close()

    onex_g,four5x_g = np.loadtxt('apcor_table_g.txt',usecols=(3,4),unpack=True)
    onex_i,four5x_i = np.loadtxt('apcor_table_i.txt',usecols=(3,4),unpack=True)

    apcor_ind_g = four5x_g - onex_g
    apcor_g = np.mean(apcor_ind_g)
    apcor_std_g = np.std(apcor_ind_g)
    apcor_sem_g = apcor_std_g/np.sqrt(len(apcor_ind_g))

    apcor_ind_i = four5x_i - onex_i
    apcor_i = np.mean(apcor_ind_i)
    apcor_std_i = np.std(apcor_ind_i)
    apcor_sem_i = apcor_std_i/np.sqrt(len(apcor_ind_i))

    print 'Aperture correction :: g = {0:7.4f} : i = {1:7.4f}'.format(apcor_g,apcor_i)
    print 'Aperture corr. StD. :: g = {0:6.4f} : i = {1:6.4f}'.format(apcor_std_g,apcor_std_i)
    print 'Aperture corr. SEM  :: g = {0:6.4f} : i = {1:6.4f}'.format(apcor_sem_g,apcor_sem_i)
    print 'Aperture corr. N    :: g = {0:2d} : i = {1:2d}'.format(len(onex_g),len(onex_i))


    apcor_tbl = open('apcor.tbl.txt','w+')
    print >> apcor_tbl, apcor_g, apcor_std_g, apcor_sem_g
    print >> apcor_tbl, apcor_i, apcor_std_i, apcor_sem_i
    apcor_tbl.close()
else :
    apcor_g = 0.0
    apcor_i = 0.0
    print 'Seeing is pretty bad, no aperture correction applied.'
# try :
#     if not os.path.isfile('point_source_info') :
#         call('escut')
# except :
#     print 'Something went wrong running escut. Try running it outside of this script.'


# do an extended source cut to get rid of background galaxies/etc. subject to change
if not os.path.isfile('escut_i.pos') :
    def onclicki(event):
        global fig, ax,i_mag, i_fwhm, ix, iy
        if event.button ==1 :
            # print event.xdata, event.ydata
            ax.cla()
            ax.scatter(i_mag,i_fwhm, edgecolors='none')
            ax.set_ylim(0,15)
            ax.set_xlabel('magnitude')
            ax.set_ylabel('FWHM')
            ix.append(event.xdata)
            iy.append(event.ydata)
        # print ix,iy
            ax.plot(ix, iy ,'r-', lw=3, alpha=0.6)
        elif event.button == 3 :
            #print 'Removedlast point from shape'
            ix.pop()
            iy.pop()
            ax.cla()
            ax.scatter(i_mag,i_fwhm, edgecolors='none')
            ax.set_ylim(0,15)
            ax.set_xlabel('magnitude')
            ax.set_ylabel('FWHM')
            ax.plot(ix, iy ,'r-', lw=3, alpha=0.6)
        elif event.key == 'q' :
            print 'Finished recording points'
            fig.canvas.mpl_disconnect(cid)
        fig.canvas.draw()
        return True
        
    def onclickg(event):
        global fig, ax, g_mag, g_fwhm, gx, gy
        if event.button == 1 :
        # print event.xdata, event.ydata
            ax.cla()
            ax.scatter(g_mag,g_fwhm, edgecolors='none')
            ax.set_ylim(0,15)
            ax.set_xlabel('magnitude')
            ax.set_ylabel('FWHM')
            gx.append(event.xdata)
            gy.append(event.ydata)
            ax.plot(gx, gy ,'r-', lw=3, alpha=0.6)
        elif event.button == 3 :
            #print 'Removedlast point from shape'
            gx.pop()
            gy.pop()
            ax.cla()
            ax.scatter(g_mag,g_fwhm, edgecolors='none')
            ax.set_ylim(0,15)
            ax.set_xlabel('magnitude')
            ax.set_ylabel('FWHM')
            ax.plot(gx, gy ,'r-', lw=3, alpha=0.6)
        elif event.key == 'q' :
            print 'Finished recording points'
            fig.canvas.mpl_disconnect(cid)
        fig.canvas.draw()
        return True
    
    # get preliminary magnitude data which is close enough for this purpose
    i0l = []
    g0l = []
    ifl = []
    gfl = []
    ixl = []
    gxl = []
    iyl =[]
    gyl = []
    
    with open('ifirst_tol7.out','r') as fin:
        lines = fin.readlines()
        for i, line in enumerate(lines):
            items = line.split()
            if len(items) > 0 :
                if items[1] == 'odi_i':
                    i0l.append(float(items[6]))
                    ixl.append(float(items[4]))
                    iyl.append(float(items[5]))
                elif items[1] == 'odi_g':
                    g0l.append(float(items[6]))
                    gxl.append(float(items[4]))
                    gyl.append(float(items[5]))
                # else:
                #     print 'Ignored line',i,'in',mkobsfile,'during read'
            # else:
            #     print 'Ignored line',i,'in',mkobsfile,'during read'
    
    with open('getfwhm_i.log','r') as fin :
        lines = fin.readlines()
        for i, line in enumerate(lines):
            items =line.split()
            if items[0] != '#':
                if items[12] != 'INDEF':
                    ifl.append(float(items[12]))
                else:
                    ifl.append(999.999)
            # else:
            #     print 'Ignored line',i,'in', ifwhm, 'during read'
                
    with open('getfwhm_g.log','r') as fin :
        lines = fin.readlines()
        for i, line in enumerate(lines):
            items = line.split()
            if items[0] != '#':
                if items[12] != 'INDEF':
                    gfl.append(float(items[12]))
                else:
                    gfl.append(999.999)
            # else:
            #     print 'Ignored line',i,'in', gfwhm, 'during read'
    
    i_i = np.array(i0l)
    g_i = np.array(g0l)
    i_fwhm = np.array(ifl)
    g_fwhm = np.array(gfl)

    g0 = g_i - (kg*amg) + apcor_g 
    i0 = i_i - (ki*ami) + apcor_i

    gmi = mu_gi*(g0-i0) + zp_gi
    i_mag = i0 + eps_gi*(gmi) + zp_i
    g_mag = gmi + i_mag
    
    
    
    if not os.path.isfile('escutRegion_i.txt'):
        print 'Recording region for I-BAND extended source cut.'
        print 'left click to select vertices, right click to delete last point'
        print "press 'q' when finished"
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(i_mag,i_fwhm,edgecolors='none')
        ax.set_ylim(0,15)
        ax.set_xlabel('magnitude')
        ax.set_ylabel('FWHM')
        
        ix = []
        iy = []
        cid = fig.canvas.mpl_connect('button_press_event', onclicki)
        
        plt.show()
        
        with open('escutRegion_i.txt','w+') as fout:
            for i in range(len(ix)):
                print >> fout, ix[i], iy[i]
            
    else :
        print 'Using prerecorded escut file for i-band'
        ix, iy = np.loadtxt('escutRegion_i.txt',usecols=(0,1),unpack=True)
        
    
    if not os.path.isfile('escutRegion_g.txt'):
        print 'Recording region for G-BAND extended source cut.'
        print 'left click to select vertices, right click to delete last point'
        print "press 'q' when finished"
        fig =plt.figure()
        ax = fig.add_subplot(111)
        ax.scatter(g_mag,g_fwhm,edgecolors='none')
        ax.set_ylim(0,15)
        ax.set_xlabel('magnitude')
        ax.set_ylabel('FWHM')
        
        gx = []
        gy = []
        cid = fig.canvas.mpl_connect('button_press_event', onclickg)
        
        plt.show()
        
        with open('escutRegion_g.txt','w+') as fout:
            for i in range(len(gx)):
                print >> fout, gx[i], gy[i]
    else :
        print 'Using prerecorded escut file for g-band'
        gx, gy = np.loadtxt('escutRegion_g.txt',usecols=(0,1),unpack=True)
    
    iverts = zip(ix,iy)        # set up the Path necessary for testing membership
    ipoints = zip(i_mag,i_fwhm)
    i_filter = Path(iverts)
    gverts = zip(gx,gy)        # set up the Path necessary for testing membership
    g_filter = Path(gverts)
    gpoints = zip(g_mag,g_fwhm)
    
    stars_f_i = i_filter.contains_points(ipoints)
    stars_f_g = g_filter.contains_points(gpoints)
    
    # escutFlag2 = np.genfromtxt('escutFlag2.txt', dtype=bool, usecols=(0,),unpack=True)

    
    match_f = list(stars_f_i)
    with open('escutFlag.txt','w+') as escutflag:
        for i in range(len(stars_f_i)) :
            match_f[i] = stars_f_i[i] and stars_f_g[i] #and escutFlag2[i]
            print >> escutflag, match_f[i],i_mag[i],i_fwhm[i]
    test = [match_f[i] for i in range(len(match_f)) if (match_f[i])]
        
    print len(test), 'stars matched'
    with open('magfwhm_gi.txt','w+') as fout:
        for i in range(len(i_mag)):
            if match_f[i] == True :
                print >> fout, gxl[i],gyl[i],g_mag[i],g_fwhm[i],ixl[i],iyl[i],i_mag[i],i_fwhm[i]
    escut_pos_file_g = open("escut_g.pos", 'w+')
    escut_pos_file_i = open("escut_i.pos", 'w+')
    for i in range(len(match_f)) :
        if match_f[i] == True :
            print >> escut_pos_file_g, gxl[i], gyl[i]
            print >> escut_pos_file_i, ixl[i], iyl[i]
    escut_pos_file_g.close()
    escut_pos_file_i.close()        
    
# finally rephot just the good stuff to get a good number
if os.path.isfile('escut_g.pos') :
    iraf.unlearn(iraf.phot,iraf.datapars,iraf.photpars,iraf.centerpars,iraf.fitskypars)
    #
    iraf.apphot.phot.setParam('interactive',"no")
    iraf.apphot.phot.setParam('verify',"no")
    iraf.datapars.setParam('datamin',"INDEF")
    iraf.datapars.setParam('datamax',50000.)
    iraf.datapars.setParam('gain',"gain")
    iraf.datapars.setParam('ccdread',"rdnoise")
    iraf.datapars.setParam('exposure',"exptime")
    iraf.datapars.setParam('airmass',"airmass")
    iraf.datapars.setParam('filter',"filter")
    iraf.datapars.setParam('obstime',"time-obs")
    iraf.datapars.setParam('sigma',"INDEF")
    iraf.photpars.setParam('zmag',0.)
    iraf.centerpars.setParam('calgorithm',"centroid")
    iraf.centerpars.setParam('cbox',9.)
    iraf.centerpars.setParam('maxshift',3.)
    iraf.fitskypars.setParam('salgorithm',"median")
    iraf.fitskypars.setParam('dannulus',10.)
#
    # Use an aperture that is 1 x <fwhm>, because an aperture correction
    # will be applied in the calc_calib_mags step
    # Using a sky annulus thatbegins at 6 x <fwhm> should be fine
    # g-band
    if not os.path.isfile(title_string+'_sources_g.mag.1') :
        print 'Phot-ing g band point sources, this could take a while.'
        iraf.datapars.setParam('fwhmpsf',ap_avg_g)
        iraf.photpars.setParam('apertures',ap_avg_g)
        iraf.fitskypars.setParam('annulus',6*ap_avg_g)
        iraf.apphot.phot(image=fits_g, coords='escut_g.pos', output=title_string+'_sources_g.mag.1')

# i-band    
if os.path.isfile('escut_i.pos') :
    if not os.path.isfile(title_string+'_sources_i.mag.1') :
        print 'Phot-ing i band point sources, this could take a while.'
        iraf.datapars.setParam('fwhmpsf',ap_avg_i)
        iraf.photpars.setParam('apertures',ap_avg_i)
        iraf.fitskypars.setParam('annulus',6*ap_avg_i)
        iraf.apphot.phot(image=fits_i, coords='escut_i.pos', output=title_string+'_sources_i.mag.1')


def getexttbl(ra,dec,fname='extinction.tbl.txt'):
    '''Takes RA and Dec in colon separated sexagesimal format and queries 
        http://irsa.ipac.caltech.edu/ for the extinction table at that location
        File is saved as extinction.tbl.txt or as specified by user in optional 3rd arg'''
    import urllib2
    from BeautifulSoup import BeautifulSoup
    # parse the ra and dec
    ravals = ra.split(':')
    decvals = dec.split(':')

    ra_str = ravals[0]+'h'+ravals[1]+'m'+ravals[2]+'s'
    dec_str = decvals[0]+'d'+decvals[1]+'m'+decvals[2]+'s'

    # set the url to go get the extinction table
    exturl = "http://irsa.ipac.caltech.edu/cgi-bin/DUST/nph-dust?locstr="+ra_str+'+'+dec_str+'+equ+j2000' 

    xmlget = urllib2.urlopen(exturl)
    soup = BeautifulSoup(xmlget,"xml")
    # print soup.prettify()

    tblurl = soup.result.data.table.string
    exttbl = urllib2.urlopen(tblurl)

    f = open(fname,'w+')
    print >> f, exttbl.read()
    f.close()

if not os.path.isfile('extinction.tbl.txt'):
    print 'Fetching extinction table for',fits_h_i[0].header['RA'],fits_h_i[0].header['DEC']
    getexttbl(fits_h_i[0].header['RA'],fits_h_i[0].header['DEC'])

LamEff,A_over_E_B_V_SandF,A_SandF,A_over_E_B_V_SFD,A_SFD= np.genfromtxt('extinction.tbl.txt', usecols=(2,3,4,5,6),unpack=True,skip_header=27,skip_footer=12)
A_id = np.genfromtxt('extinction.tbl.txt', usecols=(1,),dtype=str,unpack=True,skip_header=27,skip_footer=12)
E_B_V = np.genfromtxt('extinction.tbl.txt', usecols=(2,),skip_header=1,skip_footer=42)

for j in range(len(A_id)):
    if A_id[j] == 'g':
        cal_A_g = A_over_E_B_V_SandF[j]*0.86*E_B_V # E(B-V) is the Schlegel+ value, S&F say with their calibration
for j in range(len(A_id)):                                  # use 0.86*E(B-V) instead. cf. S&F2011 pg 1, 2011ApJ...737..103S
    if A_id[j] == 'r':
        cal_A_i = A_over_E_B_V_SandF[j]*0.86*E_B_V
        
print 'Reddening correction :: g = {0:7.4f} : i = {1:7.4f}'.format(cal_A_g,cal_A_i)

# f_zp_g = open(title_string+'_g_phot.zp')
# data_g = f_zp_g.read()
# fl_g = data_g.split('\n', 1)[0]
# zp_vals_g = fl_g.split()
# cal_zp_g = float(zp_vals_g[2])
# cal_color_g = float(zp_vals_g[0])
# cal_zp_ge = float(zp_vals_g[3])
# cal_color_ge = float(zp_vals_g[1])
# 
# f_zp_i = open(title_string+'_i_phot.zp')
# data = f_zp_i.read()
# fl_i = data.split('\n', 1)[1]
# zp_vals_i = fl_i.split()
# cal_zp_i = float(zp_vals_i[0])
# cal_zp_ie = float(zp_vals_i[1])



# print 'Zero point :: g = {0:7.4f} : i = {1:7.4f}'.format(cal_zp_g,cal_zp_i)
# print 'Zero point err :: g = {0:7.4f} : i = {1:7.4f}'.format(cal_zp_ge,cal_zp_ie)
# 
# print 'gi color term :: eps = {0:7.4f}'.format(cal_color_g)
# print 'gi color term err :: eps = {0:7.4f}'.format(cal_color_ge)

txdump_out = open('phot_sources.txdump','w+')
iraf.ptools.txdump(textfiles=title_string+'_sources_*.mag.1', fields="id,mag,merr,msky,stdev,rapert,xcen,ycen,ifilter,xairmass,image", expr='yes', headers='no', Stdout=txdump_out)
txdump_out.close()

call('sort -g phot_sources.txdump > temp', shell=True)
call('mv temp phot_sources.txdump', shell=True)
call('awk -f ~/uchvc/tools/make_calibdat phot_sources.txdump > calibration.dat', shell=True)

nid,gx,gy,g_i,g_ierr,ix,iy,i_i,i_ierr = np.loadtxt('calibration.dat',usecols=(0,1,2,4,5,11,12,14,15),unpack=True)

# AGC198606 specific values
# mu_gi = 1.055
# zp_gi = 0.571
# eps_gi = 0.007
# zp_i = 25.894
# 
# kg = 0.200
# ki = 0.058
# 
# amg = 1.082642493
# ami = 1.208449087

# g-i = mu_gi * (g0 - i0) + ZP_gi
# i = eps_gi * (g-i) + ZP_i
g0 = g_i - (kg*amg) + apcor_g 
i0 = i_i - (ki*ami) + apcor_i
gmi = mu_gi*(g0-i0) + zp_gi

i_mag = i0 + eps_gi*gmi + zp_i #- cal_A_i 
g_mag = gmi + i_mag - cal_A_g 
i_mag = i_mag - cal_A_i
gmi = g_mag - i_mag

print 'Median (g-i) :: g - i = {0:7.4f}'.format(np.median(gmi))
print 'Final number of phot-ed stars :: g = {0:5d} : i = {1:5d}'.format(len(g_mag),len(i_mag))

g_mag_lims = [g_mag[i] for i in range(len(g_mag)) if (g_ierr[i] >= 0.2)]
i_mag_lims = [i_mag[i] for i in range(len(i_mag)) if (i_ierr[i] >= 0.2)]

print '5-sigma limit :: g = {0:7.4f} : i = {1:7.4f}'.format(min(g_mag_lims), min(i_mag_lims))

f3 = open('calibrated_mags.dat', 'w+')
for i in range(len(ix)) :
    print >> f3, '{0:8.2f} {1:8.2f} {2:12.3f} {3:12.3f} {4:8.2f} {5:8.2f} {6:12.3f} {7:12.3f} {8:12.3f} '.format(gx[i],gy[i],g_mag[i],g_ierr[i],ix[i],iy[i],i_mag[i],i_ierr[i],gmi[i])
f3.close()

# delete the pipeline WCS keywords from the header, Steven's are better
iraf.imutil.hedit(images=fits_g, fields='PV*', delete='yes', verify='no')
iraf.imutil.hedit(images=fits_i, fields='PV*', delete='yes', verify='no')

