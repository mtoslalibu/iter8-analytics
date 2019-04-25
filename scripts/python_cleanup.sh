#/bin/bash

##  This script deletes all __pycache__ directories
## as well as the *.pyc and *.pyo files that accumulate
## in the iter8_analytics source-code tree as the code
## is tested locally.

SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo ""
echo "Removing __pycache__, *.pyc, *.pyo files..."

TARGET_DIR=$SCRIPTDIR/../iter8_analytics

echo "--- searching and deleting files located under $TARGET_DIR"
find $TARGET_DIR | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

echo "Done."
echo ""
