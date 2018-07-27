import numpy as np
import astropy
import lsst.sims.featureScheduler as fs
from lsst.sims.utils import Site


# Generate information useful for scheduling the DD fields

dd_surveys = fs.generate_dd_surveys()

survey_names = [survey.survey_name for survey in dd_surveys if ':u,' not in survey.survey_name]

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
location = astropy.coordinates.EarthLocation(site.longitude_rad,
                                             site.latitude_rad,
                                             site.height*astropy.units.m)

print('Comuting sun positions')
sun_position = astropy.coordinates.get_sun(times)
print('Done with sun')
sun_altaz = sun_position.transform_to(astropy.coordinates.AltAz(location=location))

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

dtypes = [float]*len(names)
dd_info = np.zeros(mjds.size, dtype=list(zip(names, dtypes)))

dd_info['mjd'] = mjds

for survey in dd_surveys:
    if survey.survey_name in survey_names:
        print('Computing survey: %s' % survey.survey_name)
        ra_rad = survey.ra
        dec_rad = survey.dec
        dd_coord = astropy.coordinates.SkyCoord(ra_rad*astropy.units.rad, dec_rad*astropy.units.rad)

        dd_alt_az = dd_coord.transform_to(astropy.coordinates.AltAz(location=location, obstime=times))
        moon_dist = dd_coord.separation(moon_position).degree
        dd_info[survey.survey_name.replace('DD:', '')+'_moon_dist'] = moon_dist

        dd_alt_az = dd_coord.transform_to(astropy.coordinates.AltAz(location=location, obstime=times))
        dd_info[survey.survey_name.replace('DD:', '')+'_alt'] = dd_alt_az.alt
        print('Done with %s' % survey.survey_name)

print('Saving')
np.savez('dd_info.npz', dd_info=dd_info)
