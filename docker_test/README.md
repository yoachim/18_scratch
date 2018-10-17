
Notes on how to run with docker:

update the container:
docker pull oboberg/opsim4_fbs_py3:latest

# enter the container
./docker_thingy

# Start up database
manage_db --save-dir=/home/opsim/run_local/output/

# set to my config:
declare and setup my scheduler_config repo.

# Run for a day:
opsim4 --frac-duration=0.003
