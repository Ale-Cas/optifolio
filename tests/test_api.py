"""Test optifolio REST API."""

import json

import httpx
from fastapi.testclient import TestClient

from optifolio.api import app
from optifolio.models import OptimizationRequest, OptimizationResponse

client = TestClient(app)


def test_read_root() -> None:
    """Test that reading the root is successful."""
    response = client.get("/")
    assert httpx.codes.is_success(response.status_code)


def test_post_optimization(optimization_request: OptimizationRequest) -> None:
    """Test the post optimization endpoint."""
    response = client.post("/optimization", json=json.loads(optimization_request.json()))
    assert httpx.codes.is_success(response.status_code)
    response_model = OptimizationResponse(**response.json())
    assert response_model.objective_values[0].name == optimization_request.objectives[0].name
    weights = response_model.weights.values()
    _tollerance = 1e-4
    assert sum(weights) - 1 <= _tollerance
    assert all(w >= _tollerance for w in weights)
