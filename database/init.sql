-- KYC/AML Platform Database Initialization
-- PostgreSQL 15+

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Roles/enums are created by SQLAlchemy ORM migration on startup.
-- This file sets up extensions and a comments-only ERD reference.

COMMENT ON DATABASE kyc_aml_db IS 'KYC/AML Client Risk Assessment Platform — Dissertation Project';

-- Indexes created after ORM tables exist (run after first startup)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_kyc_status ON client_profiles(kyc_status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_client_risk_level ON client_profiles(risk_level);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_flagged ON transactions(is_flagged) WHERE is_flagged = true;
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aml_alerts_status ON aml_alerts(status);
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
