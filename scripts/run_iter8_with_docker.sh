#/bin/bash

SCRIPTDIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# Set this environment variable to point to your Prometheus query server
ITER8_ANALYTICS_METRICS_BACKEND_URL="http:/localhost:9090"

echo "Cleaning up..."
docker rm -f iter8-analytics 2>/dev/null

echo "Starting container..."
docker run --name iter8-analytics \
    -p 5555:5555 \
    -e ITER8_ANALYTICS_METRICS_BACKEND_URL=$ITER8_ANALYTICS_METRICS_BACKEND_URL \
    -d iter8-analytics