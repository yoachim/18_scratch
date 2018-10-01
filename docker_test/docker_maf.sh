#!/bin/bash
docker run -it --rm -v  $HOME/gitRepos/sims_maf:/home/docmaf/maf_local \
                    -v  $HOME/gitRepos:/home/docmaf/my_repos \
                    -p 8080:8080 \
                     oboberg/maf:latest
