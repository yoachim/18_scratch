
A quick hack to try and compare a survey with and without the NES

Using the neos orbits from sims_movingObjects (neos_100.s3m), using the baseline2018a.db OpSim simulation.

`makeLSSTobs.py --orbitFile neos_100.s3m --opsimDb baseline2018a.db --sqlConstraint '' --outDir full`
`makeLSSTobs.py --orbitFile neos_100.s3m --opsimDb baseline2018a.db --sqlConstraint 'fieldDec < 0' --outDir noNES`



Using my branch of MAF, should be merged to master soon-ish


in each new directory:

`movingObjects.py --obsFile baseline2018a__neos_100_obs.txt --opsimRun noNES --orbitFile ../neos_100.s3m`

`movingObjects.py --obsFile baseline2018a__neos_100_obs.txt --opsimRun baseline2018a --orbitFile ../neos_100.s3m`


