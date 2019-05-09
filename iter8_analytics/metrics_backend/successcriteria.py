class StatisticalTests: # only provides class methods for statistical tests; cannot be instantiated
    @staticmethod
    def simple_threshold(candidate_metric, criterion):
        #handle None response
        test_result = {
            "sample_size_sufficient": True
        }
        if candidate_metric["statistics"]["sample_size"] < criterion["sample_size"]:
            test_result["sample_size_sufficient"] = False
            test_result["success"] = False
        else:
            if candidate_metric["statistics"]["value"] <= criterion["value"]:
                test_result["success"] = True
            else:
                test_result["success"] = False
        return test_result

    @staticmethod
    def simple_delta(baseline_metric, candidate_metric, criterion):
        #handle None response
        test_result = {
            "sample_size_sufficient": True
        }
        if candidate_metric["statistics"]["sample_size"] < criterion["sample_size"] or baseline_metric["statistics"]["sample_size"] < criterion["sample_size"]:
            test_result["sample_size_sufficient"] = False
            test_result["success"] = False
        else:
            if candidate_metric["statistics"]["value"] <= ((1 + criterion["value"]) * baseline_metric["statistics"]["value"]):
                test_result["success"] = True
            else:
                test_result["success"] = False
        return test_result

class SuccessCriterion:
    """
    Class with methods for performing a statistical test on a metric.
    """
    def __init__(self, criterion_wrapper):
        """
        criterion_wrapper:  {
                        "metricName": "iter8_error_rate",
                        "criterion": {
                            "type": "threshold",
                            "value": 0.02,
                            "confidence": 98,
                            "use_for_traffic_control": false
                        }
                    }
        """
        self.criterion_wrapper = criterion_wrapper
        self.metric_name = criterion_wrapper["metric_name"]
        self.criterion = criterion_wrapper
        if "stop_on_failure" not in self.criterion:
            self.criterion["stop_on_failure"] = False
#        self.iter8metric = Iter8Metric.create(name, entity_tags)

    def test(self):
        raise NotImplementedError()

    def post_process_test_result(self, test_result):
        is_or_is_not = "is" if test_result["success"] else "is not"
        delta_or_threshold = "delta" if self.criterion["type"] == "delta" else "threshold"
        confidence_str = f"with confidence {self.criterion['confidence']}%" if ("confidence" in self.criterion and (self.criterion["confidence"] > 0)) else ""
        baseline_str = "of the baseline" if self.criterion["type"] == "delta" else ""
        result_str = f"{self.metric_name} of the candidate {is_or_is_not} within {delta_or_threshold} {self.criterion['value']} {confidence_str} {baseline_str}. "
        conclusion_str = "Insufficient sample size. " if not test_result["sample_size_sufficient"] else result_str

        return {
            "metric_name": self.metric_name,
            "conclusions": [conclusion_str],
            "success_criterion_met": test_result["success"],
            "abort_experiment": self.criterion["stop_on_failure"] and not test_result["success"]
        }

class DeltaCriterion(SuccessCriterion):
    def __init__(self, criterion, baseline_metrics, canary_metrics):
        super().__init__(criterion)
        self.baseline_metric = baseline_metrics
        self.candidate_metric = canary_metrics

    def test(self):
        # t_delta, bernoulli_delta are the other options beyond simple_delta
        test_result = StatisticalTests.simple_delta(self.baseline_metric, self.candidate_metric, self.criterion)
        return self.post_process_test_result(test_result)


class ThresholdCriterion(SuccessCriterion):
    def __init__(self, criterion, canary_metrics):
        super().__init__(criterion)
        self.candidate_metric = canary_metrics

    def test(self):
        # t_test, bernoulli_test are the other options beyond simple_threshold
        test_result = StatisticalTests.simple_threshold(self.candidate_metric, self.criterion)
        return self.post_process_test_result(test_result)
