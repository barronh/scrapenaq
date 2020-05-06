#!/usr/bin/env python
import os
import PseudoNetCDF as pnc
import json
from glob import glob
import numpy as np
from datetime import datetime
from warnings import warn
from scipy.stats import binned_statistic_dd
import pandas as pd
from collections import OrderedDict
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-g', '--griddesc', default='GRIDDESC')
parser.add_argument('-v', '--verbose', default=0, action='count')
parser.add_argument(
    '--no-csv', dest='csv', default=True, action='store_false'
)
parser.add_argument(
    '--no-netcdf', dest='netcdf', default=True, action='store_false'
)
parser.add_argument('parameter')
parser.add_argument('startdate')
parser.add_argument('enddate')
parser.add_argument('GDNAM', default='12US1')

args = parser.parse_args()

outputdates = pd.date_range(args.startdate, args.enddate)
GDNAM = args.GDNAM
verbose = args.verbose
param = args.parameter

missing = [-999]
ugm3s = (b'<C2><B5>m<C3><B4>', b'\xc2\xb5g/m\xc2\xb3')
gf = pnc.pncopen('GRIDDESC', format='griddesc', GDNAM=GDNAM)
gf.SDATE = int(outputdates[0].strftime('%Y%j'))
gf.TSTEP = 10000
del gf.variables['TFLAG']
gf.updatemeta()
outf = gf.renameVariables(DUMMY='O3').slice(TSTEP=np.zeros(24, dtype='i'))
ovar = outf.variables['O3']
nvar = outf.copyVariable(ovar, key='O3N')


outtmpl = '{0}/{1}/OPENAQ.{1}.{2}.{3}.{0}'.format
for outdate in outputdates:
    ncfpath = outtmpl('nc', GDNAM, outdate.strftime('%F'), param)
    csvpath = outtmpl('csv', GDNAM, outdate.strftime('%F'), param)
    csvdir = os.path.dirname(csvpath)
    ncfdir = os.path.dirname(ncfpath)
    ncfexists = os.path.exists(ncfpath)
    csvexists = os.path.exists(csvpath)
    if args.netcdf and ncfexists:
        print('Keeping cached', ncfpath)
    else:
        os.makedirs(ncfdir, exist_ok=True)
    if args.csv and csvexists:
        print('Keeping cached', csvpath)
    else:
        os.makedirs(csvdir, exist_ok=True)
    makecsv = (args.csv and not csvexists)
    makencf = (args.netcdf and not ncfexists)
    if not makecsv and not makencf:
        continue

    paths = sorted(glob(
        outdate.strftime(param + '/????/????-??-??/%F.ndjson')
    ))
    rdate = outdate
    outf.SDATE = int(rdate.strftime('%Y%j'))
    outf.TSTEP = 10000
    del outf.variables['TFLAG']
    outf.updatemeta()
    ovar[:] = 0
    nvar[:] = 0
    lines = []
    for path in paths:
        print()
        print(path, flush=True, end='')
        datstr = open(path, encoding='latin1').read()
        if len(datstr) == 0:
            continue
        lines.extend(datstr.strip().split('\n'))

    lats = []
    lons = []
    vals = []
    rvals = []
    dates = []
    for li, line in enumerate(lines):
        data = json.loads(line)
        coord = data.get('coordinates', None)
        if coord is None:
            warn('Skipping values with empty coordinates')
            continue
        ap = data.get("averagingPeriod", {'value': 0, 'unit': 'unknown'})
        if ap['value'] != 1 or ap['unit'].strip().lower() != 'hours':
            warn('Skipping values with non 1-hour averaging periods')

        lat = coord['latitude']
        lon = coord['longitude']
        if verbose > 1:
            print(li, end='.', flush=True)
        date = datetime.strptime(
            data['date']['utc'] + '+0000', '%Y-%m-%dT%H:%M:%S.%fZ%z'
        )
        rval = val = data['value']
        if val < -100:
            warn('Skipping negative values: {}'.format(val))
            continue
        unit = data['unit'].strip()
        if unit.encode('latin1') in ugm3s:
            val *= (293.15 * 8.314 / 101325. / 0.048)
            unit = 'ppb'
        elif unit in ('ppm'):
            val *= 1000
            unit = 'ppb'
        if unit != 'ppb':
            print(unit)
        dates.append(date)
        vals.append(val)
        rvals.append(rval)
        lons.append(lon)
        lats.append(lat)

    i, j = outf.ll2ij(lons, lats)
    tidx = outf.time2t(dates)
    ntimes = len(outf.dimensions['TSTEP'])
    outside = (
        (i < 0) | (i >= outf.NCOLS) |
        (j < 0) | (j >= outf.NROWS) |
        (tidx < 0) | (tidx >= ntimes)
    )
    inside = ~outside
    ti = tidx[inside]
    ii = i[inside]
    ji = j[inside]
    vals = np.array(vals)[inside]
    if makecsv:
        lons = np.array(lons)[inside]
        dates = np.array(dates)[inside]
        lats = np.array(lats)[inside]
        outd = OrderedDict()
        outd['longitude'] = lons
        outd['latitude'] = lats
        outd['date'] = np.array([
            date.strftime('%Y-%m-%d %H:%M:%S%z') for date in dates
        ])
        outd['O3PPB'] = vals
        pd.DataFrame.from_dict(outd).to_csv(csvpath, index=False)

    if makencf:
        sample = np.array([ti, ji, ii, vals]).T
        bins = [
            np.arange(ntimes + 1) - 0.5,
            np.arange(outf.NROWS + 1) - 0.5,
            np.arange(outf.NCOLS + 1) - 0.5
        ]
        ddval, edges, binn = binned_statistic_dd(
            sample[:, :-1], sample[:, -1], expand_binnumbers=True,
            statistic='mean', bins=bins
        )
        ddcounts, edges, binn = binned_statistic_dd(
            sample[:, :-1], sample[:, -1], expand_binnumbers=True,
            statistic='count', bins=bins
        )
        good = ddcounts > 0
        ovar[good[:, None]] = ddval[good]
        nvar[good[:, None]] = ddcounts[good]
        savf = outf.mask(values=0).save(
            ncfpath, format='NETCDF4_CLASSIC', complevel=1, verbose=verbose
        )
        savf.close()
