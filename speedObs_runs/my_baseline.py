import numpy as np
import lsst.sims.featureScheduler as fs
from lsst.sims.speedObservatory import Speed_observatory
import matplotlib.pylab as plt
import healpy as hp

# Try making a simple baseline run
# Setup sims_feature_scheduler, and sims_ocs


# Get rid of the silly north stripe
def standard_goals(nside=None):
    """
    A quick function to generate the "standard" goal maps.
    """
    # Find the number of healpixels we expect to observe per observation
    if nside is None:
        nside = fs.set_default_nside()

    result = {}
    result['u'] = fs.generate_goal_map(nside=nside, NES_fraction=0.,
                                    WFD_fraction=0.31, SCP_fraction=0.15,
                                    GP_fraction=0.15, WFD_upper_edge_fraction=0.)
    result['g'] = fs.generate_goal_map(nside=nside, NES_fraction=0.2,
                                    WFD_fraction=0.44, SCP_fraction=0.15,
                                    GP_fraction=0.15, WFD_upper_edge_fraction=0.)
    result['r'] = fs.generate_goal_map(nside=nside, NES_fraction=0.46,
                                    WFD_fraction=1.0, SCP_fraction=0.15,
                                    GP_fraction=0.15, WFD_upper_edge_fraction=0.)
    result['i'] = fs.generate_goal_map(nside=nside, NES_fraction=0.46,
                                    WFD_fraction=1.0, SCP_fraction=0.15,
                                    GP_fraction=0.15, WFD_upper_edge_fraction=0.)
    result['z'] = fs.generate_goal_map(nside=nside, NES_fraction=0.4,
                                    WFD_fraction=0.9, SCP_fraction=0.15,
                                    GP_fraction=0.15, WFD_upper_edge_fraction=0.)
    result['y'] = fs.generate_goal_map(nside=nside, NES_fraction=0.,
                                       WFD_fraction=0.9, SCP_fraction=0.15,
                                       GP_fraction=0.15,
                                       WFD_upper_edge_fraction=0.)

    return result


if __name__ == '__main__':
    nside = fs.set_default_nside(nside=32)

    survey_length = 365.25 #365.25*10  # days

    # Define what we want the final visit ratio map to look like
    years = np.round(survey_length/365.25)
    # get rid of silly northern strip.
    target_map = standard_goals(nside=nside)

    filters = ['u', 'g', 'r', 'i', 'z', 'y']
    surveys = []

    for filtername in filters:
        bfs = []
        bfs.append(fs.M5_diff_basis_function(filtername=filtername, nside=nside))
        bfs.append(fs.Target_map_basis_function(filtername=filtername,
                                                target_map=target_map[filtername],
                                                out_of_bounds_val=hp.UNSEEN, nside=nside))

        bfs.append(fs.North_south_patch_basis_function(zenith_min_alt=50., nside=nside))
        #bfs.append(fs.Zenith_mask_basis_function(maxAlt=78., penalty=-100, nside=nside))
        bfs.append(fs.Slewtime_basis_function(filtername=filtername, nside=nside))
        bfs.append(fs.Strict_filter_basis_function(filtername=filtername))

        weights = np.array([3.0, 0.3, 1., 3., 3.])
        # Might want to try ignoring DD observations here, so the DD area gets covered normally--DONE
        surveys.append(fs.Greedy_survey_fields(bfs, weights, block_size=1, filtername=filtername,
                                               dither=True, nside=nside, ignore_obs='DD'))

    surveys.append(fs.Pairs_survey_scripted([], [], ignore_obs='DD', min_alt=20.))

    # Set up the DD
    dd_surveys = fs.generate_dd_surveys()
    surveys.extend(dd_surveys)

    scheduler = fs.Core_scheduler(surveys, nside=nside)
    observatory = Speed_observatory(nside=nside, mjd_start=59853.)
    observatory, scheduler, observations = fs.sim_runner(observatory, scheduler,
                                                         survey_length=survey_length,
                                                         filename='my_baseline_newSpeed%iyrs.db' % years,
                                                         delete_past=True)

# real    1751m55.325s = 29 hours