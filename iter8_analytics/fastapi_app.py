# Module dependencies
from fastapi import FastAPI, Body

# iter8 stuff
from iter8_analytics.api.analytics.experiment_iteration_response import *
from iter8_analytics.api.analytics.experiment_iteration_request import *
from iter8_analytics.api.health.health_check_response import Iter8HealthCheck
from iter8_analytics.api.analytics.endpoints.examples import *


app = FastAPI()

@app.post("/assessment", response_model=Iter8AssessmentAndRecommendation)
def provide_assessment_for_this_experiment_iteration(eip: ExperimentIterationParameters = Body(..., example=eip_example)):
    """
      POST iter8 experiment iteration data and obtain assessment of how the versions are performing and recommendations on how to split traffic based on multiple strategies.
      """
    return Iter8AssessmentAndRecommendation(** ar_example)



@app.get("/health_check", response_model=Iter8HealthCheck)
def provide_iter8_analytics_health():
    """
      Get iter8 analytics health status
      """
    health_ok = {"status": "Ok"}
    return Iter8HealthCheck(** health_ok)
