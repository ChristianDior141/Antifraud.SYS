-- =============================================================
-- KYC/AML Platform — Full Database Schema
-- PostgreSQL 15+
-- Generated from SQLAlchemy ORM models
-- =============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -------------------------
-- ENUMS
-- -------------------------
CREATE TYPE user_role AS ENUM ('client', 'compliance_officer', 'risk_analyst', 'admin');
CREATE TYPE kyc_status AS ENUM ('not_started','in_progress','pending_review','approved','rejected','requires_update');
CREATE TYPE risk_level AS ENUM ('low','medium','high','critical');
CREATE TYPE document_type AS ENUM ('passport','id_card','driver_license','proof_of_address','bank_statement','tax_document','other');
CREATE TYPE document_status AS ENUM ('pending','under_review','approved','rejected','expired');
CREATE TYPE transaction_type AS ENUM ('deposit','withdrawal','transfer','payment','exchange');
CREATE TYPE transaction_status AS ENUM ('pending','completed','failed','flagged','blocked');
CREATE TYPE alert_type AS ENUM ('structuring','rapid_movement','high_risk_jurisdiction','unusual_frequency','large_cash','velocity_check','layering','pep_transaction','sanctions_hit');
CREATE TYPE alert_severity AS ENUM ('low','medium','high','critical');
CREATE TYPE alert_status AS ENUM ('open','under_investigation','escalated','resolved','false_positive','sar_filed');
CREATE TYPE review_decision AS ENUM ('approved','rejected','request_more_info','escalated');

