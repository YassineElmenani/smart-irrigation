import pytest
def test_create_telemetry(client):
    response = client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-test-01",
            "soil_moisture": 32.5,
            "temperature": 24.1,
            "air_humidity": 58.0,
            "prediction": "irrigate",
            "pump_status": "on",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["device_id"] == "esp32-test-01"
    assert data["soil_moisture"] == 32.5
    assert data["temperature"] == 24.1
    assert data["air_humidity"] == 58.0
    assert data["prediction"] == "irrigate"
    assert data["pump_status"] == "on"
    assert data["id"] is not None

def test_create_telemetry_invalid_soil_moisture(client):
    response = client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-test-01",
            "soil_moisture": 150,
            "temperature": 24.1,
            "air_humidity": 58.0,
            "prediction": "irrigate",
            "pump_status": "on",
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()
def test_retrieve_telemetry(client):
    # 1. Create a telemetry record
    payload = {
        "device_id": "esp32-test-02",
        "soil_moisture": 45.0,
        "temperature": 26.0,
        "air_humidity": 60.0,
        "prediction": "no_irrigate",
        "pump_status": "off",
    }

    create_response = client.post(
        "/api/telemetry",
        json=payload,
    )

    assert create_response.status_code == 201

    # 2. Retrieve telemetry history
    history_response = client.get(
        "/api/telemetry",
        params={"device_id": "esp32-test-02"},
    )

    assert history_response.status_code == 200

    # 3. Check the retrieved record
    records = history_response.json()

    assert len(records) == 1
    assert records[0]["device_id"] == "esp32-test-02"
    assert records[0]["soil_moisture"] == 45.0
def test_get_latest_telemetry(client):
    # Create a measurement
    client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-latest-test",
            "soil_moisture": 38.0,
            "temperature": 25.0,
            "air_humidity": 55.0,
            "prediction": "irrigate",
            "pump_status": "on",
        },
    )

    # Request the latest measurement
    response = client.get(
        "/api/telemetry/latest",
        params={"device_id": "esp32-latest-test"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["device_id"] == "esp32-latest-test"
    assert data["soil_moisture"] == 38.0
    assert data["prediction"] == "irrigate"
def test_get_pump_status(client):
    # First, submit a measurement
    client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-pump-test",
            "soil_moisture": 30.0,
            "temperature": 25.0,
            "air_humidity": 60.0,
            "prediction": "irrigate",
            "pump_status": "on",
        },
    )

    # Request the pump status
    response = client.get(
        "/api/pump/status",
        params={"device_id": "esp32-pump-test"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["pump_status"] == "on"
    assert data["prediction"] == "irrigate"
def test_telemetry_statistics(client):
    # Create the first measurement
    response1 = client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-stats-test",
            "soil_moisture": 30.0,
            "temperature": 20.0,
            "air_humidity": 40.0,
            "prediction": "irrigate",
            "pump_status": "on",
        },
    )

    assert response1.status_code == 201

    # Create the second measurement
    response2 = client.post(
        "/api/telemetry",
        json={
            "device_id": "esp32-stats-test",
            "soil_moisture": 50.0,
            "temperature": 30.0,
            "air_humidity": 60.0,
            "prediction": "no_irrigate",
            "pump_status": "off",
        },
    )

    assert response2.status_code == 201

    # Request statistics
    response = client.get(
        "/api/telemetry/stats",
        params={
            "device_id": "esp32-stats-test",
            "hours": 24,
        },
    )

    assert response.status_code == 200

    data = response.json()

    # Verify the calculations
    assert data["samples"] == 2
    assert data["soil_moisture_min"] == pytest.approx(30.0)
    assert data["soil_moisture_max"] == pytest.approx(50.0)
    assert data["soil_moisture_avg"] == pytest.approx(40.0)
    assert data["temperature_avg"] == pytest.approx(25.0)
    assert data["air_humidity_avg"] == pytest.approx(50.0)
    assert data["irrigation_decisions"] == 1
    assert data["pump_on_samples"] == 1
def test_get_latest_telemetry_not_found(client):
    response = client.get(
        "/api/telemetry/latest",
        params={"device_id": "esp32-empty-device"},
    )

    assert response.status_code == 404