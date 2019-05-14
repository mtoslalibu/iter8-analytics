#!/bin/bash

# Export kubeconfig
$(ibmcloud cs cluster-config iter8 | grep "export KUBECONFIG")

# Ingress host
export INGRESS_HOST=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Prometheus port
export PROMETHEUS_PORT=$(kubectl -n istio-system get service prometheus-np -o jsonpath='{.spec.ports[?(@.nodePort)].nodePort}')

# Metrics backend url
export ITER8_ANALYTICS_METRICS_BACKEND_URL=http://$INGRESS_HOST:$PROMETHEUS_PORT

# Ingress port
export INGRESS_PORT=$(kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].port}')

# Bookinfo url
export BOOKINFO_URL=http://$INGRESS_HOST:$INGRESS_PORT/productpage