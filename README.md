ScrapenAQ
=========

A web scraping software to download and process OpenAQ data from the S3
archive. This software depends on Amazon's web interface and on OpenAQ's
archive approach, and may need to be updated if those change.


Prerequisites
-------------

- Windows, Linux, or Mac
- Python3
  - numpy
  - scipy
  - pandas
  - pseudonetcdf (for netcdf outputs)


Directory Structure
-------------------

```
.
|-- README.md
|-- run.sh
|-- csv
|   `-- <GDNAM>
|       |-- OPENAQ.<GDNAM>.%Y-%m-%d.01H.csv
|       `-- OPENAQ.<GDNAM>.%Y-%m-%d.24H.csv
|-- nc
|   `-- <GDNAM>
|       |-- OPENAQ.<GDNAM>.%Y-%m-%d.01H.nc
|       `-- OPENAQ.<GDNAM>.%Y-%m-%d.24H.nc
|-- o3
|   `-- %Y
|-- pm25
|   `-- %Y
|-- openaq-fetches.s3.amazonaws.com
|   `-- realtime-gzipped
`-- scripts
    |-- convert.py
    |-- get.py
    `-- subset.py
```
