import logging
import healpy as hp

from lsst.sims.ocs.database import SocsDatabase
from lsst.sims.ocs.kernel import Simulator
from lsst.sims.featureScheduler.driver import FeatureSchedulerDriver as Driver
from lsst.sims.ocs.setup import create_parser
from lsst.sims.ocs.setup import apply_file_config, read_file_config
from lsst.ts.scheduler.kernel import SurveyTopology

from blob_same_zmask import generate_slair_scheduler
import time

t0 = time.time()

# Let's try to launch this as a simple script since it died in jupyter
logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')

parser = create_parser()
args = parser.parse_known_args()[0]
prog_conf = read_file_config()
if prog_conf is not None:
    apply_file_config(prog_conf, args)
print(args.sqlite_save_dir, args.session_id_start, args.sqlite_session_save_dir)

db = SocsDatabase(sqlite_save_path=args.sqlite_save_dir,
                  session_id_start=args.session_id_start,
                  sqlite_session_save_path=args.sqlite_session_save_dir)

session_id = db.new_session("FBS test on notebook")

driver = Driver()
args.frac_duration = 0.003

sim = Simulator(args, db, driver=driver)

scheduler = generate_slair_scheduler()

sim.driver.scheduler = scheduler
sim.driver.sky_nside = scheduler.nside

# WTF is this crap?
survey_topology = SurveyTopology()
survey_topology.num_general_props = 1
survey_topology.general_propos = ["FuckProps"]
survey_topology.num_seq_props = 1
survey_topology.sequence_propos = ["ReallyFuckThis"]
sim.conf_comm.num_proposals = survey_topology.num_props
sim.conf_comm.survey_topology['general'] = survey_topology.general_propos
sim.conf_comm.survey_topology['sequence'] = survey_topology.sequence_propos

sim.initialize()
sim.run()
trun = time.time() - t0
print('ran in %i minutes=%i hours' % (trun/60., trun/3600.))
