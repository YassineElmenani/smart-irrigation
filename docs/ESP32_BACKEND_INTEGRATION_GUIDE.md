# ESP32 ↔ FastAPI Backend Integration Guide

This guide is for the teammate developing the ESP32 firmware in Arduino IDE. It defines how the ESP32 sends telemetry to the existing FastAPI backend.

## 1. Understand the responsibility split

The ESP32 firmware must continue to operate independently:

1. Read the sensors.
2. Run or call the TinyML inference locally on the ESP32.
3. Decide locally whether irrigation is needed.
4. Control the pump locally.
5. Send a copy of the measurement, prediction and reported pump state to the backend for supervision.

**Do not make pump control depend on a successful HTTP request.** If Wi-Fi or the backend is unavailable, local sensing, inference and pump control must continue. A telemetry failure should only mean that the measurement was not uploaded at that moment.

The ESP32-to-backend protocol currently specified by the backend is **HTTP POST with a JSON body**, over the Wi-Fi network. This is not MQTT.

## 2. Network setup for a local demonstration

For the first hardware test, connect the ESP32 and the computer running FastAPI to the same Wi-Fi network. The network must allow devices to communicate with one another; some guest Wi-Fi networks enable client isolation and block this.

### Start the backend on the backend computer

In PowerShell, from the repository's `backend/` directory, activate the virtual environment and start Uvicorn:

```powershell
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`0.0.0.0` tells Uvicorn to listen on the computer's network interfaces. It is a bind address, not the address the ESP32 should put in its URL.

### Find the backend computer's LAN IP address

Run:

```powershell
ipconfig
```

Find the IPv4 address for the active Wi-Fi adapter, for example `192.168.1.14`. This is only an example; use the actual address shown on the backend computer.

The ESP32 URL will then be:

```text
http://<BACKEND_PC_IP>:8000/api/telemetry
```

For example, if the backend computer's current IP is `192.168.1.14`:

```text
http://192.168.1.14:8000/api/telemetry
```

Do **not** use `127.0.0.1` or `localhost` in the ESP32 URL. Those addresses refer to the ESP32 itself when used by the ESP32, not to the backend computer.

### Verify network access before debugging firmware

From a second device on the same Wi-Fi network, open:

```text
http://<BACKEND_PC_IP>:8000/health
```

Expected body:

```json
{"status":"ok"}
```

If it cannot be opened, check that Uvicorn is running with `--host 0.0.0.0`, that both devices are on the same reachable network, and that Windows Firewall allows inbound connections to Python/Uvicorn on port `8000` for the private network. The backend computer's LAN IP can change, so check it again if the ESP32 suddenly cannot connect.

## 3. Exact telemetry endpoint

- Method: `POST`
- Path: `/api/telemetry`
- Full URL: `http://<BACKEND_PC_IP>:8000/api/telemetry`
- Header: `Content-Type: application/json`
- Successful status: `201 Created`

### Required JSON fields

| Field | JSON type | Backend constraint | Meaning |
|---|---|---|---|
| `device_id` | string | 1–64 characters | Unique identifier for this ESP32 |
| `soil_moisture` | number | 0–100 | Soil moisture percentage |
| `temperature` | number | -40 to 80 | Temperature in °C |
| `air_humidity` | number | 0–100 | Air humidity percentage |
| `prediction` | string | `irrigate` or `no_irrigate` | TinyML decision |
| `pump_status` | string | `on` or `off` | Pump state reported by the ESP32 |

`timestamp` is optional. If supplied, it must be a datetime that Pydantic can parse (prefer an ISO 8601 UTC timestamp, for example `2026-11-23T14:05:00Z`). If the ESP32 does not have a reliable clock/NTP time, omit `timestamp`.

The backend sets `received_at` itself when the request arrives. **Do not send `received_at` from the ESP32.** The backend also generates the record `id`.

### Example request body

```json
{
  "device_id": "esp32-gr2-01",
  "soil_moisture": 32.5,
  "temperature": 24.1,
  "air_humidity": 58.0,
  "prediction": "irrigate",
  "pump_status": "on"
}
```

A second example with an optional timestamp:

```json
{
  "device_id": "esp32-gr2-01",
  "soil_moisture": 65.0,
  "temperature": 26.0,
  "air_humidity": 45.0,
  "prediction": "no_irrigate",
  "pump_status": "off",
  "timestamp": "2026-11-23T14:05:00Z"
}
```

