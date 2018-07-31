import numpy as np
import astropy
import lsst.sims.featureScheduler as fs
from lsst.sims.utils import Site
import lsst.sims.skybrightness as sb
import sys
import time


t0 = time.time()

# Generate information useful for scheduling the DD fields

dd_surveys = fs.generate_dd_surveys()
# toss the u-band only ones
dd_surveys = [survey for survey in dd_surveys if ':u,' not in survey.survey_name]
survey_names = [survey.survey_name for survey in dd_surveys]

# Set the start
mjd0 = 59580.0381944435
length = 365.25 * 10.05
# Use half-hour timesteps
timestep = 0.5 / 24.
mjds = np.arange(mjd0, mjd0+length, timestep)
times = astropy.time.Time(mjds, format='mjd')

# What limit do we put on the sun
sun_alt_limit = -20

# The Site
site = Site(name='LSST')
location = astropy.coordinates.EarthLocation(site.longitude_rad*astropy.units.rad,
                                             site.latitude_rad*astropy.units.rad,
                                             site.height*astropy.units.m)

print('Computing sun positions')
sun_position = astropy.coordinates.get_sun(times)
sun_altaz = sun_position.transform_to(astropy.coordinates.AltAz(location=location))
print('Done with sun')

# Crop off mjds where the sun is too high
sun_down = np.where(sun_altaz.alt < sun_alt_limit*astropy.units.deg)

mjds = mjds[sun_down]
times = astropy.time.Time(mjds, format='mjd')

# Compute the moon position
print('Computing moon position')
moon_position = astropy.coordinates.get_moon(times)
print('Moon Done')
names = ['mjd']
for name in survey_names:
    names.append(name.replace('DD:', '')+'_moon_dist')
    names.append(name.replace('DD:', '')+'_alt')
    names.append(name.replace('DD:', '')+'_g_sb')

dtypes = [float]*len(names)
dd_info = np.zeros(mjds.size, dtype=list(zip(names, dtypes)))

dd_info['mjd'] = mjds
skyModel = sb.SkyModel(mags=True)
for survey in dd_surveys:
    if survey.survey_name in survey_names:
        print('Computing survey: %s' % survey.survey_name)
        ra_rad = survey.ra
        dec_rad = survey.dec
        dd_coord = astropy.coordinates.SkyCoord(ra_rad*astropy.units.rad, dec_rad*astropy.units.rad)

        moon_dist = dd_coord.separation(moon_position).degree
        dd_info[survey.survey_name.replace('DD:', '')+'_moon_dist'] = moon_dist

        dd_alt_az = dd_coord.transform_to(astropy.coordinates.AltAz(location=location, obstime=times))
        dd_info[survey.survey_name.replace('DD:', '')+'_alt'] = dd_alt_az.alt
        print('Done with %s' % survey.survey_name)

ras = [survey.ra for survey in dd_surveys]
decs = [survey.dec for survey in dd_surveys]
skymags = np.zeros((mjds.size, len(ras)))

print('Computing sky brighntess values')
imax = float(np.size(mjds))
for i, mjd in enumerate(mjds):
    skyModel.setRaDecMjd(ras, decs, mjd, degrees=False)
    # look in the model to check if points are good
    if skyModel.goodPix.size > 0:
        skymags[i] = skyModel.returnMags()['g']

    progress = i/imax*100
    text = '\rprogress = %.1f%%' % progress
    sys.stdout.write(text)
    sys.stdout.flush()


for i, survey in enumerate(dd_surveys):
    dd_info[survey.survey_name.replace('DD:', '')+'_g_sb'] = skymags[:, i]

print('Saving')
np.savez('dd_info.npz', dd_info=dd_info)
delta_t = time.time() - t0
print('genererated grid for %i years in %i minutes' % (length/365.25, delta_t/60.))
