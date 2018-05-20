import lsst.sims.maf.batches as batches
import lsst.sims.maf.db as db
from lsst.sims.maf.metricBundles import MetricBundleGroup
import numpy as np
import lsst.sims.maf.metrics as metrics
import lsst.sims.maf.slicers as slicers
import lsst.sims.maf.plots as plots
import lsst.sims.maf.metricBundles as mb
from lsst.sims.maf.batches.colMapDict import ColMapDict
from lsst.sims.maf.batches.common import standardSummary, filterList

# Ugh, need more intelligent color ranges
def interNight(colmap=None, runName='opsim', nside=64, extraSql=None, extraMetadata=None):
    """Generate a set of statistics about the spacing between nights with observations.

    Parameters
    ----------
    colmap : dict or None, opt
        A dictionary with a mapping of column names. Default will use OpsimV4 column names.
    runName : str, opt
        The name of the simulated survey. Default is "opsim".
    nside : int, opt
        Nside for the healpix slicer. Default 64.
    extraSql : str or None, opt
        Additional sql constraint to apply to all metrics.
    extraMetadata : str or None, opt
        Additional metadata to use for all outputs.

    Returns
    -------
    metricBundleDict
    """

    if colmap is None:
        colmap = ColMapDict('opsimV4')

    bundleList = []

    # Set up basic all and per filter sql constraints.
    filterlist, colors, orders, sqls, metadata = filterList(all=True,
                                                            extraSql=extraSql,
                                                            extraMetadata=extraMetadata)

    displayDict = {'group': 'InterNight', 'subgroup': 'Night gaps', 'caption': None, 'order': 0}
    bins = np.arange(1, 20.5, 1)
    metric = metrics.NightgapsMetric(bins=bins, nightCol=colmap['night'], metricName='DeltaNight Histogram')
    slicer = slicers.HealpixSlicer(nside=nside, latCol=colmap['dec'], lonCol=colmap['ra'],
                                   latLonDeg=colmap['raDecDeg'])
    plotDict = {'bins': bins, 'xlabel': 'dT (nights)'}
    displayDict['caption'] = 'Histogram of the number of nights between consecutive visits to a ' \
                             'given point on the sky, considering separations between %d and %d.' \
                             % (bins.min(), bins.max())
    plotFunc = plots.SummaryHistogram()
    bundle = mb.MetricBundle(metric, slicer, sqls['all'], plotDict=plotDict,
                             displayDict=displayDict, metadata=metadata['all'], plotFuncs=[plotFunc])
    bundleList.append(bundle)

    standardStats = standardSummary()
    subsetPlots = [plots.HealpixSkyMap(), plots.HealpixHistogram()]

    # Median inter-night gap (each and all filters)
    metric = metrics.InterNightGapsMetric(metricName='Median Inter-Night Gap', mjdCol=colmap['mjd'],
                                          reduceFunc=np.median)
    slicer = slicers.HealpixSlicer(nside=nside, latCol=colmap['dec'], lonCol=colmap['ra'],
                                   latLonDeg=colmap['raDecDeg'])
    for f in filterlist:
        if f == 'all':
            colormax = 10.
        else:
            colormax = 60
        displayDict['caption'] = 'Median gap between nights with observations, %s.' % metadata[f]
        displayDict['order'] = orders[f]
        plotDict = {'color': colors[f], 'colorMin': 0, 'colorMax':colormax}
        bundle = mb.MetricBundle(metric, slicer, sqls[f], metadata=metadata[f],
                                 displayDict=displayDict,
                                 plotFuncs=subsetPlots, plotDict=plotDict,
                                 summaryMetrics=standardStats)
        bundleList.append(bundle)

    # Maximum inter-night gap (in each and all filters).
    metric = metrics.InterNightGapsMetric(metricName='Max Inter-Night Gap', mjdCol=colmap['mjd'],
                                          reduceFunc=np.max)
    slicer = slicers.HealpixSlicer(nside=nside, latCol=colmap['dec'], lonCol=colmap['ra'],
                                   latLonDeg=colmap['raDecDeg'])
    for f in filterlist:
        displayDict['caption'] = 'Maximum gap between nights with observations, %s.' % metadata[f]
        displayDict['order'] = orders[f]
        plotDict = {'color': colors[f], 'percentileClip': 95., 'binsize': 5}
        bundle = mb.MetricBundle(metric, slicer, sqls[f], metadata=metadata[f], displayDict=displayDict,
                                 plotFuncs=subsetPlots, plotDict=plotDict, summaryMetrics=standardStats)
        bundleList.append(bundle)

    # Set the runName for all bundles and return the bundleDict.
    for b in bundleList:
        b.setRunName(runName)
    return mb.makeBundlesDictFromList(bundleList)




colmap = batches.ColMapDict('barebones')
colmap['ra'] = 'RA'
colmap['seeingEff'] = 'FWHMeff'
colmap['seeingGeom'] = 'FWHM_geometric'
colmap['note'] = 'note'
bd = batches.glanceBatch(colmap=colmap)

cadence_batch = interNight(colmap=colmap)


def run_glance(outDir, dbname):

    conn = db.Database(dbname, defaultTable='observations')
    resultsDb = db.ResultsDb(outDir=outDir)
    mbg = MetricBundleGroup(bd, conn, outDir=outDir, resultsDb=resultsDb)
    mbg.runAll()
    mbg.plotAll()
    conn.close()


def run_cadence(outDir, dbname):
    conn = db.Database(dbname, defaultTable='observations')
    resultsDb = db.ResultsDb(outDir=outDir)
    mbg = MetricBundleGroup(cadence_batch, conn, outDir=outDir, resultsDb=resultsDb)
    mbg.runAll()
    mbg.plotAll()
    conn.close()


if __name__ == '__main__':
    #run_glance('baseline_0', 'my_baseline__0yrs.db')
    run_glance('repo_0', 'from_repo__0yrs.db')