The example values are illustrative. Send the actual sensor readings and actual local TinyML/pump state.

## 4. What a successful response looks like

The backend returns `201 Created` and a JSON representation of the stored measurement. For example:

```json
{
  "device_id": "esp32-gr2-01",
  "soil_moisture": 32.5,
  "temperature": 24.1,
  "air_humidity": 58.0,
  "prediction": "irrigate",
  "pump_status": "on",
  "id": 2,
  "timestamp": null,
  "received_at": "2026-11-23T13:38:37.106620"
}
```

The returned `id` and `received_at` are assigned by the backend. The example ID and date are from a test and will differ in real use.

## 5. Arduino ESP32 HTTP client outline

Use the ESP32 Arduino core's Wi-Fi and HTTP client libraries (`WiFi.h` and `HTTPClient.h`). The following is an outline to show the request structure; adapt the Wi-Fi credentials, sensor variables, device ID, and timing to the actual firmware. It is not a complete project sketch and does not define sensor wiring or TinyML logic.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Replace with the backend computer's current LAN IPv4 address.
const char* SERVER_URL = "http://192.168.1.14:8000/api/telemetry";
const char* DEVICE_ID = "esp32-gr2-01";

void connectToWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  // Add an appropriate timeout/retry strategy for your firmware.
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Waiting for Wi-Fi...");
  }

  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void sendTelemetry(float soilMoisture,
                   float temperature,
                   float airHumidity,
                   const char* prediction,
                   const char* pumpStatus) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi unavailable; telemetry not sent.");
    return;
  }

  WiFiClient client;
  HTTPClient http;

  if (!http.begin(client, SERVER_URL)) {
    Serial.println("Could not initialize HTTP connection.");
    return;
  }

  http.setTimeout(5000);
  http.addHeader("Content-Type", "application/json");

  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"soil_moisture\":" + String(soilMoisture, 1) + ",";
  payload += "\"temperature\":" + String(temperature, 1) + ",";
  payload += "\"air_humidity\":" + String(airHumidity, 1) + ",";
  payload += "\"prediction\":\"" + String(prediction) + "\",";
  payload += "\"pump_status\":\"" + String(pumpStatus) + "\"";
  payload += "}";

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.print("HTTP status: ");
    Serial.println(httpCode);
    Serial.print("Backend response: ");
    Serial.println(http.getString());
  } else {
    Serial.print("HTTP request failed: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
}
```

Important implementation notes:

- Call `sendTelemetry(...)` after obtaining the sensor values, computing the TinyML prediction, and updating the local pump control/state.
- Pass only the exact prediction strings `"irrigate"` or `"no_irrigate"`.
- Pass only the exact pump strings `"on"` or `"off"`.
- Ensure sensor values are numeric and within the backend's accepted ranges. Check sensor calibration and units; do not fake or clamp values merely to make the API accept them.
- Do not block local irrigation while waiting for the HTTP request. Use reasonable timeouts and a retry/reconnect strategy that does not interfere with the control loop.
- Avoid sending telemetry in a tight loop. Choose a reporting interval appropriate to the project and coordinate it with the team.
- Do not commit Wi-Fi credentials to GitHub. Keep them in a local, ignored configuration file or enter them outside the committed source code.
- The sample uses a placeholder IP address. Replace it with the backend computer's actual address.

## 6. Useful backend endpoints

The ESP32's main required integration is `POST /api/telemetry`. These GET endpoints are primarily useful for the dashboard and manual checks:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Check that the backend responds |
| `GET` | `/api/telemetry/latest?device_id=esp32-gr2-01` | Latest measurement for one device |
| `GET` | `/api/telemetry?device_id=esp32-gr2-01` | Measurement history for one device |
| `GET` | `/api/telemetry/stats?device_id=esp32-gr2-01&hours=24` | Statistics for the last 24 hours |
| `GET` | `/api/pump/status?device_id=esp32-gr2-01` | Latest pump state and prediction reported by that device |

`device_id` can be omitted from the GET telemetry/history/statistics endpoints to query across devices. The pump status endpoint reports the last state received by the backend; it is not a live electrical measurement of the pump.

## 7. Troubleshooting

| Symptom | What to check |
|---|---|
| Connection refused / cannot connect | Is Uvicorn running? Is it bound to `0.0.0.0`? Is the IP and port correct? Does Windows Firewall allow port 8000? |
| ESP32 cannot reach the PC | Are both on the same reachable Wi-Fi? Is guest/client isolation enabled? Did the PC's IP change? |
| HTTP `201` | Measurement was accepted and stored. |
| HTTP `422` | Request body is malformed JSON, a required field is missing, a field has the wrong type/range, or an enum value is incorrect. Read the response body for the field and reason. |
| HTTP `404` | Check the URL/path. For GET `/latest`, 404 also means no measurement matched the requested device/filter. |
| HTTP `500` | Check the backend terminal for the server-side exception and report it to the backend developer. |
| Request times out | Check Wi-Fi signal, server availability, firewall and timeout settings. Do not stop local pump control because telemetry failed. |

## 8. Recommended integration test sequence

1. Start FastAPI on the backend computer.
2. From another device on the same Wi-Fi, open `http://<BACKEND_PC_IP>:8000/health` and confirm `{"status":"ok"}`.
3. Confirm the ESP32 joins the same Wi-Fi and print its IP address to Serial Monitor.
4. Send one test measurement using the exact JSON contract above.
5. Confirm that Serial Monitor reports HTTP `201` and shows the backend response.
6. Open `http://<BACKEND_PC_IP>:8000/docs` on the backend computer and call `GET /api/telemetry/latest` with the ESP32's `device_id`.
7. Confirm the returned readings match the ESP32's Serial Monitor output.
8. Temporarily make the backend unavailable and verify that local sensing, TinyML inference and pump control continue. Restore the backend and verify telemetry can be sent again.

## 9. Ready-to-use prompt for an AI coding assistant

Copy the following prompt into your AI assistant and provide your existing ESP32 firmware, sensor definitions, and TinyML output details. Do not ask the AI to invent missing pin assignments or sensor details.

> I am implementing the ESP32 firmware for a team smart-irrigation project. The backend already exists and must not be redesigned. The ESP32 must read the sensors, run the TinyML decision locally, control the pump locally, and then send telemetry to a FastAPI backend over Wi-Fi using HTTP POST with a JSON body. Do not use MQTT.
>
> Backend endpoint: `POST http://<BACKEND_PC_IP>:8000/api/telemetry` (replace the placeholder with the backend computer's LAN IPv4 address). Header: `Content-Type: application/json`.
>
> The JSON body must contain these exact fields:
> - `device_id`: string, 1–64 characters, unique per ESP32.
> - `soil_moisture`: number from 0 to 100, in percent.
> - `temperature`: number from -40 to 80, in degrees Celsius.
> - `air_humidity`: number from 0 to 100, in percent.
> - `prediction`: exactly `irrigate` or `no_irrigate`.
> - `pump_status`: exactly `on` or `off`.
> - `timestamp`: optional ISO 8601 datetime. Omit it if the ESP32 has no reliable UTC time. Do not send `received_at`; the backend creates it.
>
> A successful request returns HTTP `201 Created`. Invalid or missing fields return HTTP `422`. The backend also provides `GET /health` for a connectivity check.
>
> Use the ESP32 Arduino environment and its `WiFi.h` and `HTTPClient.h` libraries unless the existing project already uses an appropriate alternative. Integrate the HTTP sender with my actual existing sensor variables, TinyML output and pump state. First inspect the code I provide and identify the real variable names and data types. Ask me for missing pin mappings, sensor details, or TinyML output mappings instead of inventing them.
>
> Important architecture requirements:
> 1. TinyML inference and pump control remain local on the ESP32.
> 2. HTTP failures, Wi-Fi loss or backend unavailability must never stop local irrigation control.
> 3. Use a reasonable HTTP timeout and a reconnect/retry approach that does not block the control loop for too long.
> 4. Do not flood the backend with requests; use a deliberate telemetry interval.
> 5. Print connection state, HTTP status code and response/error details to Serial Monitor for debugging.
> 6. Keep Wi-Fi credentials out of committed GitHub source code.
> 7. Return the modified code and explain exactly where the telemetry function is called and how to test it against the backend.

## 10. Current integration status

The backend contract and endpoints have been exercised through Swagger with sample JSON, including successful insert/retrieval and validation checks. A real ESP32-to-backend Wi-Fi test has not yet been confirmed. Complete the sequence above with the physical board before declaring hardware integration finished.
