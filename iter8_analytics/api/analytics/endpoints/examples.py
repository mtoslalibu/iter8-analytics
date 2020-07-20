import copy

eip_example = {
    'start_time': "2020-04-03T12:55:50.568Z",
    'iteration_number': 1,
    'service_name': "reviews",
    "metric_specs": {
        "counter_metrics": [
        {
            "id": "iter8_request_count",
            "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval])) by ($version_labels)"
        },
        {
            "id": "iter8_total_latency",
            "query_template": "sum(increase(istio_request_duration_milliseconds_sum{reporter='source'}[$interval])) by ($version_labels)"
        },
        {
            "id": "iter8_error_count",
            "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval])) by ($version_labels)",
            "preferred_direction": "lower"
        },
        {
            "id": "conversion_count",
            "query_template": "sum(increase(newsletter_signups[$interval])) by ($version_labels)"
        },
    ],  
    "ratio_metrics": [
        {
            "id": "iter8_mean_latency",
            "numerator": "iter8_total_latency",
            "denominator": "iter8_request_count",
            "preferred_direction": "lower",
            "zero_to_one": False
        }, 
        {
            "id": "iter8_error_rate",
            "numerator": "iter8_error_count",
            "denominator": "iter8_request_count",
            "preferred_direction": "lower",
            "zero_to_one": True
        }, 
        {
            "id": "conversion_rate",
            "numerator": "conversion_count",
            "denominator": "iter8_request_count",
            "preferred_direction": "higher",
            "zero_to_one": True
        }
    ]},
    "criteria": [
        {
            "id": "0",
            "metric_id": "iter8_mean_latency",
            "is_reward": False,
            "threshold": {
                "type": "absolute",
                "value": 25
            }
        }
    ],
    "baseline": {
        "id": "reviews_base",
        "version_labels": {
            'destination_service_namespace': "default",
            'destination_workload': "reviews-v1"
        }
    },
    "candidates": [
        {
            "id": "reviews_candidate",
            "version_labels": {
                'destination_service_namespace': "default",
                'destination_workload': "reviews-v2"
            }
        }
    ]
}

ar_example = {
    'timestamp': "2020-04-03T12:59:50.568Z",
    'baseline_assessment': {
        "id": "reviews_base",
        "request_count": 500,
        "win_probability": 0.1,
        "criterion_assessments": [
            {
                "id": "0",
                "metric_id": "iter8_mean_latency",
                "statistics": {
                    "value": 0.005,
                    "ratio_statistics": {
                        "improvement_over_baseline": {
                            'lower': 2.3,
                            'upper': 5.0
                        },
                        "probability_of_beating_baseline": .82,
                        "probability_of_being_best_version": 0.1,
                        "credible_interval": {
                            'lower': 22, 
                            'upper': 28
                        }
                    }
                },
                "threshold_assessment": {
                    "threshold_breached": False,
                    "probability_of_satisfying_threshold": 0.8
                }
            }
        ]
    },
    'candidate_assessments': [
        {
            "id": "reviews_candidate",
            "request_count": 1500,
            "win_probability": 0.11,
            "criterion_assessments": [
                {
                    "id": "0",
                    "metric_id": "iter8_mean_latency",
                    "statistics": {
                        "value": 0.1005,
                        "ratio_statistics": {
                            "sample_size": 1500,
                            "improvement_over_baseline": {
                                'lower': 12.3, 
                                'upper': 15.0
                            },
                            "probability_of_beating_baseline": .182,
                            "probability_of_being_best_version": 0.1,
                            "credible_interval": {
                                'lower': 122, 
                                'upper': 128
                            }
                        }
                    },
                    "threshold_assessment": {
                        "threshold_breached": True,
                        "probability_of_satisfying_threshold": 0.180
                    }
                }
            ]
        }
    ],
    'traffic_split_recommendation': {
        'unif': {
            'reviews_base': 50.0,
            'reviews_candidate': 50.0
        }
    },
    'winner_assessment': {
        'winning_version_found': False
    },
    'status': ["all_ok"]
}

