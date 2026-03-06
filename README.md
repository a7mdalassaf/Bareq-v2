# Bareq v2 — Smart Building Energy Management

**Turn building electricity into actionable intelligence.**

Bareq gives building operators and owners clear visibility and control over energy consumption: apartment-level monitoring, anomaly detection, peak load alerts, and remote control — built for modern smart buildings.

## Features

### Energy Monitoring
- **Apartment-level consumption tracking** — Real-time and historical data
- **Peak load detection** — Identify consumption patterns and optimize schedules
- **Anomaly alerts** — Detect spikes, unusual patterns, and potential issues
- **Cost analysis** — Track spending by apartment, floor, or building
- **Comparative reports** — Benchmark consumption across units

### Building Control
- **Remote circuit control** — Toggle, schedule, and automate smart breakers
- **Access management** — Smart lock integration (TTLock)
- **Device automation** — Rules-based control via Tuya integration
- **LED indicators** — Visual status for active systems

### Platform Features
- **Multi-building support** — Manage entire portfolios from one dashboard
- **Role-based access** — Secure, audit-friendly permissions
- **Background jobs** — Automated sync, alerts, and reporting
- **RESTful API** — Integrate with external systems

## Tech Stack

- **Backend:** Python 3.10+, Flask, SQLAlchemy
- **Database:** SQLite (production-ready for pilot scale)
- **Integrations:** Tuya Cloud API, TTLock Cloud API
- **Deployment:** Gunicorn, Nginx, systemd

## Project Structure

```
bareq-v2/
├── web_app.py              # Main Flask application
├── models.py               # Database models (User, Guest, LockDeviceMapping, etc.)
├── jobs.py                 # Background task scheduler
├── requirements.txt        # Python dependencies
│
├── routes/                 # API route blueprints
│   ├── admin.py            # Admin dashboard
│   └── locks.py            # Lock management
│
├── services/               # Business logic layer
│   ├── credential_service.py
│   ├── auth_service.py
│   ├── audit_service.py
│   └── ttlock_account_manager.py
│
├── templates/              # Jinja2 HTML templates
│   ├── index.html          # Main dashboard
│   ├── admin/              # Admin UI
│   └── auth/               # Login pages
│
├── public/                 # Static frontend (landing page)
│   ├── index.html          # Marketing site
│   ├── dashboard.html      # Energy dashboard preview
│   └── assets/
│
├── tuya_adapter.py         # Tuya device control & energy monitoring
├── ttlock_adapter.py       # TTLock smart lock integration
└── docs/                   # Architecture & API documentation
```

## Installation

### Prerequisites
- Python 3.10+
- pip
- virtualenv

### Setup

1. Clone the repository:
```bash
git clone https://github.com/a7mdalassaf/Bareq-v2.git
cd Bareq-v2
```

2. Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

5. Initialize database:
```bash
python web_app.py
```

6. Run development server:
```bash
flask run --port 5000
```

## Deployment

See [docs/deployment.md](docs/deployment.md) for production setup with Gunicorn + Nginx.

## Roadmap

### Phase 1: Energy Monitoring Core (Current)
- [x] Tuya device integration
- [x] Basic consumption tracking
- [ ] Apartment-level energy dashboard
- [ ] Historical data aggregation
- [ ] Cost calculation module

### Phase 2: Analytics & Alerts
- [ ] Peak load detection algorithms
- [ ] Anomaly detection (ML-based)
- [ ] Automated alert system
- [ ] Weekly/monthly reports

### Phase 3: Multi-Building Scale
- [ ] Building portfolio dashboard
- [ ] Comparative analytics
- [ ] Export to CSV/PDF
- [ ] SSO integration

## API Integrations

### Tuya Cloud API
Used for:
- Smart plug power monitoring
- Smart breaker control
- Device status tracking

### TTLock Cloud API
Used for:
- Smart lock management
- Guest access control
- Passcode automation

## Security

- Role-based access control (RBAC)
- Encrypted credential storage
- Audit logging for all actions
- Session-based authentication

## Contributing

This is a private project. For questions or support, contact ahmad@bareq.site.

## License

Proprietary — All rights reserved.

---

**Bareq** — Smart building energy intelligence for the modern world.
