import pytest
import app as portal


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "test_portal.db"
    monkeypatch.setattr(portal, "DB_PATH", test_db)
    portal.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    portal.init_db()
    with portal.app.test_client() as client:
        yield client


def login(client, username, password="pass123"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True
    )


def test_customer_login_routes_to_customer_page(client):
    response = login(client, "customer1")
    assert response.status_code == 200
    assert b"Customer Status View" in response.data
    assert b"ORD-1001" in response.data


def test_employee_can_update_workflow_record(client):
    login(client, "employee1")
    response = client.post(
        "/employee",
        data={
            "order_id": "1",
            "status": "Delayed",
            "document_status": "Missing",
            "delay_reason": "Waiting on customer confirmation"
        },
        follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Workflow record updated" in response.data
    assert b"Waiting on customer confirmation" in response.data


def test_manager_dashboard_shows_core_metrics(client):
    response = login(client, "manager1")
    assert response.status_code == 200
    assert b"Manager Dashboard" in response.data
    assert b"Total Records" in response.data
    assert b"Missing Documents" in response.data
    assert b"Delayed Records" in response.data


def test_customer_cannot_access_manager_dashboard(client):
    login(client, "customer1")
    response = client.get("/manager", follow_redirects=True)
    assert response.status_code == 200
    assert b"Access denied for this role" in response.data
    assert b"Customer Status View" in response.data