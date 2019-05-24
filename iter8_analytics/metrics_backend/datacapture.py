import logging, os, json

log = logging.getLogger(__name__)

class DataCapture:
    captured_data = {
        "request_payload": None,
        "prometheus_requests": [],
        "prometheus_responses": [],
        "service_response": None
    }
    data_capture_mode = None

    @classmethod
    def fill_value(cls, key, value):
        if cls.data_capture_mode == "ON":
            cls.captured_data[key] = value

    @classmethod
    def append_value(cls, key, value):
        log.info(f"Data Capture: {key} Value {value}")
        if cls.data_capture_mode == "ON":
            cls.captured_data[key].append(value)

    @classmethod
    def initialize_data_capture(cls):
        cls.captured_data = {
            "request_payload": None,
            "prometheus_requests": [],
            "prometheus_responses": [],
            "service_response": None
        }

    @classmethod
    def save_data(cls):
        data_capture_file_path = "data_captured.json"
        exists = os.path.isfile(data_capture_file_path)
        if exists:
            with open(data_capture_file_path, 'r+') as json_file:
                try:
                    captured_so_far = json.load(json_file)
                    captured_so_far.append(cls.captured_data)
                    json_file.seek(0)
                    json.dump(captured_so_far, json_file)
                except:
                    with open(data_capture_file_path, 'w') as f:
                        json.dump([cls.captured_data], f)
        else:
            with open(data_capture_file_path, 'w') as f:
                json.dump([cls.captured_data], f)
        cls.initialize_data_capture()
