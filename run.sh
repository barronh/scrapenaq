#!/bin/bash

# Download at least 3 days after the measurement day of interest
# data is often delivered after the measurement day
./scripts/get.py 2019-01-01 2019-01-04
./scripts/subset.py o3 2019-01-01 2019-01-04
./scripts/convert.py o3 2019-01-01 2019-01-01 12US1
