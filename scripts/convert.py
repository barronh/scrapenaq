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
    '-a', '--averaginghours', default=1, type=int,
    help='Number of hours in an averaging period. 1 or 24'
)

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
avghours = args.averaginghours

missing = [-999]
ugm3s = (b'micrograms/m**3', b'<C2><B5>m<C3><B4>', b'\xc2\xb5g/m\xc2\xb3')
gf = pnc.pncopen('GRIDDESC', format='griddesc', GDNAM=GDNAM)
gf.SDATE = int(outputdates[0].strftime('%Y%j'))
gf.TSTEP = 10000
del gf.variables['TFLAG']
gf.updatemeta()
outkey = param.upper()
outf = gf.subset(['DUMMY']).renameVariables(DUMMY=outkey).slice(
    TSTEP=np.zeros(24 // avghours, dtype='i')
)
outf.TSTEP = avghours * 10000

ovar = outf.variables[outkey]
nvar = outf.copyVariable(ovar, key=outkey + 'N')
ovar.long_name = outkey.ljust(16)
ovar.var_desc = ovar.long_name.ljust(80)
nvar.long_name = ('N' + outkey).ljust(16)
nvar.var_desc = nvar.long_name.ljust(80)
nvar.units = '1'.ljust(16)

delattr(outf, 'VAR-LIST')
del outf.variables['TFLAG']
outf.updatemeta()
setattr(outf, 'VAR-LIST', ovar.long_name + nvar.long_name)
outf.NVARS = 2
outf.createDimension('VAR', 2)
outf.updatetflag(overwrite=True)

ncftmpl = f'nc/{GDNAM}/OPENAQ.{GDNAM}.%F.{param}.{avghours:02d}H.nc'
csvtmpl = f'csv/{GDNAM}/OPENAQ.{GDNAM}.%F.{param}.{avghours:02d}H.csv'
for outdate in outputdates:
    ncfpath = outdate.strftime(ncftmpl)
    csvpath = outdate.strftime(csvtmpl)
    csvdir = os.path.dirname(csvpath)
    ncfdir = os.path.dirname(ncfpath)
    ncfexists = os.path.exists(ncfpath)
    csvexists = os.path.exists(csvpath)
    if args.netcdf and ncfexists:
        warn('Keeping cached', ncfpath)
    else:
        os.makedirs(ncfdir, exist_ok=True)
    if args.csv and csvexists:
        warn('Keeping cached', csvpath)
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
    outf.TSTEP = avghours * 10000
    del outf.variables['TFLAG']
    outf.updatetflag(overwrite=True)
    ovar[:] = 0
    nvar[:] = 0
    lines = []
    print(len(paths))
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
        apvalue = ap['value']
        apunit = ap['unit'].strip().lower()
        if (apvalue != avghours or apunit != 'hours'):
            warn(
                f'Skipping values with non {avghours}-hour'
                + f' averaging periods {apunit} {apvalue}'
            )
            continue

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
        if param == 'o3':
            if unit.encode('latin1') in ugm3s:
                val *= (293.15 * 8.314 / 101325. / 0.048)
                unit = 'ppb'
            elif unit in ('ppm'):
                val *= 1000
                unit = 'ppb'
            if unit != 'ppb':
                warn(f'***Unit warning: {unit} used as ppb for {param}')
            unit = 'ppb'
        elif param in ('pm25', 'pm10'):
            if not unit.encode('latin1') in ugm3s:
                warn(f'***Unit warning: {unit} used as {ugm3s[0]} for {param}')
            unit = ugm3s[0]
        else:
            raise KeyError(
                'Units must be unified for gridding.'
                + ' Currently, only O3 and PM are coded.'
            )
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
    if vals.size == 0:
        if verbose > 0:
            print('No valid data')
        continue

    if makecsv:
        if verbose > 0:
            print('Making csv')
        lons = np.array(lons)[inside]
        dates = np.array(dates)[inside]
        lats = np.array(lats)[inside]
        outd = OrderedDict()
        outd['longitude'] = lons
        outd['latitude'] = lats
        outd['date'] = np.array([
            date.strftime('%Y-%m-%d %H:%M:%S%z') for date in dates
        ])
        if param == 'o3':
            outd['O3PPB'] = vals
        else:
            outd[outkey] = vals

        pd.DataFrame.from_dict(outd).to_csv(csvpath, index=False)

    if makencf:
        if verbose > 0:
            print('Making ncf')
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
        ovar.units = unit.ljust(16)
        nvar[good[:, None]] = ddcounts[good]
        savf = outf.mask(values=0).save(
            ncfpath, format='NETCDF4_CLASSIC', complevel=1, verbose=verbose
        )
        savf.close()
