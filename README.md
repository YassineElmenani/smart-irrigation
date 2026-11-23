# Smart Irrigation — TinyML and IoT

Academic project for the Master's programme in Computer Engineering and Embedded Systems, 2026–2027.

The project aims to build an intelligent irrigation system using an ESP32, sensors, a TinyML model, a backend API, and a web dashboard.

## 1. System architecture

The ESP32 is responsible for local operation:

1. Read the sensors.
2. Run the TinyML prediction locally on the ESP32.
3. Control the pump locally according to the irrigation logic.
4. Send measurement and status data to the backend over Wi-Fi using HTTP and JSON.

The backend is for supervision. It receives and validates measurements, stores them in SQLite, and provides API endpoints for the dashboard. The irrigation process must continue locally if Wi-Fi or the backend is unavailable.

```text
Sensors ──> ESP32 ──> TinyML decision ──> Local pump control
                  │
                  └── Wi-Fi / HTTP POST (JSON)
                              │
                              v
                    FastAPI backend
                              │
                         SQLite database
                              │
                         HTTP GET API
                              │
                              v
                         Dashboard
```

**Communication stack:** Wi-Fi (IEEE 802.11) provides wireless network access; IP addresses devices; TCP transports the connection; HTTP defines the request/response; JSON is the measurement data format. This project currently uses HTTP, not MQTT, for ESP32-to-backend telemetry.

## 2. Repository structure

```text
smart-irrigation/
├── backend/       # FastAPI API, database, models, schemas, services, tests
├── esp32/         # ESP32 firmware and Arduino project
├── tinyml/        # Dataset, training code, and TinyML model assets
├── frontend/      # Web dashboard (HTML, CSS, JavaScript)
├── docs/          # Architecture, API, and integration documentation
├── .gitignore
└── README.md
```

Git does not track empty folders. Add a source file, README, or `.gitkeep` file inside a new folder so it appears in GitHub.

## 3. Team responsibilities

| Workstream | Suggested branch | Main responsibility |
|---|---|---|
| Backend (future improvements/tests) | `feature/backend-tests` | FastAPI, SQLite, validation, API, backend tests |
| ESP32 firmware | `feature/esp32-firmware` | Sensor acquisition, local pump control, Wi-Fi and HTTP client |
| TinyML | `feature/tinyml-model` | Dataset preparation, training, Decision Tree and model conversion |
| Dashboard | `feature/dashboard-ui` | Display measurements, statistics, pump state and history |

Coordinate changes if more than one person is working in the same folder. The branch names above are recommendations; agree on the final names as a team.

## 4. Git workflow for every teammate

### First time: clone the shared repository

```powershell
git clone https://github.com/YassineElmenani/smart-irrigation.git
cd smart-irrigation
```

### Before starting a task: update `main` and create your own branch

```powershell
git switch main
git pull origin main
git switch -c feature/your-work-name
```

Use a descriptive branch name, for example `feature/esp32-firmware` or `feature/tinyml-model`.

### Work only in your assigned folder

Create your folder if it does not exist, then add your source files there. Do not commit virtual environments, local databases, passwords, Wi-Fi credentials, generated Python cache files, or temporary test files.

### Commit and push your branch

```powershell
git status
git add your-folder/
git commit -m "feat: describe your change"
git push -u origin feature/your-work-name
```

Replace `your-folder/` and `feature/your-work-name` with your own folder and branch.

### Share your work

Open a Pull Request on GitHub from your feature branch into `main`. Describe what changed and how you tested it. Do not push directly to `main`; review and merge contributions through Pull Requests.

Before starting another task, update your local `main` again. If you already have an existing feature branch, merge or rebase the latest `main` into it according to the team's agreed workflow.

## 5. Backend quick start

The backend is in `backend/`. On Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open the interactive API documentation at:

- Swagger UI: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/health`

Run the command from the `backend/` directory so the relative SQLite database path is created there. Each developer should use their own local database; do not commit the `.db` file.

For ESP32 access over the same local Wi-Fi network, use the backend computer's LAN IPv4 address instead of `127.0.0.1`. See [docs/ESP32_BACKEND_INTEGRATION_GUIDE.md](docs/ESP32_BACKEND_INTEGRATION_GUIDE.md).

## 6. Current backend API contract

### ESP32 sends telemetry

`POST /api/telemetry` — send a JSON body with these required fields:

| Field | Type / accepted values |
|---|---|
| `device_id` | String, 1–64 characters |
| `soil_moisture` | Number, 0–100 (%) |
| `temperature` | Number, -40 to 80 (°C) |
| `air_humidity` | Number, 0–100 (%) |
| `prediction` | Exactly `irrigate` or `no_irrigate` |
| `pump_status` | Exactly `on` or `off` |
| `timestamp` | Optional ISO 8601 datetime from the ESP32 |

Example:

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

A successful request returns `201 Created`. The backend generates `id` and `received_at`. The ESP32 does not need to send `received_at`; `timestamp` can be omitted if the ESP32 does not have a reliable clock.

### Dashboard and monitoring endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/telemetry` | List history; optional `device_id`, `since`, `skip`, `limit` filters |
| `GET` | `/api/telemetry/latest` | Latest measurement; optional `device_id` filter |
| `GET` | `/api/telemetry/stats` | Aggregates; optional `device_id`, `hours` (1–720) |
| `GET` | `/api/pump/status` | Latest reported pump status and prediction; optional `device_id` |
| `GET` | `/health` | Basic application liveness response |

The `device_id` filter can be omitted to query measurements across all devices. `/api/pump/status` reports the latest state received by the backend; it does not directly read the physical pump.

See [docs/ESP32_BACKEND_INTEGRATION_GUIDE.md](docs/ESP32_BACKEND_INTEGRATION_GUIDE.md) for the ESP32-specific instructions.

## 7. Important project rules

- Keep TinyML inference and pump control local to the ESP32.
- Treat the backend as a monitoring and data-storage service, not as the irrigation controller.
- Keep the JSON field names and accepted values in sync between the ESP32, TinyML and backend teams.
- Use a unique `device_id` for each ESP32.
- Do not commit `.venv/`, `__pycache__/`, `.pyc`, local `.db` files, `.env` files, Wi-Fi passwords, or API secrets.
- The current local HTTP setup is intended for development on a trusted local network. Do not expose this unauthenticated development API directly to the public internet.

## 8. Project status

The backend application, telemetry routes, pump status route, data validation, and Swagger-based endpoint checks have been implemented. Testing with a physical ESP32 over the team's Wi-Fi network, automated backend tests, and dashboard implementation/integration remain project work.
