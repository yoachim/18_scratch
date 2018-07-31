import numpy as np
import lsst.sims.featureScheduler as fs
import healpy as hp


def generate_slair_scheduler():
    nside = fs.set_default_nside(nside=32)
    # get rid of silly northern strip.
    target_map = fs.standard_goals(nside=nside)
    norm_factor = fs.calc_norm_factor(target_map)
    # List to hold all the surveys (for easy plotting later)
    surveys = []

    # Set up observations to be taken in blocks
    filter1s = ['u', 'g', 'r', 'i', 'z', 'y']
    filter2s = [None, 'g', 'r', 'i', None, None]
    pair_surveys = []
    for filtername, filtername2 in zip(filter1s, filter2s):
        bfs = []
        bfs.append(fs.M5_diff_basis_function(filtername=filtername, nside=nside))
        if filtername2 is not None:
            bfs.append(fs.M5_diff_basis_function(filtername=filtername2, nside=nside))
        bfs.append(fs.Target_map_basis_function(filtername=filtername,
                                                target_map=target_map[filtername],
                                                out_of_bounds_val=hp.UNSEEN, nside=nside,
                                                norm_factor=norm_factor))
        if filtername2 is not None:
            bfs.append(fs.Target_map_basis_function(filtername=filtername2,
                                                    target_map=target_map[filtername2],
                                                    out_of_bounds_val=hp.UNSEEN, nside=nside,
                                                    norm_factor=norm_factor))
        bfs.append(fs.Slewtime_basis_function(filtername=filtername, nside=nside))
        bfs.append(fs.Strict_filter_basis_function(filtername=filtername))
        bfs.append(fs.Zenith_shadow_mask_basis_function(nside=nside, shadow_minutes=60., max_alt=76.))
        weights = np.array([3.0, 3.0, .3, .3, 3., 3., 0.])
        if filtername2 is None:
            # Need to scale weights up so filter balancing still works properly.
            weights = np.array([6.0, 0.6, 3., 3., 0.])
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
    filters = ['u', 'g', 'r', 'i', 'z', 'y']
    #filters = ['i', 'z', 'y']
    greedy_surveys = []
    for filtername in filters:
        bfs = []
        bfs.append(fs.M5_diff_basis_function(filtername=filtername, nside=nside))
        bfs.append(fs.Target_map_basis_function(filtername=filtername,
                                                target_map=target_map[filtername],
                                                out_of_bounds_val=hp.UNSEEN, nside=nside,
                                                norm_factor=norm_factor))

        bfs.append(fs.North_south_patch_basis_function(zenith_min_alt=50., nside=nside))
        bfs.append(fs.Slewtime_basis_function(filtername=filtername, nside=nside))
        bfs.append(fs.Strict_filter_basis_function(filtername=filtername))
        bfs.append(fs.Zenith_shadow_mask_basis_function(nside=nside, shadow_minutes=60., max_alt=76.))
        weights = np.array([3.0, 0.3, 1., 3., 3., 0.])
        # Might want to try ignoring DD observations here, so the DD area gets covered normally--DONE
        surveys.append(fs.Greedy_survey_fields(bfs, weights, block_size=1, filtername=filtername,
                                               dither=True, nside=nside, ignore_obs='DD'))
        greedy_surveys.append(surveys[-1])

    # Set up the DD surveys
    dd_surveys = fs.generate_dd_surveys()
    surveys.extend(dd_surveys)

    survey_list_o_lists = [dd_surveys, pair_surveys, greedy_surveys]

    # put in as list-of-lists so pairs get evaluated first.
    scheduler = fs.Core_scheduler(survey_list_o_lists, nside=nside)
    return scheduler
