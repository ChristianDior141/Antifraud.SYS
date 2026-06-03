export type UserRole = 'client' | 'compliance_officer' | 'risk_analyst' | 'admin';
export type KYCStatus = 'not_started' | 'in_progress' | 'pending_review' | 'approved' | 'rejected' | 'requires_update';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type DocumentStatus = 'pending' | 'under_review' | 'approved' | 'rejected' | 'expired';
export type AlertStatus = 'open' | 'under_investigation' | 'escalated' | 'resolved' | 'false_positive' | 'sar_filed';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

export interface ClientProfile {
  id: number;
  user_id: number;
  first_name: string;
  last_name: string;
  middle_name?: string;
  date_of_birth?: string;
  nationality?: string;
  country_of_residence?: string;
  phone_number?: string;
  address_line1?: string;
  city?: string;
  country?: string;
  occupation?: string;
  source_of_funds?: string;
  annual_income_range?: string;
  expected_monthly_transaction_volume?: number;
  kyc_status: KYCStatus;
  risk_level: RiskLevel;
  risk_score: number;
  is_pep: boolean;
  is_sanctioned: boolean;
  is_high_risk_country: boolean;
  created_at: string;
}

export interface Document {
  id: number;
  client_id: number;
  document_type: string;
  status: DocumentStatus;
  original_filename: string;
  mime_type?: string;
  file_size?: number;
  is_authentic?: boolean;
  authenticity_score?: number;
  rejection_reason?: string;
  created_at: string;
}

export interface Transaction {
  id: number;
  client_id: number;
  transaction_ref: string;
  type: string;
  status: string;
  amount: number;
  currency: string;
  counterparty_name?: string;
  counterparty_country?: string;
  is_flagged: boolean;
  flag_reason?: string;
  risk_score: number;
  transaction_date: string;
  created_at: string;
}

export interface AMLAlert {
  id: number;
  client_id: number;
  transaction_id?: number;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  description: string;
  amount_involved?: number;
  countries_involved?: string[];
  investigation_notes?: string;
  is_auto_generated: boolean;
  created_at: string;
}

export interface DashboardStats {
  clients: {
    total: number;
    approved: number;
    rejected: number;
    pending_review: number;
    approval_rate: number;
  };
  risk_distribution: { low: number; medium: number; high: number; critical: number };
  aml: { open_alerts: number; critical_alerts: number };
  transactions: { total: number; flagged: number; total_volume: number };
  documents_pending_review: number;
}

// ---- Incident Management & False Positive Analysis ----------------------

export type TicketStatus = 'new' | 'assigned' | 'in_progress' | 'under_review' | 'escalated' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';
export type IncidentClassification = 'real_incident' | 'false_positive';
export type FalsePositiveReason =
  | 'threshold_too_sensitive' | 'incorrect_correlation_rule' | 'whitelisted_activity'
  | 'legitimate_user_behavior' | 'data_quality_issue' | 'configuration_error' | 'other';

export interface IncidentComment {
  id: number; ticket_id: number; author_id?: number; comment: string; created_at: string;
}

export interface IncidentAssignment {
  id: number; ticket_id: number; assigned_to?: number; assigned_by?: number;
  note?: string; created_at: string;
}

export interface RiskAssessment {
  id: number; ticket_id: number; assessor_id?: number; risk_level: RiskLevel;
  business_impact?: string; financial_impact?: number; technical_impact?: string;
  confidence_score?: number; recommended_action?: string; created_at: string;
}

export interface FalsePositive {
  id: number; ticket_id: number; classified_by?: number; detection_rule_id?: number;
  reason: FalsePositiveReason; root_cause?: string; source_system?: string;
  analyst_comments?: string; suggested_rule_tuning?: string; created_at: string;
}

export interface IncidentTicket {
  id: number; alert_id: number; client_id?: number; detection_rule_id?: number;
  alert_source?: string; alert_type?: string; priority: TicketPriority; risk_level: RiskLevel;
  status: TicketStatus; classification?: IncidentClassification; assigned_analyst_id?: number;
  resolution_notes?: string; first_assigned_at?: string; closed_at?: string; created_at: string;
}

export interface IncidentTicketDetail extends IncidentTicket {
  comments: IncidentComment[];
  assignments: IncidentAssignment[];
  risk_assessments: RiskAssessment[];
  false_positive?: FalsePositive | null;
}

export interface DetectionRuleStats {
  total_alerts: number; confirmed_incidents: number; false_positives: number;
  false_positive_rate: number; effectiveness_score: number;
}

export interface DetectionRule {
  id: number; rule_code: string; name: string; description?: string; alert_type?: string;
  parameters?: Record<string, any>; version: number; is_active: boolean; created_at: string;
  stats?: DetectionRuleStats;
}

export interface RuleTuningHistory {
  id: number; rule_id: number; changed_by?: number; false_positive_id?: number; version: number;
  change_description?: string; old_parameters?: Record<string, any>;
  new_parameters?: Record<string, any>; created_at: string;
}

export interface DetectionRuleDetail extends DetectionRule {
  tuning_history: RuleTuningHistory[];
  suggested_improvements: string[];
}

export interface IncidentMetrics {
  total_incidents: number; open_incidents: number; closed_incidents: number;
  average_resolution_hours: number; mttr_hours: number; mtta_hours: number;
  by_status: Record<string, number>;
}

export interface FalsePositiveMetrics {
  total_false_positives: number; false_positive_rate: number;
  by_rule: Record<string, number>; by_source: Record<string, number>;
  monthly_trend: { month: string; false_positives: number; classified: number; false_positive_rate: number }[];
}

export interface Analyst { id: number; full_name: string; role: string; }
