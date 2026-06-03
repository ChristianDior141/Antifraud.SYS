# System Architecture

## Overview

The KYC/AML Risk Assessment Platform follows a **three-tier architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT TIER (Browser)                    │
│   React 18 + TypeScript + Tailwind CSS + Redux Toolkit       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS / REST API
┌──────────────────────────▼──────────────────────────────────┐
│                  APPLICATION TIER (FastAPI)                   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │  Auth API  │  │ KYC/Client │  │  AML Monitor Engine  │   │
│  │  JWT/RBAC  │  │    API     │  │  Rule-based alerts   │   │
│  └────────────┘  └────────────┘  └──────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │  Risk      │  │  Document  │  │  Analytics API       │   │
│  │  Engine    │  │  Service   │  │  Dashboard metrics   │   │
│  └────────────┘  └────────────┘  └──────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ SQLAlchemy async
┌──────────────────────────▼──────────────────────────────────┐
│                     DATA TIER                                 │
│         PostgreSQL 15          Redis 7 (cache/queue)         │
└─────────────────────────────────────────────────────────────┘
```

## Security Architecture

```
Request → Rate Limiter → CORS → JWT Validation → RBAC → Handler
                                      ↓
                               Audit Log (all writes)
```

### Authentication Flow

1. Client POSTs `/auth/login` with credentials
2. Server verifies bcrypt hash
3. Returns JWT access token (8h) + refresh token (7d)
4. Client stores tokens in localStorage
5. Every API request includes `Authorization: Bearer <token>`
6. Server validates JWT on every protected endpoint

### RBAC Matrix

| Endpoint | Client | Analyst | Compliance | Admin |
|----------|--------|---------|------------|-------|
| Own profile | ✓ | — | — | ✓ |
| Upload docs | ✓ | — | — | ✓ |
| View all clients | — | ✓ | ✓ | ✓ |
| Review/approve | — | — | ✓ | ✓ |
| AML alerts | — | ✓ | ✓ | ✓ |
| User management | — | — | — | ✓ |
| Audit logs | — | — | — | ✓ |

## Risk Scoring Algorithm

```
Total Score = Personal(30%) + Geographic(25%) + Transaction(25%)
            + Behavioral(10%) + Document(10%)

Risk Level:
  0–30   → LOW
  31–60  → MEDIUM
  61–80  → HIGH
  81–100 → CRITICAL
```

### Personal Risk Factors
- PEP status: +40 points
- Sanctions hit: +50 points
- Missing profile fields: +4 per field (max +20)

### Geographic Risk Factors
- High-risk nationality: +35 points
- High-risk residence: +35 points

### Transaction Risk Factors
- Total volume > $100K: +20 points
- Transactions > $10K each: +5 per (max +20)
- >10 transactions in 24h: +25 points
- Previously flagged transactions: +10 per (max +30)

### Behavioral Risk Factors
- Recent 30-day volume > 3× declared expected monthly volume: +20 points
- Activity from > 3 distinct devices: +15 points
- Activity from > 5 distinct IP addresses: +15 points
- Use of transaction types not declared at onboarding: +10 points

> High-risk jurisdictions are defined in a single shared module
> (`app/services/high_risk_countries.py`) used by both the risk engine and the
> AML monitor, so the two stay in sync.

## AML Rules Engine

Each transaction is evaluated against all rules sequentially (an async DB
session cannot run concurrent queries). Matching rules raise an `AMLAlert`
and flag the transaction; alert text is rendered from shared templates.

| Rule | Trigger | Severity |
|------|---------|----------|
| STRUCTURING | 3+ transactions $8K–$10K in 24h | HIGH |
| LARGE_TRANSACTION | Single tx ≥ $50,000 (≥ $100K → CRITICAL) | HIGH/CRITICAL |
| HIGH_RISK_JURISDICTION | Transfer to high-risk country | HIGH |
| VELOCITY_CHECK | >10 transactions in 24h | MEDIUM |
| RAPID_MOVEMENT | ≥5 tx in 2h with both inflow and outflow (layering) | HIGH |
| PEP_TRANSACTION | PEP client + transaction ≥ $10,000 | HIGH |
| SANCTIONS_HIT | Any transaction by a sanctioned client | CRITICAL |

## Database Schema (ERD Summary)

```
users ──< client_profiles ──< documents
                         ──< kyc_forms
                         ──< risk_scores
                         ──< transactions ──< aml_alerts ──1 incident_tickets
                         ──< reviews
