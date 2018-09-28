
Notes on how to run with docker:

update the container:
docker pull oboberg/opsim4_fbs_py3:latest

My 1-year run got killed when I gave it only 16GB of memory. Let's try it again with 24.

# Start up database
manage_db --save-dir=/home/opsim/run_local/output/

# set to my config:


# Run:
opsim4 --frac-duration=1.0