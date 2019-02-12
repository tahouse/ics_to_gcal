#!/bin/bash

export LANG="en_US.UTF-8"
export LC_COLLATE="en_US.UTF-8"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo $USER >> $DIR/out.log

source /anaconda3/etc/profile.d/conda.sh
conda activate cal

echo `which python` >> $DIR/out.log
echo `python --version` >> $DIR/out.log

python -u $DIR/cal.py 2>&1 | tee -a $DIR/out.log
