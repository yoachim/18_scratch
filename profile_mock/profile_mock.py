import numpy as np
import cProfile
from lsst.sims.featureScheduler.mockTelem import Mock_observatory
from lsst.sims.featureScheduler.schedulers import Core_scheduler
from lsst.sims.featureScheduler.utils import sim_runner, standard_goals, calc_norm_factor
import lsst.sims.featureScheduler.basis_functions as bf
from lsst.sims.featureScheduler.surveys import (generate_dd_surveys, Greedy_survey,
                                                Blob_survey, Pairs_survey_scripted)

# Need to profile the mock telemetry to see what is making things run so slow
# python -m cProfile -o mock_prof_results profile_mock.py


def gen_greedy_surveys(nside):
    """
    Make a quick set of greedy surveys
    """
    target_map = standard_goals(nside=nside)
    filters = ['g', 'r', 'i', 'z', 'y']
    surveys = []
    cloud_map = target_map['r'][0]*0 + 0.7

    for filtername in filters:
        bfs = []
        bfs.append(bf.M5_diff_basis_function(filtername=filtername, nside=nside))
        bfs.append(bf.Target_map_basis_function(filtername=filtername,
                                                target_map=target_map[filtername],
                                                out_of_bounds_val=np.nan, nside=nside))
        bfs.append(bf.Slewtime_basis_function(filtername=filtername, nside=nside))
        bfs.append(bf.Strict_filter_basis_function(filtername=filtername))
        # Masks, give these 0 weight
        bfs.append(bf.Zenith_shadow_mask_basis_function(nside=nside, shadow_minutes=60., max_alt=76.))
        bfs.append(bf.Moon_avoidance_basis_function(nside=nside, moon_distance=40.))
        bfs.append(bf.Bulk_cloud_basis_function(max_cloud_map=cloud_map, nside=nside))

        bfs.append(bf.Filter_loaded_basis_function(filternames=filtername))

        weights = np.array([3.0, 0.3, 3., 3., 0., 0., 0., 0.])
        surveys.append(Greedy_survey(bfs, weights, block_size=1, filtername=filtername,
                                     dither=True, nside=nside))
    return surveys


def run_simple_sim():
    nside = 32
    survey_length = 2.1  # days

    surveys = gen_greedy_surveys(nside)
    surveys.append(Pairs_survey_scripted(None, ignore_obs='DD'))

    # Set up the DD
    dd_surveys = generate_dd_surveys(nside=nside)
    surveys.extend(dd_surveys)

    scheduler = Core_scheduler(surveys, nside=nside)
    observatory = Mock_observatory(nside=nside)
    observatory, scheduler, observations = sim_runner(observatory, scheduler,
                                                      survey_length=survey_length,
                                                      filename=None)

if __name__ == '__main__':
    run_simple_sim()