-- -------------------------
-- USERS
-- -------------------------
CREATE TABLE users (
    id                  SERIAL PRIMARY KEY,
    email               VARCHAR(255) UNIQUE NOT NULL,
    hashed_password     VARCHAR(255) NOT NULL,
    full_name           VARCHAR(255) NOT NULL,
    role                user_role NOT NULL DEFAULT 'client',
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    mfa_enabled         BOOLEAN DEFAULT FALSE,
    mfa_secret          TEXT,                 -- encrypted at rest (Fernet)
    last_login          TIMESTAMPTZ,
    login_attempts      INTEGER DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- -------------------------
-- CLIENT PROFILES
-- -------------------------
CREATE TABLE client_profiles (
    id                                      SERIAL PRIMARY KEY,
    user_id                                 INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Personal
    first_name                              VARCHAR(100) NOT NULL,
    last_name                               VARCHAR(100) NOT NULL,
    middle_name                             VARCHAR(100),
    date_of_birth                           DATE,
    gender                                  VARCHAR(20),
    nationality                             VARCHAR(100),
    country_of_birth                        VARCHAR(100),
    country_of_residence                    VARCHAR(100),
    -- Contact
    phone_number                            TEXT,  -- encrypted at rest (Fernet)
    address_line1                           VARCHAR(255),
    address_line2                           VARCHAR(255),
    city                                    VARCHAR(100),
    state_province                          VARCHAR(100),
    postal_code                             VARCHAR(20),
    country                                 VARCHAR(100),
    -- Identity
    id_type                                 VARCHAR(50),
    id_number                               TEXT,  -- encrypted at rest (Fernet)
    id_expiry_date                          DATE,
    id_issuing_country                      VARCHAR(100),
    -- Financial
    occupation                              VARCHAR(255),
    employer_name                           VARCHAR(255),
    annual_income_range                     VARCHAR(50),
    source_of_funds                         TEXT,  -- encrypted at rest (Fernet)
    source_of_wealth                        TEXT,  -- encrypted at rest (Fernet)
    expected_monthly_transaction_volume     FLOAT,
    expected_transaction_types              JSONB,
    -- AML Flags
    is_pep                                  BOOLEAN DEFAULT FALSE,
    pep_details                             TEXT,  -- encrypted at rest (Fernet)
    is_sanctioned                           BOOLEAN DEFAULT FALSE,
    is_high_risk_country                    BOOLEAN DEFAULT FALSE,
    -- Status
    kyc_status                              kyc_status DEFAULT 'not_started',
    risk_level                              risk_level DEFAULT 'low',
    risk_score                              FLOAT DEFAULT 0.0,
    -- Meta
    ip_address                              VARCHAR(45),
    device_fingerprint                      VARCHAR(255),
    created_at                              TIMESTAMPTZ DEFAULT NOW(),
    updated_at                              TIMESTAMPTZ
);
CREATE INDEX idx_client_kyc_status ON client_profiles(kyc_status);
CREATE INDEX idx_client_risk_level ON client_profiles(risk_level);
CREATE INDEX idx_client_risk_score ON client_profiles(risk_score);
CREATE INDEX idx_client_pep ON client_profiles(is_pep) WHERE is_pep = TRUE;

-- -------------------------
-- KYC FORMS
-- -------------------------
CREATE TABLE kyc_forms (
    id                              SERIAL PRIMARY KEY,
    client_id                       INTEGER UNIQUE REFERENCES client_profiles(id) ON DELETE CASCADE,
    purpose_of_account              VARCHAR(255),
    business_type                   VARCHAR(100),
    industry_sector                 VARCHAR(100),
    estimated_annual_income         VARCHAR(50),
    primary_source_of_funds         VARCHAR(100),
    other_source_of_funds           TEXT,
    countries_of_transaction        JSONB,
    expected_monthly_volume         FLOAT,
    max_single_transaction          FLOAT,
    is_us_person                    BOOLEAN DEFAULT FALSE,
    has_other_citizenship           BOOLEAN DEFAULT FALSE,
    other_citizenships              JSONB,
    is_beneficial_owner             BOOLEAN DEFAULT TRUE,
    beneficial_owner_details        TEXT,
    agrees_to_terms                 BOOLEAN DEFAULT FALSE,
    agrees_to_data_processing       BOOLEAN DEFAULT FALSE,
    submitted_at                    TIMESTAMPTZ,
    is_complete                     BOOLEAN DEFAULT FALSE,
    completion_percentage           INTEGER DEFAULT 0,
    created_at                      TIMESTAMPTZ DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ
);

-- -------------------------
-- DOCUMENTS
-- -------------------------
CREATE TABLE documents (
    id                      SERIAL PRIMARY KEY,
    client_id               INTEGER REFERENCES client_profiles(id) ON DELETE CASCADE,
    document_type           document_type NOT NULL,
    status                  document_status DEFAULT 'pending',
    original_filename       VARCHAR(255) NOT NULL,
    stored_filename         VARCHAR(255) NOT NULL,
    file_path               VARCHAR(500) NOT NULL,
    file_size               INTEGER,
    mime_type               VARCHAR(100),
    ocr_data                JSONB,
    extracted_name          VARCHAR(255),
    extracted_dob           VARCHAR(50),
    extracted_document_number VARCHAR(100),
    extracted_expiry        VARCHAR(50),
    extracted_nationality   VARCHAR(100),
    is_authentic            BOOLEAN,
    authenticity_score      INTEGER,
    rejection_reason        TEXT,
    reviewer_notes          TEXT,
    reviewed_by             INTEGER REFERENCES users(id),
    reviewed_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);
CREATE INDEX idx_documents_client ON documents(client_id);
CREATE INDEX idx_documents_status ON documents(status);

-- -------------------------
-- RISK SCORES
-- -------------------------
CREATE TABLE risk_scores (
    id                          SERIAL PRIMARY KEY,
    client_id                   INTEGER REFERENCES client_profiles(id) ON DELETE CASCADE,
    total_score                 FLOAT DEFAULT 0.0,
    risk_level                  VARCHAR(20) NOT NULL DEFAULT 'low',
    personal_risk_score         FLOAT DEFAULT 0.0,
    transaction_risk_score      FLOAT DEFAULT 0.0,
    behavioral_risk_score       FLOAT DEFAULT 0.0,
    geographic_risk_score       FLOAT DEFAULT 0.0,
    document_risk_score         FLOAT DEFAULT 0.0,
    risk_factors                JSONB,
    calculation_details         JSONB,
    pep_flag                    BOOLEAN DEFAULT FALSE,
    sanctions_flag              BOOLEAN DEFAULT FALSE,
    high_risk_country_flag      BOOLEAN DEFAULT FALSE,
    unusual_transaction_flag    BOOLEAN DEFAULT FALSE,
    calculated_at               TIMESTAMPTZ DEFAULT NOW(),
    calculated_by               VARCHAR(50) DEFAULT 'system'
);
CREATE INDEX idx_risk_scores_client ON risk_scores(client_id);
CREATE INDEX idx_risk_scores_calculated_at ON risk_scores(calculated_at DESC);

-- -------------------------
-- TRANSACTIONS
-- -------------------------
CREATE TABLE transactions (
    id                      SERIAL PRIMARY KEY,
    client_id               INTEGER REFERENCES client_profiles(id) ON DELETE CASCADE,
    transaction_ref         VARCHAR(100) UNIQUE NOT NULL,
    type                    transaction_type NOT NULL,
    status                  transaction_status DEFAULT 'pending',
    amount                  FLOAT NOT NULL,
    currency                VARCHAR(10) DEFAULT 'USD',
    counterparty_name       VARCHAR(255),
    counterparty_account    VARCHAR(100),
    counterparty_country    VARCHAR(100),
    counterparty_bank       VARCHAR(255),
    description             TEXT,
    is_flagged              BOOLEAN DEFAULT FALSE,
    flag_reason             TEXT,
    risk_score              FLOAT DEFAULT 0.0,
    ip_address              VARCHAR(45),
    device_id               VARCHAR(255),
    transaction_date        TIMESTAMPTZ NOT NULL,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_transactions_client ON transactions(client_id);
CREATE INDEX idx_transactions_flagged ON transactions(is_flagged) WHERE is_flagged = TRUE;
CREATE INDEX idx_transactions_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_amount ON transactions(amount DESC);

-- -------------------------
-- AML ALERTS
-- -------------------------
CREATE TABLE aml_alerts (
    id                      SERIAL PRIMARY KEY,
    client_id               INTEGER REFERENCES client_profiles(id) ON DELETE CASCADE,
    transaction_id          INTEGER REFERENCES transactions(id),
    alert_type              alert_type NOT NULL,
    severity                alert_severity NOT NULL,
    status                  alert_status DEFAULT 'open',
    title                   VARCHAR(255) NOT NULL,
    description             TEXT NOT NULL,
    triggered_rule          VARCHAR(100),
    rule_parameters         JSONB,
    amount_involved         FLOAT,
    countries_involved      JSONB,
    assigned_to             INTEGER REFERENCES users(id),
    investigation_notes     TEXT,
    resolution_notes        TEXT,
    resolved_at             TIMESTAMPTZ,
    resolved_by             INTEGER REFERENCES users(id),
    is_auto_generated       BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ
);
CREATE INDEX idx_aml_alerts_client ON aml_alerts(client_id);
CREATE INDEX idx_aml_alerts_status ON aml_alerts(status);
CREATE INDEX idx_aml_alerts_severity ON aml_alerts(severity);
CREATE INDEX idx_aml_alerts_created ON aml_alerts(created_at DESC);

-- -------------------------
-- REVIEWS
-- -------------------------
CREATE TABLE reviews (
    id                  SERIAL PRIMARY KEY,
    client_id           INTEGER REFERENCES client_profiles(id) ON DELETE CASCADE,
    reviewer_id         INTEGER REFERENCES users(id),
    decision            review_decision,
    notes               TEXT,
    rejection_reason    TEXT,
    required_documents  TEXT,
    is_complete         BOOLEAN DEFAULT FALSE,
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reviews_client ON reviews(client_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);

-- -------------------------
-- AUDIT LOGS
-- -------------------------
CREATE TABLE audit_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     INTEGER,
    description     TEXT,
    old_values      JSONB,
    new_values      JSONB,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    status          VARCHAR(20) DEFAULT 'success',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- -------------------------
-- NOTIFICATIONS
-- -------------------------
CREATE TABLE notifications (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title               VARCHAR(255) NOT NULL,
    message             TEXT NOT NULL,
    notification_type   VARCHAR(50) DEFAULT 'info',
    is_read             BOOLEAN DEFAULT FALSE,
    action_url          VARCHAR(500),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;

-- =============================================================
-- INCIDENT MANAGEMENT & FALSE POSITIVE ANALYSIS
-- =============================================================
CREATE TYPE ticket_status AS ENUM ('new','assigned','in_progress','under_review','escalated','closed');
CREATE TYPE ticket_priority AS ENUM ('low','medium','high','critical');
CREATE TYPE incident_classification AS ENUM ('real_incident','false_positive');
CREATE TYPE false_positive_reason AS ENUM ('threshold_too_sensitive','incorrect_correlation_rule','whitelisted_activity','legitimate_user_behavior','data_quality_issue','configuration_error','other');

-- -------------------------
-- DETECTION RULES
-- -------------------------
CREATE TABLE detection_rules (
    id                  SERIAL PRIMARY KEY,
    rule_code           VARCHAR(100) UNIQUE NOT NULL,
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    alert_type          VARCHAR(100),
    parameters          JSONB,
    version             INTEGER NOT NULL DEFAULT 1,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ
);
CREATE INDEX idx_detection_rules_code ON detection_rules(rule_code);

-- -------------------------
-- INCIDENT TICKETS
-- -------------------------
CREATE TABLE incident_tickets (
    id                  SERIAL PRIMARY KEY,
    alert_id            INTEGER UNIQUE NOT NULL REFERENCES aml_alerts(id) ON DELETE CASCADE,
    client_id           INTEGER REFERENCES client_profiles(id),
    detection_rule_id   INTEGER REFERENCES detection_rules(id),
    alert_source        VARCHAR(100) DEFAULT 'AML Monitor',
    alert_type          VARCHAR(100),
    priority            ticket_priority NOT NULL DEFAULT 'medium',
    risk_level          risk_level NOT NULL DEFAULT 'medium',
    status              ticket_status NOT NULL DEFAULT 'new',
    classification      incident_classification,
    assigned_analyst_id INTEGER REFERENCES users(id),
    resolution_notes    TEXT,
    first_assigned_at   TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ
);
CREATE INDEX idx_incident_tickets_status ON incident_tickets(status);
CREATE INDEX idx_incident_tickets_rule ON incident_tickets(detection_rule_id);

-- -------------------------
-- INCIDENT COMMENTS
-- -------------------------
CREATE TABLE incident_comments (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER NOT NULL REFERENCES incident_tickets(id) ON DELETE CASCADE,
    author_id           INTEGER REFERENCES users(id),
    comment             TEXT NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_incident_comments_ticket ON incident_comments(ticket_id);

-- -------------------------
-- INCIDENT ASSIGNMENTS
-- -------------------------
CREATE TABLE incident_assignments (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER NOT NULL REFERENCES incident_tickets(id) ON DELETE CASCADE,
    assigned_to         INTEGER REFERENCES users(id),
    assigned_by         INTEGER REFERENCES users(id),
    note                TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_incident_assignments_ticket ON incident_assignments(ticket_id);

-- -------------------------
-- RISK ASSESSMENTS
-- -------------------------
CREATE TABLE risk_assessments (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER NOT NULL REFERENCES incident_tickets(id) ON DELETE CASCADE,
    assessor_id         INTEGER REFERENCES users(id),
    risk_level          risk_level NOT NULL,
    business_impact     TEXT,
    financial_impact    DOUBLE PRECISION,
    technical_impact    TEXT,
    confidence_score    DOUBLE PRECISION,
    recommended_action  TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_risk_assessments_ticket ON risk_assessments(ticket_id);

-- -------------------------
-- FALSE POSITIVES
-- -------------------------
CREATE TABLE false_positives (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER UNIQUE NOT NULL REFERENCES incident_tickets(id) ON DELETE CASCADE,
    classified_by       INTEGER REFERENCES users(id),
    detection_rule_id   INTEGER REFERENCES detection_rules(id),
    reason              false_positive_reason NOT NULL,
    root_cause          TEXT,
    source_system       VARCHAR(100),
    analyst_comments    TEXT,
    suggested_rule_tuning TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_false_positives_rule ON false_positives(detection_rule_id);

-- -------------------------
-- RULE TUNING HISTORY
-- -------------------------
CREATE TABLE rule_tuning_history (
    id                  SERIAL PRIMARY KEY,
    rule_id             INTEGER NOT NULL REFERENCES detection_rules(id) ON DELETE CASCADE,
    changed_by          INTEGER REFERENCES users(id),
    false_positive_id   INTEGER REFERENCES false_positives(id),
    version             INTEGER NOT NULL,
    change_description  TEXT,
    old_parameters      JSONB,
    new_parameters      JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_rule_tuning_history_rule ON rule_tuning_history(rule_id);

-- =============================================================
-- GDPR / PRIVACY (Stage 2)
-- =============================================================

-- Audit-log hash chain (tamper-evidence, ISO 27001 A.12.4.2)
ALTER TABLE audit_logs ADD COLUMN prev_hash  VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN entry_hash VARCHAR(64);
CREATE INDEX idx_audit_logs_entry_hash ON audit_logs(entry_hash);

-- Client data lifecycle (retention, restriction, anonymization)
ALTER TABLE client_profiles ADD COLUMN retention_until       TIMESTAMPTZ;
ALTER TABLE client_profiles ADD COLUMN processing_restricted BOOLEAN DEFAULT FALSE;
ALTER TABLE client_profiles ADD COLUMN anonymized_at         TIMESTAMPTZ;

CREATE TYPE dsar_type AS ENUM ('access','export','erasure','restriction','rectification');
CREATE TYPE dsar_status AS ENUM ('received','in_progress','completed','rejected');

-- Data-subject requests (GDPR Art.15–20)
CREATE TABLE data_subject_requests (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    request_type        dsar_type NOT NULL,
    status              dsar_status NOT NULL DEFAULT 'received',
    details             TEXT,
    resolution_notes    TEXT,
    handled_by          INTEGER REFERENCES users(id),
    legal_hold          BOOLEAN DEFAULT FALSE,   -- AML retention blocks erasure
    due_at              TIMESTAMPTZ,             -- 30-day response SLA
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
CREATE INDEX idx_dsar_user ON data_subject_requests(user_id);

-- Versioned, revocable consent records (GDPR Art.7)
CREATE TABLE consents (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose             VARCHAR(100) NOT NULL,
    policy_version      VARCHAR(20) NOT NULL DEFAULT '1.0',
    granted             BOOLEAN NOT NULL DEFAULT TRUE,
    granted_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    ip_address          VARCHAR(45),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_consents_user ON consents(user_id);
