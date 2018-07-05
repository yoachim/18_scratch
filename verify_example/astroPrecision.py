import numpy as np

from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord


# Stolen from lsst.sims.maf.utils. Should probably go to a more general library.
def gnomonic_project_toxy(RA1, Dec1, RAcen, Deccen):
    """
    Calculate the x/y values of RA1/Dec1 in a gnomonic projection with center at RAcen/Deccen.

    Parameters
    ----------
    RA1 : numpy.ndarray
        RA values of the data to be projected, in radians.
    Dec1 : numpy.ndarray
        Dec values of the data to be projected, in radians.
    RAcen: float
        RA value of the center of the projection, in radians.
    Deccen : float
        Dec value of the center of the projection, in radians.

    Returns
    -------
    numpy.ndarray, numpy.ndarray
        The x/y values of the projected RA1/Dec1 positions.
    """
    cosc = np.sin(Deccen) * np.sin(Dec1) + np.cos(Deccen) * np.cos(Dec1) * np.cos(RA1-RAcen)
    x = np.cos(Dec1) * np.sin(RA1-RAcen) / cosc
    y = (np.cos(Deccen)*np.sin(Dec1) - np.sin(Deccen)*np.cos(Dec1)*np.cos(RA1-RAcen)) / cosc
    return x, y

# from lsst.sims.maf.utils.
# For justification for simplified astromertic error propigation, see:
# https://github.com/yoachim/18_scratch/tree/master/astrom_exmaple
# Which should be put into a tech note
def sigma_slope(x, sigma_y):
    """
    Calculate the uncertainty in fitting a line, as
    given by the spread in x values and the uncertainties
    in the y values.

    Parameters
    ----------
    x : numpy.ndarray
        The x values of the data
    sigma_y : numpy.ndarray
        The uncertainty in the y values

    Returns
    -------
    float
        The uncertainty in the line fit
    """
    w = 1./sigma_y**2
    denom = np.sum(w)*np.sum(w*x**2)-np.sum(w*x)**2
    if denom <= 0:
        return np.nan
    else:
        result = np.sqrt(np.sum(w)/denom)
        return result


def delta_coords(ra, dec, mjds):
    """
    Compute the offsets in ra and dec caused by parallax only.

    Parameters
    ----------
    ra : float (degrees)
        RA of the object
    dec : float (degrees)
        Dec of the object
    mjds : array
        The Modified Julian Dates of the observations (days)

    Returns
    delta_ra : array
        The offsets in the RA direction (degrees)
    delta_dec : array
        The offsets in the dec direction (degrees)
    """
    star_fixed = SkyCoord(ra*u.deg, dec*u.deg, frame='icrs')
    # Using a star at 1 pc distance. This value cancels out, could use anything.
    star_near = SkyCoord(ra*u.deg, dec*u.deg, frame='icrs', distance=1.*u.pc)

    delta_ra = np.zeros(np.size(mjds), dtype=float)
    delta_dec = np.zeros(np.size(mjds), dtype=float)

    for i, mjd in enumerate(mjds):
        t = Time(mjd, format='mjd')
        star_near.obstime = t
        star_fixed.obstime = t
        fixed_gcrs = star_fixed.gcrs
        near_gcrs = star_near.gcrs
        x, y = gnomonic_project_toxy(near_gcrs.ra.to(u.rad), near_gcrs.dec.to(u.rad),
                                     fixed_gcrs.ra.to(u.rad), fixed_gcrs.dec.to(u.rad))
        delta_ra[i] = x
        delta_dec[i] = y
    return np.degrees(delta_ra), np.degrees(delta_dec)


def parallax_precision(ra_center, dec_center, ra_sigma, dec_sigma, mjds):
    """
    Return the final precision of a parallax fit. Assumes the position and proper motion
    are well fit and there is no covariance with the parallax fit.

    Parameters
    ----------
    ra_center : float
         The RA of the star (degrees).
    dec_center : float
         The Dec of the star (degrees).
    ra_sigma : float or array
         The uncertainty on each RA centroid (arcsec)
    dec_sigma : float of array
         The uncertainty on each Dec centroid (arcsec). Probably similar
         to ra_sigma.
    mjds : array
         The Modified Julian Dates of observations (days).

    Returns
    -------
    Uncertainty in the parallax amplitude in mas.
    """
    delta_ra, delta_dec = delta_coords(ra_center, dec_center, mjds)
    pi_ra_uncert = ra_sigma / (delta_ra * 3600.)
    pi_dec_uncert = dec_sigma / (delta_dec * 3600.)

    sigma_ra = np.sqrt(1./np.sum((1./(pi_ra_uncert**2))))
    sigma_dec = np.sqrt(1./np.sum((1./pi_dec_uncert**2)))
    final_sigma = np.sqrt(1./(1./sigma_ra**2+1./sigma_dec**2))

    return final_sigma * 1e3


def proper_motion_precision(mjds, centroid_error):
    """"
    Compute the uncertainty in the proper motion fit.

    Parameters
    ----------
    mjds : array
        The Modified Julian Dates of the observations (days)
    centroid_error : float of array
        The RMS uncertainty on each centroid (RA or Dec direction). (arcsec)

    Return
    ------
    Uncertainty on the fitted proper motion (mas/yr)
    """
    # If we are assuming one centroid error for all observations
    if np.size(centroid_error) == 1:
        centroid_errors = mjds*0. + centroid_error
    else:
        centroid_errors = centroid_error
    pm_uncert = sigma_slope(mjds, centroid_errors)

    return pm_uncert * 1e3 * 365.25

