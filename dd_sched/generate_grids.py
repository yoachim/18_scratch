import numpy as np
import astropy
import lsst.sims.featureScheduler as fs
from lsst.sims.utils import Site


# Generate information useful for scheduling the DD fields

dd_surveys = fs.generate_dd_surveys()

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

sun_position = astropy.coordinates.get_sun(times)

sun_altaz = sun_position.transform_to(astropy.coordinates.AltAz(location=location))

# Crop off mjds where the sun is too high
sun_down = np.where(sun_altaz.alt < sun_alt_limit)

mjds = mjds[sun_down]
times = astropy.time.Time(mjds, format='mjd')

# Compute the moon position
moon_position = astropy.coordinates.get_moon(times)

for survey in dd_surveys:
    ra_rad = survey.ra
    dec_rad = survey.dec
    dd_coord = astropy.coordinates.SkyCoord(ra_rad*astropy.units.rad, dec_rad*astropy.units.rad)
    dd_alt_az = dd_coord.transform_to(astropy.coordinates.AltAz(location=location, obstime=times))
    moon_dist = dd_coord.separation(moon_position).degree