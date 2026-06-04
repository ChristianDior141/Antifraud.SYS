# KYC/AML Client Risk Assessment Platform

**Dissertation Project — IT Systems for Business**

A production-quality web application that automates customer onboarding, KYC verification,
AML compliance monitoring, and client risk scoring for financial institutions.

---

## Quick Start (Docker)

```bash
# 1. Clone and enter directory
cd kyc-aml-platform

# 2. Start all services
docker-compose up -d

# 3. Seed demo data
docker-compose exec backend python seed_data.py

# 4. Open the application
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/docs
# ReDoc:     http://localhost:8000/redoc
```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@kyc-platform.com | Admin123!@# |
| Compliance Officer | compliance1@kyc-platform.com | Admin123!@# |
| Risk Analyst | analyst1@kyc-platform.com | Admin123!@# |
| Client | (register new) | — |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS, Redux Toolkit |
| Backend | FastAPI (Python 3.11), SQLAlchemy 2.0 async |
| Database | PostgreSQL 15 |
| Cache/Queue | Redis 7 |
| Auth | JWT (access + refresh tokens) |
| Container | Docker + Docker Compose |
| API Docs | OpenAPI / Swagger |

---

## Project Structure

```
kyc-aml-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST endpoints (auth, clients, docs, aml, …)
│   │   ├── core/               # Config, security, DB, dependencies
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── services/           # Risk engine, AML monitor
│   ├── tests/                  # Pytest test suite
│   ├── seed_data.py            # Demo data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/         # Layout, shared UI components
│       ├── pages/              # Page components per role
│       ├── services/           # Axios API client
│       ├── store/              # Redux state management
│       ├── types/              # TypeScript interfaces
│       └── utils/              # Formatters, helpers
├── database/
│   ├── schema.sql              # Full PostgreSQL DDL
│   └── init.sql                # Docker init script
├── docs/
│   ├── ARCHITECTURE.md             # System design documentation
│   ├── SECURITY_COMPLIANCE_AUDIT.md# GDPR / ISO 27001 audit + roadmap
│   ├── RoPA.md                     # Records of Processing Activities (Art.30)
│   └── INCIDENT_RESPONSE.md        # Breach notification & IR runbook
├── .github/workflows/ci.yml        # Tests, build, SAST, dep & secret scanning
└── docker-compose.yml
```

---

## Features

### Client Portal
- Self-registration and login
- Multi-step KYC questionnaire (4 sections, 30+ fields)
- Document upload (passport, ID, proof of address)
- Real-time verification status tracking
- Transaction history

### Risk Scoring Engine
- Weighted composite score (0–100)
- Personal risk: PEP status, sanctions, completeness
- Geographic risk: high-risk country detection (shared 27-country list)
- Transaction risk: velocity, structuring, large amounts
- Behavioral risk: volume deviation, device/IP spread, undeclared transaction types
- Document risk factors

### AML Monitoring
- Real-time transaction screening
- Rule-based alert generation (7 rules: structuring, large transaction,
  high-risk jurisdiction, velocity, rapid movement, PEP, sanctions)
- Alert investigation workflow (Open → Investigating → Resolved/SAR)
- Jurisdiction risk screening

### Compliance Dashboard
- Client verification queue
- Risk distribution visualization
- AML alert management
- Document approval/rejection workflow

### Admin Panel
- User and role management
- Comprehensive audit trail
- System statistics

### User Identity & Device Intelligence
- Required, unique, validated account phone number (E.164) at registration
- Device tracking per login (OS/browser/type/screen), trusted devices, device history
- Session, login history and IP history tracking; new-device / new-IP detection
- Automatic security events: new device, new IP, multiple failed logins, rapid IP change
- Tamper-evident audit log enriched with username/role/device id
- Admin **Audit Dashboard**: full activity/devices/sessions/login/security views with
  search, filters, date range and export to **CSV / Excel / PDF**
- Self-service **My Activity** page (own devices, logins, actions) — users cannot see others'

### Account Security (Enterprise)
- Multi-factor authentication (TOTP) with one-time backup codes
- Account lockout after repeated failed logins; rate limiting on auth endpoints
- JWT revocation / real logout (token denylist) and self-service password reset
- PII encrypted at rest (Fernet) and encrypted document storage with access-controlled download
- See `docs/SECURITY_COMPLIANCE_AUDIT.md` for the full controls list

### Privacy & GDPR Compliance
- Data-subject self-service: export personal data (Art.15/20), manage consents
  (Art.7), submit access/rectification/erasure/restriction requests (Art.16–18)
- Admin/DPO console: process DSARs (erasure → anonymization, with AML legal hold),
  run retention purge (Art.5(1)(e)), verify audit-log integrity
- Tamper-evident audit log (SHA-256 hash chain) and logging of staff access to PII
- See `docs/SECURITY_COMPLIANCE_AUDIT.md` for the full GDPR / ISO 27001 audit and roadmap

### Incident Management & False Positive Analysis
- Every AML alert auto-creates an incident ticket (lifecycle: New → Assigned →
  In Progress → Under Review → Escalated → Closed)
- Risk assessment per incident (business/financial/technical impact, confidence,
  recommended action) with full history
- Classification as **Real Incident** or **False Positive** (with root cause,
  reason, responsible rule, suggested tuning)
- Detection-rule tuning: per-rule total alerts / confirmed / false positives /
  FP rate / effectiveness score, suggested improvements, version history
- Executive dashboards: incident metrics (MTTR, MTTA, open/closed), false-positive
  metrics (rate, by rule, by source, monthly trend) and risk distribution
- Roles map onto the existing four: Analyst = Risk Analyst, Senior Analyst =
  Compliance Officer, Manager + Administrator = Admin

---

## Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Set environment variables
copy .env.example .env
# Edit .env with your PostgreSQL credentials

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                    # Starts on http://localhost:3000
```

### Run Tests
```bash
cd backend
pip install aiosqlite
pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| POSTGRES_SERVER | localhost | DB host |
| POSTGRES_USER | postgres | DB user |
| POSTGRES_PASSWORD | postgres | DB password |
| POSTGRES_DB | kyc_aml_db | Database name |
| SECRET_KEY | (random) | JWT signing key |
| ACCESS_TOKEN_EXPIRE_MINUTES | 480 | Token lifetime |
| REDIS_URL | redis://localhost:6379 | Redis connection |

---

## API Documentation

After starting the backend, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All 30+ endpoints are documented with request/response schemas.

---

## Architecture Decisions

1. **FastAPI over Django/Flask** — native async support, auto OpenAPI generation, Pydantic validation
2. **Async SQLAlchemy 2.0** — non-blocking DB queries for high-throughput compliance workloads
3. **Redux Toolkit** — predictable state management; auth state persisted to localStorage
4. **Rule-based AML engine** — interpretable, auditable alerts vs. black-box ML (regulatory requirement)
5. **RBAC at dependency level** — roles enforced via FastAPI `Depends()` rather than middleware, enabling fine-grained control per endpoint
6. **Composite risk score** — weighted average of 5 independent dimensions allows compliance officers to understand exactly why a client scored high

---

*Developed as a graduation dissertation project for IT Systems for Business.*
