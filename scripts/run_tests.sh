#!/bin/bash

SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

echo ""
echo ""
echo "===================================="
echo "=== STARTING TESTS with NOSETESTS==="
echo "===================================="
echo ""
echo ""

set -o xtrace
cd $SCRIPTDIR/..

nosetests --exe --with-coverage --cover-package=iter8_analytics --cover-html --cover-html-dir=$SCRIPTDIR/../code_coverage