reviews_example = {
  "start_time": "2020-05-17T12:55:50.568Z",
  "service_name": "reviews",
  "metric_specs": {
    "counter_metrics": [
      {
        "id": "iter8_request_count",
        "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval])) by ($version_labels)"
      },
      {
        "id": "iter8_total_latency",
        "query_template": "sum(increase(istio_request_duration_milliseconds_sum{reporter='source'}[$interval])) by ($version_labels)"
      },
      {
        "id": "iter8_error_count",
        "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval])) by ($version_labels)",
        "preferred_direction": "lower"
      }
    ],
    "ratio_metrics": [
      {
        "id": "iter8_mean_latency",
        "numerator": "iter8_total_latency",
        "denominator": "iter8_request_count",
        "preferred_direction": "lower"
      }
    ]
  },
  "criteria": [
    {
      "id": "0",
      "metric_id": "iter8_error_count",
      "is_reward": False,
      "threshold": {
        "type": "absolute",
        "value": 25
      }
    },
    {
      "id": "1",
      "metric_id": "iter8_mean_latency",
      "is_reward": False,
      "threshold": {
        "type": "absolute",
        "value": 500
      }
    }
  ],
  "baseline": {
    "id": "reviews_base",
    "version_labels": {
      "destination_service_namespace": "bookinfo-iter8",
      "destination_workload": "reviews-v2"
    }
  },
  "candidates": [
    {
      "id": "reviews_candidate",
      "version_labels": {
        "destination_service_namespace": "bookinfo-iter8",
        "destination_workload": "reviews-v3"
      }
    }
  ]
}

