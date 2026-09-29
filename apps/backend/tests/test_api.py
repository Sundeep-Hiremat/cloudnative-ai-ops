import pytest
from fastapi.testclient import TestClient
from apps.backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_order_crud_flow():
    # 1. Create order
    create_payload = {
        "customer_name": "Alice Developer",
        "item_name": "Kubernetes Mastery Guide",
        "quantity": 2,
        "total_price": 99.99
    }
    response = client.post("/api/orders", json=create_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Alice Developer"
    assert data["status"] == "PENDING"
    order_id = data["id"]

    # 2. Get order by ID
    response = client.get(f"/api/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["id"] == order_id

    # 3. List orders
    response = client.get("/api/orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) > 0

    # 4. Update order status
    update_payload = {"status": "COMPLETED"}
    response = client.put(f"/api/orders/{order_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    # 5. Delete order
    response = client.delete(f"/api/orders/{order_id}")
    assert response.status_code == 204

    # 6. Verify deleted
    response = client.get(f"/api/orders/{order_id}")
    assert response.status_code == 404
