#!/work/ROMO/anaconda_envs/basic38/bin/python
import pandas as pd
import urllib.request
import re
import os
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('startdate', help='Find ndjson.gz created >= startdate')
parser.add_argument('enddate', help='Find ndjson.gz created <= enddate')

args = parser.parse_args()

# Find ndjson.gz paths created between these dates
dates = pd.date_range(args.startdate, args.enddate)

# ndjson names are between Key tags
keyre = re.compile('<Key>(.+?)</Key>')

# Amazon S3 bucket root
BROOT = 'openaq-fetches.s3.amazonaws.com/'

for date in dates:
    # Path used to generate an xml describing ndjson.gz paths
    # archived on date
    xrpath = (
        'https://{}?delimiter=%2F&'.format(BROOT) +
        'prefix=realtime-gzipped%2F{}%2F'.format(date.strftime('%F'))
    )
    # xml that describe contents will be downloaded here
    xmlpath = BROOT + date.strftime('realtime-gzipped/%F.xml')
    # Contents will be downloaded to the folder
    zippedpath = BROOT + date.strftime('realtime-gzipped/%F')
    # Make if it does not exist
    os.makedirs(zippedpath, exist_ok=True)

    # If not already downloaded, download xml
    if os.path.exists(xmlpath):
        print('Keeping cached', xmlpath)
    else:
        urllib.request.urlretrieve(xrpath, xmlpath)
    xmltxt = open(xmlpath, mode='r').read()
    # Each key is a ndjson.gz
    keys = keyre.findall(xmltxt)
    for key in keys:
        url = 'https://' + BROOT + key
        outpath = BROOT + key
        # If not already downloaded, download ndjson.gz
        if os.path.exists(outpath):
            print('Keeping cached', outpath)
        else:
            urllib.request.urlretrieve(url, outpath)