users ──< audit_logs
users ──< notifications

detection_rules ──< rule_tuning_history
detection_rules ──< incident_tickets
detection_rules ──< false_positives

incident_tickets ──< incident_comments
                 ──< incident_assignments
                 ──< risk_assessments
                 ──1 false_positives
```

## Incident Management & False Positive Analysis

Every `AMLAlert` is bridged to exactly one `IncidentTicket` (created in the
transaction flow and during seeding). Analysts investigate the ticket, record
`RiskAssessment`s, and classify it as a **real incident** or a **false
positive**. False positives capture a root cause and the rule responsible,
which feeds detection-rule effectiveness scoring and tuning.

```
Alert ─▶ Ticket(NEW) ─▶ Assigned ─▶ In Progress ─▶ Risk Assessment ─▶ Classify
                                                                        │
                                   Real Incident ◀────────────┴────────▶ False Positive
                                        │                                   │
                                   Close + record                     Record root cause,
                                                                      rule responsible,
                                                                      suggested tuning
                                                                            │
                                                              Rule effectiveness ▼
                                                              recompute → tuning history
```

**Roles (mapped onto the existing 4):** Analyst = `RISK_ANALYST`,
Senior Analyst = `COMPLIANCE_OFFICER`, Manager + Administrator = `ADMIN`.
Analysts investigate/assess/classify; admins tune detection rules.

**Rule effectiveness:** `fp_rate = false_positives / (false_positives +
confirmed_incidents)`; `effectiveness = 100 − fp_rate`. Computed on demand from
ticket outcomes. The dashboards expose incident metrics (totals, open/closed,
MTTR = mean(closed−created), MTTA = mean(first_assigned−created)), false-positive
metrics (rate, by-rule, by-source, monthly trend) and risk-level distribution.

New entities: `detection_rules`, `rule_tuning_history`, `incident_tickets`,
`incident_comments`, `incident_assignments`, `risk_assessments`,
`false_positives`.

## API Structure

```
/api/v1/
  auth/
    POST /register
    POST /login
    POST /refresh
    GET  /me
    PUT  /me
  clients/
    POST /profile
    GET  /profile/me
    PUT  /profile/me
    GET  /                   (staff only)
    GET  /{id}               (staff only)
    POST /{id}/risk-score    (staff only)
  documents/
    POST /upload
    GET  /my
    GET  /client/{id}        (staff only)
    PUT  /{id}/review        (staff only)
  transactions/
    POST /
    GET  /my
    GET  /client/{id}        (staff only)
    GET  /stats/summary      (staff only)
  aml/
    GET  /alerts             (staff only)
    GET  /alerts/{id}        (staff only)
    PUT  /alerts/{id}        (compliance only)
    GET  /stats              (staff only)
  reviews/
    POST /                   (compliance only)
    PUT  /{id}/decide        (compliance only)
    GET  /pending            (compliance only)
  analytics/
    GET  /dashboard          (staff only)
    GET  /monthly-trend      (staff only)
    GET  /incidents          (staff only)   # totals, MTTR, MTTA, by status
    GET  /false-positives    (staff only)   # rate, by rule, by source, trend
    GET  /risk               (staff only)   # incident risk distribution
  incidents/
    GET  /                   (staff only)
    GET  /{id}               (staff only)
    GET  /meta/analysts      (staff only)
    POST /{id}/assign        (staff only)
    PUT  /{id}/status        (staff only)
    POST /{id}/escalate      (staff only)
    POST /{id}/comments      (staff only)
    POST /{id}/risk-assessment (staff only)
    POST /{id}/classify      (staff only)
  detection-rules/
    GET  /                   (staff only)
    GET  /{id}               (staff only)
    GET  /{id}/false-positives (staff only)
    GET  /{id}/history       (staff only)
    POST /{id}/tune          (admin only)
  admin/
    GET  /users              (admin only)
    POST /users              (admin only)
    PUT  /users/{id}         (admin only)
    DELETE /users/{id}       (admin only)
    GET  /audit-logs         (admin only)
    GET  /stats              (admin only)
```
