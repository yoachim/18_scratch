import numpy as np
import lsst.sims.featureScheduler as fs
from lsst.sims.speedObservatory import Speed_observatory
import matplotlib.pylab as plt
import healpy as hp
import time

t0 = time.time()

survey_length = 5.5 #365.25*10 # days
nside = fs.set_default_nside(nside=32)
# Define what we want the final visit ratio map to look like
years = np.round(survey_length/365.25)
# get rid of silly northern strip.
target_map = fs.standard_goals(nside=nside)
norm_factor = fs.calc_norm_factor(target_map)
# List to hold all the surveys (for easy plotting later)
surveys = []

# Let's set up a scripted observation that will just interupt whenever

ssurvey = fs.Scripted_survey()
for_type = fs.empty_observation()
scripted_obs = np.zeros(20, dtype=for_type.dtype)
mjd0 = 59583.060669
scripted_obs['filter'] = 'r'
# Take a strip of declination at constant RA.
scripted_obs['RA'] = np.radians(53.)  # radians
scripted_obs['dec'] = np.radians(-np.arange(20)*2. - 20.)
# Assume about 37 seconds per visit
scripted_obs['mjd'] = np.arange(20)*37. + mjd0
scripted_obs['exptime'] = 30.
scripted_obs['nexp'] = 2
# Add a note so it's easy to see if they fire
scripted_obs['note'] = 'scripted_tier1'

ssurvey.set_script(scripted_obs)

scripted_surveys = [ssurvey]


# Set up observations to be taken in blocks
filter1s = ['u', 'g', 'r', 'i', 'z', 'y']
filter2s = [None, 'r', 'i', 'g', None, None]
pair_surveys = []
for filtername, filtername2 in zip(filter1s, filter2s):
    bfs = []
    bfs.append(fs.M5_diff_basis_function(filtername=filtername, nside=nside))
    if filtername2 is not None:
        bfs.append(fs.M5_diff_basis_function(filtername=filtername2, nside=nside))
    bfs.append(fs.Target_map_basis_function(filtername=filtername,
                                            target_map=target_map[filtername],
                                            out_of_bounds_val=hp.UNSEEN, nside=nside))
    if filtername2 is not None:
        bfs.append(fs.Target_map_basis_function(filtername=filtername2,
                                                target_map=target_map[filtername2],
                                                out_of_bounds_val=hp.UNSEEN, nside=nside))
    bfs.append(fs.Slewtime_basis_function(filtername=filtername, nside=nside))
    bfs.append(fs.Zenith_shadow_mask_basis_function(nside=nside, shadow_minutes=90.))
    weights = np.array([3.0, 3.0, .3, .3, 3., 0])
    if filtername2 is None:
        # Need to scale weights up so filter balancing still works.
        weights = np.array([6.0, 0.6, 3., 0])
    # XXX-
    # This is where we could add a look-ahead basis function to include m5_diff in the future.
    # Actually, having a near-future m5 would also help prevent switching to u or g right at twilight?
    # Maybe just need a "filter future" basis function?
    if filtername2 is None:
        survey_name = 'blob, %s' % filtername
    else:
        survey_name = 'blob, %s%s' % (filtername, filtername2)
    surveys.append(fs.Blob_survey(bfs, weights, filtername=filtername, filter2=filtername2,
                                  survey_note=survey_name))
    pair_surveys.append(surveys[-1])


# Let's set up some standard surveys as well to fill in the gaps. This is my old silly masked version.
# It would be good to put in Tiago's verion and lift nearly all the masking. That way this can also
# chase sucker holes.
#filters = ['u', 'g', 'r', 'i', 'z', 'y']
filters = ['i', 'z', 'y']

greedy_surveys = []
for filtername in filters:
    bfs = []
    bfs.append(fs.M5_diff_basis_function(filtername=filtername, nside=nside))
    bfs.append(fs.Target_map_basis_function(filtername=filtername,
                                            target_map=target_map[filtername],
                                            out_of_bounds_val=hp.UNSEEN, nside=nside))

    bfs.append(fs.North_south_patch_basis_function(zenith_min_alt=50., nside=nside))
    bfs.append(fs.Slewtime_basis_function(filtername=filtername, nside=nside))
    bfs.append(fs.Strict_filter_basis_function(filtername=filtername))

    weights = np.array([3.0, 0.3, 1., 3., 3.])
    # Might want to try ignoring DD observations here, so the DD area gets covered normally--DONE
    surveys.append(fs.Greedy_survey_fields(bfs, weights, block_size=1, filtername=filtername,
                                           dither=True, nside=nside, ignore_obs='DD'))
    greedy_surveys.append(surveys[-1])

# Set up the DD surveys
dd_surveys = fs.generate_dd_surveys()
surveys.extend(dd_surveys)

survey_list_o_lists = [scripted_surveys, dd_surveys, pair_surveys, greedy_surveys]

# Debug to stop at a spot if needed
n_visit_limit = None

# put in as list-of-lists so pairs get evaluated first.
scheduler = fs.Core_scheduler(survey_list_o_lists, nside=nside)
observatory = Speed_observatory(nside=nside, quickTest=True)
observatory, scheduler, observations = fs.sim_runner(observatory, scheduler,
                                                     survey_length=survey_length,
                                                     filename='blobs_mix_script_%iyrs.db' % years,
                                                     delete_past=True, n_visit_limit=n_visit_limit)
t1 = time.time()
delta_t = t1-t0
print('ran in %.1f min = %.1f hours' % (delta_t/60., delta_t/3600.))

