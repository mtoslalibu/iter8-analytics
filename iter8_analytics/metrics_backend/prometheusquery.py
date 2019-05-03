from string import Template
import requests
import logging
import numpy as np

log = logging.getLogger(__name__)


class PrometheusQuery():
    def __init__(self, prometheus_url, query_spec):
        self.prometheus_url = prometheus_url + "/api/v1/query"
        self.query_spec = query_spec

    def query_from_template(self, interval_str, offset_str):
        kwargs = {
            "interval": interval_str,  # interval must be interval string
            # offset must be offset string
            "offset_str": f" offset {offset_str}" if offset_str else "",
            "entity_labels": ",".join(self.query_spec["entity_tags"].keys())
        }
        query_template = Template(self.query_spec["query_template"])
        query = query_template.substitute(**kwargs)
        return self.query(query)

    def query(self, query):
        params = {'query': query}
        log.info(query)
        prom_result = requests.get(self.prometheus_url, params=params).json()
        return self.post_process(prom_result)

    def post_process(self, prom_result):
        if "data" not in prom_result:
            if self.query_spec["zero_value_on_nodata"] == True:
                return 0
            else:
                return None
        results = prom_result["data"]["result"]
        if prom_result["status"] == "error":
            raise ValueError("Invalid query")
        if results == []:
            if self.query_spec["zero_value_on_nodata"] == True:
                return 0
            else:
                return None
        match_key = self.query_spec["entity_tags"]
        for each_result in results:
            if each_result["metric"] == match_key:
                result_float = float(each_result["value"][1])
                if not np.isnan(result_float):
                    return float(each_result["value"][1])
        if self.query_spec["zero_value_on_nodata"] == True:
            return 0
        else:
            return None
