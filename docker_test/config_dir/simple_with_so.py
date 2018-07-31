from lsst.sims.speedObservatory import Speed_observatory
import lsst.sims.featureScheduler as fs
import numpy as np
from blob_same_zmask import generate_slair_scheduler
import time

t0 = time.time()

survey_length = 1.
years = np.round(survey_length/365.25)
nside = fs.set_default_nside(nside=32)
scheduler = generate_slair_scheduler()

observatory = Speed_observatory(nside=nside, quickTest=True)
observatory, scheduler, observations = fs.sim_runner(observatory, scheduler,
                                                     survey_length=survey_length,
                                                     filename='blobs_same_zmask%iyrs.db' % years,
                                                     delete_past=True)


trun = time.time() - t0
print('ran in %i, %i minutes=%i hours' % (trun, trun/60., trun/3600.))
