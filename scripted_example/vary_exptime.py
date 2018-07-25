import numpy as np
from lsst.sims.featureScheduler import (BaseSurveyFeature, set_default_nside, Base_basis_function,
                                        utils, features, Greedy_survey_fields)
import lsst.sims.featureScheduler as fs
import healpy as hp
from lsst.sims.utils import _hpid2RaDec, _raDec2Hpid, Site
from lsst.sims.featureScheduler import (empty_observation, set_default_nside, hp_in_lsst_fov, read_fields, stupidFast_altAz2RaDec,
                    raster_sort, stupidFast_RaDec2AltAz, gnomonic_project_toxy, haversine,
                    int_binned_stat, max_reject, tsp_convex, M5_diff_basis_function)
from lsst.sims.utils import (_hpid2RaDec, _raDec2Hpid, Site, _angularSeparation,
                             _altAzPaFromRaDec, _xyz_from_ra_dec, _healbin)
import copy


default_nside = None


def scale_exptime(m5diff, min_exptime, max_exptime, fiducial_time=30.):
    """
    Scale the exposure time given the conditions and desired exposure times

    Parameters
    ----------
    m5diff : float
        The 5-sigma limiting depth difference
    min_exptime : float
        Units should match max_exptime. Seconds are good.
    max_exptime : float
        The maximum exposure time to use.
    fiducial_time : float
        The exposure time assumed for the m5diff value.

    """
    new_times = min_exptime*10.**(-m5diff/1.25)
    new_times = np.clip(new_times, a_min=min_exptime, a_max=max_exptime)
    return new_times


