#!/bin/bash

scriptdir="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

source ${scriptdir}/venv/bin/activate

python3 ./4x20-lcd-cal.py
