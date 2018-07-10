import numpy as np
import urllib.request
import json


def gemini_log_json(utc_str):
    """
    grab the json file
    """
    url = 'https://archive.gemini.edu/jsonsummary/notengineering/%s/science/NotFail/present/canonical' % utc_str
    response = urllib.request.urlopen(url)
    json_contents = response.read()
    entry_list = json.loads(json_contents)
    return entry_list


def log_stats(entry_list):
    """
    Cut down to just Gemini South, calc some stats
    """
    exp_times = [entry['exposure_time'] for entry in entry_list if entry['telescope'] == 'Gemini-South']
    if len(exp_times) == 0:
        return 0
    else:
        return np.nansum(np.array(exp_times, dtype=float))

if __name__ == '__main__':

    year = '2014'
    exposure_time_in_night = []
    utc_strs = []
    days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    #days = [2]
    out_file = open('%s_exp.csv' % year, 'w')
    for i, ndays in enumerate(days):
        for day in range(1, ndays+1):
            utc_str = '%s%02d%02d' % (year, i+1, day)
            entry_list = gemini_log_json(utc_str)
            utc_strs.append(utc_str)
            total_seconds = log_stats(entry_list)
            exposure_time_in_night.append(total_seconds)
            print('%s%02d%02d, %f' % (year, i+1, day, total_seconds))
            out_file.write('%s%02d%02d, %f\n' % (year, i+1, day, total_seconds))

    exp_times = np.array(exposure_time_in_night)
    np.savez('%s_exp' % year, exp_times=exp_times, utc_strs=utc_strs)
