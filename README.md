# iter8

[![Build Status](https://travis.ibm.com/istio-research/iter8.svg?token=PbqjhFTz8kmzqqC9jUkr&branch=master)](https://travis.ibm.com/istio-research/iter8-controller)

## Requirements

* Kubernetes >= 1.14. `kubectl` command needs to work.
* Istio >= 1.1.5. `istioctl` command needs to work.
  + Ensure your Istio is installed with Prometheus addon enabled. Prometheus is enabled by default.
* Download iter8 (`git clone https://github.ibm.com/istio-research/iter8.git`)
* Docker Desktop >= 2.0.4.0
* Python >= 3.7

## Steps

* Clone the repository and navigate to the correct folder
```
cd iter8/
```
* Set Prometheus backend url to the variable `ITER8_ANALYTICS_METRICS_BACKEND_URL`.
```
export ITER8_ANALYTICS_METRICS_BACKEND_URL=<Your Prometheus backend URL>
```
By default, the url http://localhost:9090 is used.
* Build the iter8 docker image
```
./scripts/build_docker_image.sh
```
* Run the image created:
```
./scripts/run_iter8_with_docker.sh
```

You can now go to `http://localhost:5555/api/v1` to try out the iter8 analytics service!
