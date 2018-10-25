
A quick hack to try and compare a survey with and without the NES

Using the neos orbits from sims_movingObjects (neos_100.s3m), using the baseline2018a.db OpSim simulation.

`makeLSSTobs.py --orbitFile neos_100.s3m --opsimDb baseline2018a.db --sqlConstraint '' --outDir full`
`makeLSSTobs.py --orbitFile neos_100.s3m --opsimDb baseline2018a.db --sqlConstraint 'fieldDec < 0' --outDir noNES`



Using my branch of MAF, should be merged to master soon-ish




movingObjects.py --obsFile baseline2018a_neos_100_full_obs.txt --opsimRun baseline2018a --outDir full --orbitFile neos_100.s3m