last_state = {
    "aggregated_counter_metrics": {
      "reviews_candidate": {
        "iter8_request_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }, 
        "iter8_error_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        },
        "iter8_total_latency": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      },
      "reviews_base": {
        "iter8_request_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        },
        "iter8_error_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }, 
        "iter8_total_latency": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      }
    },
    "aggregated_ratio_metrics": {
      "reviews_candidate": {
        "iter8_mean_latency": {
          "value": None,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      },
      "reviews_base": {
        "iter8_mean_latency": {
          "value": None,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      }
    },
    "ratio_max_mins": {
      "iter8_mean_latency": {
        "minimum": None,
        "maximum": None
      }
    }
  }

partial_last_state = {
    "aggregated_counter_metrics": {
      "reviews_candidate": {
        "iter8_request_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }, 
        "iter8_error_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      },
      "reviews_base": {
        "iter8_request_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        },
        "iter8_error_count": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }, 
        "iter8_total_latency": {
          "value": 0,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      }
    },
    "aggregated_ratio_metrics": {
      "reviews_candidate": {
        "iter8_mean_latency": {
          "value": None,
          "timestamp": "2020-05-19T11:41:51.474487+00:00",
          "status": "no versions in prometheus response"
        }
      }
    },
    "ratio_max_mins": {
      "iter8_mean_latency": {
        "minimum": None,
        "maximum": None
      }
    }
  }

last_state_with_ratio_max_mins = copy.deepcopy(last_state)
last_state_with_ratio_max_mins["ratio_max_mins"] = {
      "iter8_mean_latency": {
        "minimum": 1.5,
        "maximum": 20
      }
    }

reviews_example_with_last_state = {
  "start_time": "2020-05-17T12:55:50.568Z",
  "service_name": "reviews",
  "metric_specs": {
    "counter_metrics": [
      {
        "id": "iter8_request_count",
        "query_template": "sum(increase(istio_requests_total{reporter='source'}[$interval])) by ($version_labels)"
      },
      {
        "id": "iter8_total_latency",
        "query_template": "sum(increase(istio_request_duration_milliseconds_sum{reporter='source'}[$interval])) by ($version_labels)"
      },
      {
        "id": "iter8_error_count",
        "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source'}[$interval])) by ($version_labels)",
        "preferred_direction": "lower"
      }
    ],
    "ratio_metrics": [
      {
        "id": "iter8_mean_latency",
        "numerator": "iter8_total_latency",
        "denominator": "iter8_request_count",
        "preferred_direction": "lower"
      }
    ]
  },
  "criteria": [
    {
      "id": "0",
      "metric_id": "iter8_error_count",
      "is_reward": False,
      "threshold": {
        "type": "absolute",
        "value": 25
      }
    },
    {
      "id": "1",
      "metric_id": "iter8_mean_latency",
      "is_reward": False,
      "threshold": {
        "type": "absolute",
        "value": 500
      }
    }
  ],
  "baseline": {
    "id": "reviews_base",
    "version_labels": {
      "destination_service_namespace": "bookinfo-iter8",
      "destination_workload": "reviews-v2"
    }
  },
  "candidates": [
    {
      "id": "reviews_candidate",
      "version_labels": {
        "destination_service_namespace": "bookinfo-iter8",
        "destination_workload": "reviews-v3"
      }
    }
  ],
  "last_state": copy.deepcopy(last_state)
}

reviews_example_with_partial_last_state = copy.deepcopy(reviews_example_with_last_state)
reviews_example_with_partial_last_state["last_state"] = copy.deepcopy(partial_last_state)

reviews_example_with_ratio_max_mins = copy.deepcopy(reviews_example_with_last_state)
reviews_example_with_ratio_max_mins["last_state"] = copy.deepcopy(last_state_with_ratio_max_mins)

eip_with_invalid_ratio = copy.deepcopy(reviews_example_with_ratio_max_mins)
eip_with_invalid_ratio["metric_specs"]["ratio_metrics"].append({
    "id": "iter8_invalid_latency",
    "numerator": "iter8_total_invalid_latency",
    "denominator": "iter8_request_count",
    "preferred_direction": "lower"
})
eip_with_invalid_ratio["criteria"].append({
    "id": "2",
    "metric_id": "iter8_invalid_latency",
    "is_reward": False,
    "threshold": {
          "type": "absolute",
          "value": 500
    }
})

eip_with_unknown_metric_in_criterion = copy.deepcopy(reviews_example_with_ratio_max_mins)
eip_with_unknown_metric_in_criterion["criteria"].append({
    "id": "2",
    "metric_id": "iter8_invalid_latency",
    "is_reward": False,
    "threshold": {
          "type": "absolute",
          "value": 500
    }
})


eip_with_current_time = {
    "name": "productpage-abn-test",
    "start_time": "2020-07-17T20:05:02-04:00",
    "service_name": "productpage",
    "iteration_number": 0,
    "metric_specs": {
        "counter_metrics": [{
            "name": "iter8_request_count",
            "preferred_direction": "lower",
            "query_template": "sum(increase(istio_requests_total{reporter='source',job='istio-mesh'}[$interval])) by ($version_labels)"
        }, {
            "name": "iter8_total_latency",
            "preferred_direction": "lower",
            "query_template": "(sum(increase(istio_request_duration_milliseconds_sum{reporter='source',job='istio-mesh'}[$interval])) by ($version_labels))*1000"
        }, {
            "name": "iter8_error_count",
            "preferred_direction": "higher",
            "query_template": "sum(increase(istio_requests_total{response_code=~'5..',reporter='source',job='istio-mesh'}[$interval])) by ($version_labels)"
        }, {
            "name": "books_purchased_total",
            "preferred_direction": "higher",
            "query_template": "sum(increase(number_of_books_purchased_total{}[$interval])) by ($version_labels)"
        }, {
            "name": "500_ms_latency_percentile",
            "preferred_direction": "higher",
            "query_template": "(sum(increase(istio_request_duration_milliseconds_bucket{le='500',reporter='source',job='istio-mesh'}[$interval])) by ($version_labels))"
        }, {
            "name": "latency_percentile_total",
            "query_template": "(sum(increase(istio_request_duration_milliseconds_bucket{le='10000',reporter='source',job='istio-mesh'}[$interval])) by ($version_labels))"
        }],
        "ratio_metrics": [{
            "name": "iter8_mean_latency",
            "numerator": "iter8_total_latency",
            "denominator": "iter8_request_count"
        }, {
            "name": "iter8_error_rate",
            "numerator": "iter8_error_count",
            "denominator": "iter8_request_count",
            "zero_to_one": True
        }, {
            "name": "mean_books_purchased",
            "numerator": "books_purchased_total",
            "denominator": "iter8_request_count"
        }, {
            "name": "mean_500_ms_latency_percentile",
            "numerator": "500_ms_latency_percentile",
            "denominator": "latency_percentile_total"
        }]
    },
    "criteria": [{
        "id": "iter8_mean_latency",
        "metric_id": "iter8_mean_latency",
        "is_reward": False,
        "threshold": {
            "threshold_type": "relative",
            "value": 0.6
        }
    }, {
        "id": "iter8_error_rate",
        "metric_id": "iter8_error_rate",
        "is_reward": False,
        "threshold": {
            "threshold_type": "absolute",
            "value": 0.05
        }
    }, {
        "id": "mean_500_ms_latency_percentile",
        "metric_id": "mean_500_ms_latency_percentile",
        "is_reward": False,
        "threshold": {
            "threshold_type": "absolute",
            "value": 0.99
        }
    }, {
        "id": "mean_books_purchased",
        "metric_id": "mean_books_purchased",
        "is_reward": True
    }],
    "baseline": {
        "id": "productpage-v1",
        "version_labels": {
            "destination_service_namespace": "kubecon-demo",
            "destination_workload": "productpage-v1"
        }
    },
    "candidates": [{
        "id": "productpage-v2",
        "version_labels": {
            "destination_service_namespace": "kubecon-demo",
            "destination_workload": "productpage-v2"
        }
    }, {
        "id": "productpage-v3",
        "version_labels": {
            "destination_service_namespace": "kubecon-demo",
            "destination_workload": "productpage-v3"
        }
    }],
    "last_state": {},
    "traffic_control": {
        "max_increment": 2,
        "strategy": "progressive"
    }
}

reviews_example_without_request_count = copy.deepcopy(reviews_example)
del reviews_example_without_request_count["criteria"][1]
del reviews_example_without_request_count["metric_specs"]["counter_metrics"][0]
del reviews_example_without_request_count["metric_specs"]["ratio_metrics"][0]