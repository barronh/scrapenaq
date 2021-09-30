#!/usr/bin/env python
import os
import gzip
from glob import glob
from datetime import datetime
from collections import defaultdict
import pandas as pd
import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    'parameter',
    help='openaq parameters (e.g., o3, pm25, pm10, o3, so2, no2, co)'
)
parser.add_argument('startdate', help='Parse ndjson.gz >= startdate')
parser.add_argument('enddate', help='Parse ndjson.gz <= enddate')
parser.description = """
Parses gzipped ndjsons from download folder and extracts data for the selected
parameter. For each ndjson, the file creates separate ndjsons for each
measurement date. The resulting ndjsons are stored in:

<parameter>/<ndjsondate>/<measurementdate>.ndjson
"""

args = parser.parse_args()
parameter = args.parameter
dates = pd.date_range(args.startdate, args.enddate)
dirpaths = [
    date.strftime('openaq-fetches.s3.amazonaws.com/realtime-gzipped/%Y-%m-%d')
    for date in dates
]
foldertmpl = '{}/%Y/%F'.format(parameter)
paramtag = '"parameter":"{}"'.format(parameter)

for dirpath in dirpaths:
    print(dirpath, flush=True)
    param = defaultdict(lambda: [])
    date1 = datetime.strptime(
        os.path.basename(dirpath),
        '%Y-%m-%d'
    )
    paths = sorted(glob(dirpath + '/*.ndjson.gz'))
    for path in paths:
        outdir = date1.strftime(foldertmpl)
        os.makedirs(outdir, exist_ok=True)
        ts = os.path.basename(path).replace('.ndjson.gz', '')
        with gzip.GzipFile(path, 'r') as fin:
            data = []
            for l in fin.read().decode('utf-8').split('\n'):
                if paramtag in l:
                    start = l.find('"utc":"') + 7
                    end = start + 10
                    date = l[start:end]
                    outpath = outdir + '/' + date + '.ndjson'
                    param[outpath].append(l)

        for outpath, val in param.items():
            with open(outpath, 'w', encoding='utf-8') as outf:
                outf.write('\n'.join(val))
