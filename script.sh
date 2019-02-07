#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source /anaconda3/etc/profile.d/conda.sh
conda activate cal

echo `which python`
echo `python --version`

python -u $DIR/cal.py 2>&1 | tee -a $DIR/out.log
