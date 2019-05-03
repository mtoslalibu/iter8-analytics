# Run Bookinfo as Knative services

## Prerequisites
Kubernetes(v1.11+)
Istio(v1.1+)
Knative serving(v0.5.0)
Chrome with extention Requstly installed

If you have your k8s cluster, you can follow the instructions below to complete the installation for Istio and Knative serving.
https://github.com/knative/docs/blob/master/docs/install/Knative-with-IKS.md

## Deploy the application
Let's follow the steps to 

### Step 1: Deploy the application with reviews v2
Apply the bookinfo application with service reviews version 2 onto your K8s cluster.
```bash
kubectl apply -f productpage.yaml
kubectl apply -f reviews-v2.yaml
kubectl apply -f details.yaml
kubectl apply -f ratings.yaml
```

Noted that small code changes have been made to productpage and reviews -- env vars are set to let the services know which port to talk to when internal calls are made. Knative services listen for traffic at port 80, which is different from the default setting in original bookinfo application.

Now you can check the knative services by running:
```bash
kubectl get ksvc
```

### Step 2: Access the application from the browser
To access the application from browser, we need a few more setups:
Get the ip address of the Ingress Gateway in the cluster:
```bash
INGRESSGATEWAY=istio-ingressgateway
INGRESSGATEWAY_LABEL=istio

export INGRESS_IP=`kubectl get svc $INGRESSGATEWAY --namespace istio-system \
--output jsonpath="{.status.loadBalancer.ingress[*].ip}"`
echo $INGRESS_IP
```

Get the hostname exposed by productpage service:
```bash
export SERVICE_HOSTNAME=`kubectl get ksvc productpage --output jsonpath="{.status.domain}"`
echo $SERVICE_HOSTNAME
```

Define a new rule in Requestly which adds a host header to a request:

Save this setting and turn on the rule.

Now you can view the application with this url in the browser:
```bash
$INGRESS_IP/productpage
```

You may need to wait for several seconds and keep refreshing the page for a few times until all services are up and show results on the webpage.

### Step 3: Update reviews service to version 3
Deploy version 3 of reviews:
```bash
kubectl apply -f reviews-v3.yaml
```

You can now check the updated application following the same procedures in step 2.
Now the "stars" in reviews should have changed from black to red.

### Step 4: Traffic splitting between reviews version 2 and version 3
Get the revisions for service reviews.
```bash
kubectl get revision -l "serving.knative.dev/service=productpage"
```
You should now see two revisions listed.

Then copy and paste these two revision names into the revisions list in the `reviews-v2-50-v3-50.yaml` file. Here we change the type of service reviews from `runLatest` to `release`, which enables us to specify how traffic would be routed between primary and candidate revisions.
The `rolloutPercent: 50` suggests that 50 pecents of the traffic to service reviews will be routed to the candidate revision(second item in the list).

Then apply the changes.
```bash
kubectl apply -f reviews-v2-50-v3-50.yaml
```

Now if you keep refreshing the application webpage, you should see black or red stars appearing in the reviews section with half possibilities for each case.