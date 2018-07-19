from lsst.sims.featureScheduler import BaseSurvey, set_default_nside, features, empty_observation
from lsst.sims.utils import (_hpid2RaDec, _raDec2Hpid, Site, _angularSeparation,
                             _altAzPaFromRaDec, _xyz_from_ra_dec, _healbin)
import numpy as np
default_nside = None


class Scripted_survey(BaseSurvey):
    """
    Take a set of scheduled observations and serve them up.
    """
    def __init__(self, mjd_target, mjd_tol, extra_features=None,
                 smoothing_kernel=None, reward=1e6, ignore_obs='dummy',
                 nside=default_nside):
        """
        Parameters
        ----------
        mjd_target : float
            The MJD that the script should be executed at (days). It is up to the
            user to make sure the target is visible at that time.
        mjd_tol : float
            The tolerance on the MJD (minutes).
        reward : float (1e6)
            The reward to report if the current MJD is within mjd_tol of mjd_target. 
        """
        if nside is None:
            nside = set_default_nside()

        self.mjd_target = mjd_target
        self.mjd_tol = mjd_tol/60./24.

        self.nside = nside
        self.reward_val = reward
        self.reward = -reward
        if extra_features is None:
            extra_features = {'mjd': features.Current_mjd()}
            extra_features['altaz'] = features.AltAzFeature(nside=nside)
        super(Scripted_survey, self).__init__(basis_functions=[],
                                              basis_weights=[],
                                              extra_features=extra_features,
                                              smoothing_kernel=smoothing_kernel,
                                              ignore_obs=ignore_obs,
                                              nside=nside)

    def add_observation(self, observation, indx=None, **kwargs):
        """Check if this matches a scripted observation
        """
        # XXX--TODO: remove observation from list if it got executed
        pass

    def calc_reward_function(self):
        """If there is an observation ready to go, execute it, otherwise, -inf
        """
        dt = self.mjd_target - self.extra_features['mjd'].feature
        if (np.abs(dt) > self.mjd_tol) | (len(self.obs_wanted) == 0):
            self.reward = -np.inf
        else:
            self.reward = self.reward_val
        return self.reward

    def _slice2obs(self, obs_row):
        """take a slice and return a full observation object
        """
        observation = empty_observation()
        for key in ['RA', 'dec', 'filter', 'exptime', 'nexp', 'note', 'field_id']:
            observation[key] = obs_row[key]
        return observation

    def set_script(self, obs_wanted):
        """
        Parameters
        ----------
        obs_wanted : np.array
            The observations that should be executed. Needs to have columns with dtype names:
            'RA', 'dec', 'filter', 'exptime', 'nexp', 'note', 'field_id'
        mjds : np.array
            The MJDs for the observaitons, should be same length as obs_list
        mjd_tol : float (15.)
            The tolerance to consider an observation as still good to observe (min)
        """
        self.obs_wanted = [self._slice2obs(obs) for obs in obs_wanted]
        # Set something to record when things have been observed
        self.obs_log = np.zeros(obs_wanted.size, dtype=bool)

    def __call__(self):
        if self.calc_reward_function() == self.reward:
            return self.obs_wanted
        else:
            return [None]
