"""Exercise the real HTTP adapter and analysis service together."""
import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from route_lab.demo import make_server, openapi


@pytest.fixture(scope="module")
def lab_server():
    server = make_server(Path("results"), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def post(base, path, payload):
    req = Request(base + path, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def test_threshold_http(lab_server):
    code, result = post(lab_server, "/api/threshold", {
        "grid": [[1, 1, 1, 1, 1], [1, 1, 1, 1, 1]],
        "start": [0, 0], "goal": [0, 4], "cells": [[0, 1], [0, 2], [0, 3]],
    })
    assert code == 200, result
    assert result["first_switch_cost"] == 2
    assert [(r["cost"], r["steps"]) for r in result["levels"][:2]] == [(4, 4), (6, 6)]


def test_closures_http(lab_server):
    code, result = post(lab_server, "/api/closures", {
        "grid": [[1, 1, 1]], "start": [0, 0], "goal": [0, 2],
    })
    assert code == 200, result
    assert result["tested_count"] == 1
    assert result["critical_cells"] == [[0, 1]]


@pytest.mark.parametrize("path", ["/api/closures", "/api/threshold"])
def test_analysis_validation_http(lab_server, path):
    code, result = post(lab_server, path, {})
    assert code == 400
    assert result["code"] == "validation_error"
    assert result["field"]


def test_lab_static_script(lab_server):
    with urlopen(lab_server + "/static/lab.js") as response:
        assert response.status == 200
        assert b"/api/threshold" in response.read()


def test_analysis_schema_contract():
    paths = openapi()["paths"]
    threshold = paths["/api/threshold"]["post"]
    props = threshold["requestBody"]["content"]["application/json"]["schema"]
    assert "cells" in props["required"]
    assert props["additionalProperties"] is False
    schema = threshold["responses"]["200"]["content"]["application/json"]["schema"]
    assert "levels" in schema["required"]
    closure = paths["/api/closures"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert "critical_count" in closure["properties"]
