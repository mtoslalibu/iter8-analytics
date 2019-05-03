#/bin/bash

SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo ""
echo "Building iter8-analytics Docker image"

$SCRIPTDIR/python_cleanup.sh

CONTEXT_DIR=$SCRIPTDIR/..
docker build -t iter8-analytics $CONTEXT_DIR