class Vary_expt_survey(Greedy_survey_fields):
    """Select observations in large, blobs. Vary exposure times so depth is fairly uniform.
    """
    def __init__(self, basis_functions, basis_weights,
                 extra_features=None, extra_basis_functions=None,
                 filtername='r', filter2='g',
                 slew_approx=7.5, filter_change_approx=140.,
                 read_approx=2., nexp=2, min_exptime=15.,
                 max_exptime=60.,
                 ideal_pair_time=22., min_pair_time=15.,
                 search_radius=30., alt_max=85., az_range=90.,
                 smoothing_kernel=None, nside=default_nside,
                 dither=True, seed=42, ignore_obs='ack',
                 tag_fields=False, tag_map=None, tag_names=None,
                 sun_alt_limit=-19., survey_note='blob',
                 sitename='LSST'):
        """
        Parameters
        ----------
        min_exp_time : float (15.)
            The minimum exposure time to use (seconds). This is the exposure time when
            conditions are dark time on the meridian (or better).
        max_exp_time : float (60.)
            The maximum exposure time to use (seconds)
        filtername : str ('r')
            The filter to observe in.
        filter2 : str ('g')
            The filter to pair with the first observation. If set to None, no pair
            will be observed.
        slew_approx : float (7.5)
            The approximate slewtime between neerby fields (seconds). Used to calculate
            how many observations can be taken in the desired time block.
        filter_change_approx : float (140.)
             The approximate time it takes to change filters (seconds).
        ideal_pair_time : float (22.)
            The ideal time gap wanted between observations to the same pointing (minutes)
        min_pair_time : float (15.)
            The minimum acceptable pair time (minutes)
        search_radius : float (30.)
            The radius around the reward peak to look for additional potential pointings (degrees)
        alt_max : float (85.)
            The maximum altitude to include (degrees).
        az_range : float (90.)
            The range of azimuths to consider around the peak reward value (degrees).
        sitename : str ('LSST')
            The name of the site to lookup latitude and longitude.
        """

        if nside is None:
            nside = set_default_nside()

        if extra_features is None:
            extra_features = {}
            extra_features['night'] = features.Current_night()
            extra_features['mounted_filters'] = features.Mounted_filters()
            extra_features['mjd'] = features.Current_mjd()
            extra_features['night_boundaries'] = features.CurrentNightBoundaries()
            extra_features['sun_moon_alt'] = features.Sun_moon_alts()
            extra_features['lmst'] = features.Current_lmst()  # Pretty sure in hours
            extra_features['current_filter'] = features.Current_filter()
            extra_features['altaz'] = features.AltAzFeature()
        if extra_basis_functions is None:
            extra_basis_functions = {}
            extra_basis_functions['filter1_m5diff'] = M5_diff_basis_function(filtername=filtername,
                                                                             nside=nside)
            if filter2 is not None:
                extra_basis_functions['filter2_m5diff'] = M5_diff_basis_function(filtername=filter2,
                                                                                 nside=nside)

        super(Vary_expt_survey, self).__init__(basis_functions=basis_functions,
                                               basis_weights=basis_weights,
                                               extra_features=extra_features,
                                               extra_basis_functions=extra_basis_functions,
                                               filtername=filtername,
                                               block_size=0, smoothing_kernel=smoothing_kernel,
                                               dither=dither, seed=seed, ignore_obs=ignore_obs,
                                               tag_fields=tag_fields, tag_map=tag_map,
                                               tag_names=tag_names,
                                               nside=nside)
        self.nexp = nexp
        self.min_exptime = min_exptime
        self.max_exptime = max_exptime
        self.slew_approx = slew_approx
        self.read_approx = read_approx
        self.hpids = np.arange(hp.nside2npix(self.nside))
        # If we are taking pairs in same filter, no need to add filter change time.
        if filtername == filter2:
            filter_change_approx = 0
        # Compute the minimum time needed to observe a blob (or observe, then repeat.)
        if filter2 is not None:
            self.time_needed = (min_pair_time*60.*2. + read_approx + filter_change_approx)/24./3600.  # Days
        else:
            self.time_needed = (min_pair_time*60. + read_approx)/24./3600.  # Days
        self.filter_set = set(filtername)
        if filter2 is None:
            self.filter2_set = self.filter_set
        else:
            self.filter2_set = set(filter2)
        self.sun_alt_limit = np.radians(sun_alt_limit)

        self.ra, self.dec = _hpid2RaDec(self.nside, self.hpids)
        # Look up latitude and longitude for alt,az conversions later
        # XXX: TODO: lat and lon should be in the Observatory feature. But that feature
        # needs documentation on what's in it!
        site = Site(name=sitename)
        self.lat = site.latitude_rad
        self.lon = site.longitude_rad
        self.survey_note = survey_note
        self.counter = 1  # start at 1, because 0 is default in empty observation
        self.filter2 = filter2
        self.search_radius = np.radians(search_radius)
        self.az_range = np.radians(az_range)
        self.alt_max = np.radians(alt_max)
        self.min_pair_time = min_pair_time
        self.ideal_pair_time = ideal_pair_time

    def _set_block_time(self):
        """
        Update the block size if it's getting near the end of the night.
        """

        available_time = self.extra_features['night_boundaries'].feature['next_twilight_start'] -\
                         self.extra_features['mjd'].feature
        available_time *= 24.*60.  # to minutes

        n_ideal_blocks = available_time / self.ideal_pair_time
        if n_ideal_blocks >= 3:
            self.block_time = self.ideal_pair_time
        else:
            # Now we can stretch or contract the block size to allocate the remainder time until twilight starts
            # We can take the remaining time and try to do 1,2, or 3 blocks.
            possible_times = available_time / np.arange(1, 4)
            diff = np.abs(self.ideal_pair_time-possible_times)
            best_block_time = possible_times[np.where(diff == np.min(diff))]
            self.block_time = best_block_time

    def _check_feasability(self):
        # Check if filters are loaded
        filters_mounted = self.filter_set.issubset(set(self.extra_features['mounted_filters'].feature))
        if self.filter2 is not None:
            second_fitler_mounted = self.filter2_set.issubset(set(self.extra_features['mounted_filters'].feature))
            filters_mounted = filters_mounted & second_fitler_mounted

        available_time = self.extra_features['night_boundaries'].feature['next_twilight_start'] - self.extra_features['mjd'].feature
        if not filters_mounted:
            return False
        # Check we are not in twilight
        elif self.extra_features['sun_moon_alt'].feature['sunAlt'] > self.sun_alt_limit:
            return False
        # We have enough time before twilight starts
        elif available_time < self.time_needed:
            return False
        else:
            return True

    def calc_reward_function(self):
        """

        """
        # Figure out how much time we have for observing
        self._set_block_time()

        #  Computing reward like usual with basis functions and weights
        if self._check_feasability():
            self.reward = 0
            indx = np.arange(hp.nside2npix(self.nside))
            # keep track of masked pixels
            mask = np.zeros(indx.size, dtype=bool)
            for bf, weight in zip(self.basis_functions, self.basis_weights):
                basis_value = bf(indx=indx)
                mask[np.where(basis_value == hp.UNSEEN)] = True
                if hasattr(basis_value, 'mask'):
                    mask[np.where(basis_value.mask == True)] = True
                self.reward += basis_value*weight
                # might be faster to pull this out into the feasabiliity check?
                if hasattr(self.reward, 'mask'):
                    indx = np.where(self.reward.mask == False)[0]
            self.reward[mask] = hp.UNSEEN
            self.reward.mask = mask
            self.reward.fill_value = hp.UNSEEN

            if self.smoothing_kernel is not None:
                self.smooth_reward()

            # Apply max altitude cut
            too_high = np.where(self.extra_features['altaz'].feature['alt'] > self.alt_max)
            self.reward[too_high] = hp.UNSEEN

            # Select healpixels within some radius of the max
            # This is probably faster with a kd-tree.
            peak_reward = np.min(np.where(self.reward == np.max(self.reward))[0])
            # Apply radius selection
            dists = haversine(self.ra[peak_reward], self.dec[peak_reward], self.ra, self.dec)
            out_hp = np.where(dists > self.search_radius)
            self.reward[out_hp] = hp.UNSEEN

            # Apply az cut
            az_centered = self.extra_features['altaz'].feature['az'] - self.extra_features['altaz'].feature['az'][peak_reward]
            az_centered[np.where(az_centered < 0)] += 2.*np.pi

            az_out = np.where((az_centered > self.az_range/2.) & (az_centered < 2.*np.pi-self.az_range/2.))
            self.reward[az_out] = hp.UNSEEN
            potential_hp = np.where(self.reward.filled() != hp.UNSEEN)
            # Find the max reward for each potential pointing
            ufields, reward_by_field = int_binned_stat(self.hp2fields[potential_hp],
                                                       self.reward[potential_hp].filled(),
                                                       statistic=max_reject)
            ufields, m5_filter1_by_field = int_binned_stat(self.hp2fields[potential_hp],
                                                           self.extra_basis_functions['filter1_m5diff']()[potential_hp],
                                                           statistic=np.mean)
            order = np.argsort(reward_by_field)
            # Highest reward first
            ufields = ufields[order][::-1]
            m5_filter1_by_field = m5_filter1_by_field[order][::-1]
            # calculate the exposure times that we would want, given the m5 diff values
            exptime_f1 = scale_exptime(m5_filter1_by_field, self.min_exptime, self.max_exptime)
            overhead = np.zeros(exptime_f1.size) + self.slew_approx + self.read_approx*(self.nexp-1)
            elapsed_sec = np.cumsum(exptime_f1 + overhead)
            max_indx = np.max(np.where(elapsed_sec/60. <= self.block_time))
            self.exptimes_f1 = exptime_f1[0:max_indx+1]

            if self.filter2 is not None:
                # Now, we're assuming the 5-sigma depth doesn't change much over the pair period.
                # Obviously, if the moon rises or something, this is ont a good approx
                # Also, assuming the exptimes will scale similarly between filter1 and filter2.
                # If that is not the case, may miss target block time by a lot. 
                ufields, m5_filter2_by_field = int_binned_stat(self.hp2fields[potential_hp],
                                                               self.extra_basis_functions['filter2_m5diff']()[potential_hp],
                                                               statistic=np.mean)
                m5_filter2_by_field[order][::-1]
                exptime_f2 = scale_exptime(m5_filter2_by_field, self.min_exptime, self.max_exptime)
                self.exptimes_f2 = exptime_f2[0:max_indx+1]

            self.best_fields = ufields[0:max_indx+1]
        else:
            self.reward = -np.inf
        self.reward_checked = True
        return self.reward

    def __call__(self):
        """
        Find a good block of observations.
        """
        if not self.reward_checked:
            # This should set self.best_fields
            self.reward = self.calc_reward_function()

        # Let's find the alt, az coords of the points (right now, hopefully doesn't change much in time block)
        pointing_alt, pointing_az = stupidFast_RaDec2AltAz(self.fields['RA'][self.best_fields],
                                                           self.fields['dec'][self.best_fields],
                                                           self.lat, self.lon,
                                                           self.extra_features['mjd'].feature,
                                                           lmst=self.extra_features['lmst'].feature)
        # Let's find a good spot to project the points to a plane
        mid_alt = (np.max(pointing_alt) - np.min(pointing_alt))/2.

        # Code snippet from MAF for computing mean of angle accounting for wrap around
        # XXX-TODO: Maybe move this to sims_utils as a generally useful snippet.
        x = np.cos(pointing_az)
        y = np.sin(pointing_az)
        meanx = np.mean(x)
        meany = np.mean(y)
        angle = np.arctan2(meany, meanx)
        radius = np.sqrt(meanx**2 + meany**2)
        mid_az = angle % (2.*np.pi)
        if radius < 0.1:
            mid_az = np.pi

        # Project the alt,az coordinates to a plane. Could consider scaling things to represent
        # time between points rather than angular distance.
        pointing_x, pointing_y = gnomonic_project_toxy(pointing_az, pointing_alt, mid_az, mid_alt)
        # Now I have a bunch of x,y pointings. Drop into TSP solver to get an effiencent route
        towns = np.vstack((pointing_x, pointing_y)).T
        # Leaving optimize=False for speed. The optimization step doesn't usually improve much.
        better_order = tsp_convex(towns, optimize=False)
        # XXX-TODO: Could try to roll better_order to start at the nearest/fastest slew from current position.
        observations = []
        counter2 = 0
        for indx in better_order:
            field = self.best_fields[indx]
            if self.tag_fields:
                tag = np.unique(self.tag_map[np.where(self.hp2fields == field)])[0]
            else:
                tag = 1
            if tag == 0:
                continue
            obs = empty_observation()
            obs['RA'] = self.fields['RA'][field]
            obs['dec'] = self.fields['dec'][field]
            obs['rotSkyPos'] = 0.
            obs['filter'] = self.filtername
            obs['nexp'] = self.nexp
            obs['exptime'] = self.exptimes_f1[indx]
            obs['field_id'] = -1
            if self.tag_fields:
                obs['survey_id'] = np.unique(self.tag_map[np.where(self.hp2fields == field)])[0]
            else:
                obs['survey_id'] = 1
            obs['note'] = '%s' % (self.survey_note)
            obs['block_id'] = self.counter
            obs['note'] = '%s, a' % (self.survey_note)
            observations.append(obs)
            counter2 += 1

        # If we only want one filter block
        if self.filter2 is None:
            result = observations
        else:
            # Double the list to get a pair.
            observations_paired = []
            for i, observation in enumerate(observations):
                obs = copy.copy(observation)
                obs['filter'] = self.filter2
                obs['exptime'] = self.exptimes_f2[better_order[i]]
                obs['note'] = '%s, b' % (self.survey_note)
                observations_paired.append(obs)

            # Check loaded filter here to decide which goes first
            if self.extra_features['current_filter'].feature == self.filter2:
                result = observations_paired + observations
            else:
                result = observations + observations_paired

        # Keep track of which block we're on. Nice for debugging.
        self.counter += 1
        return result
