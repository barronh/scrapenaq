ScrapenAQ
---------

A web scraping software to download and process OpenAQ data from the S3
archive. This software depends on Amazon's web interface and on OpenAQ's
archive approach, and may need to be updated if things change.

Prerequisites
-------------

- Linux or Mac
- Python3
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
|       `-- OPENAQ.<GDNAM>.%Y-%m-%d.csv
|-- nc
|   `-- <GDNAM>
|       `-- OPENAQ.<GDNAM>.%Y-%m-%d.nc
|-- o3
|   `-- %Y
|-- openaq-fetches.s3.amazonaws.com
|   `-- realtime-gzipped
`-- scripts
    |-- convert.py
    |-- get.py
    `-- subset.py
```
