#!/bin/bash
run_dir=/Users/yoachim/gitRepos/18_scratch/docker_test/run_dir
config_dir=/Users/yoachim/gitRepos/18_scratch/docker_test/config_dir
sky_brightness_data_dir=$HOME/gitRepos/sims_skybrightness_pre/data
host_ip="$(dig +short myip.opendns.com @resolver1.opendns.com)"

docker run -it --rm --name "$1" \
          -v ${run_dir}:/home/opsim/run_local \
          -v ${config_dir}:/home/opsim/other-configs \
          -v $HOME/.config:/home/opsim/.config \
          -v ${sky_brightness_data_dir}:/home/opsim/repos/sims_skybrightness_pre/data \
          -e OPSIM_HOSTNAME=${host_name} \
          -e DISPLAY=${host_ip}:0 \
          -p 8888:8888 \
          oboberg/opsim4_fbs_py3:latest

