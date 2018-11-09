import numpy as np

from astroplan import Observer
from astropy.coordinates import EarthLocation
import astropy.units as u
from astropy.time import Time


observer = Observer(longitude=-70.7494*u.deg, latitude=-30.2444*u.deg,
                   elevation=2650.0*u.m, name="LSST")

mjd_start=59853.5


times = Time(np.arange(mjd_start, mjd_start+356.25*3, .3), format='mjd')


tt = observer.twilight_evening_astronomical(times)

ack = observer.moon_rise_time(times)

round_ack = np.round(ack.mjd, decimals=5)

