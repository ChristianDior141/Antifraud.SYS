import { format, parseISO } from 'date-fns';
import type {
  RiskLevel, KYCStatus, AlertSeverity, AlertStatus,
  TicketStatus, TicketPriority, IncidentClassification, FalsePositiveReason,
} from '@/types';

export const formatCurrency = (amount: number, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);

export const formatDate = (dateStr: string) => {
  try { return format(parseISO(dateStr), 'MMM d, yyyy'); } catch { return dateStr; }
};

export const formatDateTime = (dateStr: string) => {
  try { return format(parseISO(dateStr), 'MMM d, yyyy HH:mm'); } catch { return dateStr; }
};

export const riskLevelConfig: Record<RiskLevel, { label: string; color: string; bg: string }> = {
  low:      { label: 'Low Risk',      color: 'text-emerald-700', bg: 'bg-emerald-100' },
  medium:   { label: 'Medium Risk',   color: 'text-amber-700',   bg: 'bg-amber-100'   },
  high:     { label: 'High Risk',     color: 'text-red-700',     bg: 'bg-red-100'     },
  critical: { label: 'Critical Risk', color: 'text-purple-700',  bg: 'bg-purple-100'  },
};

export const kycStatusConfig: Record<KYCStatus, { label: string; color: string; bg: string }> = {
  not_started:    { label: 'Not Started',    color: 'text-gray-600',    bg: 'bg-gray-100'    },
  in_progress:    { label: 'In Progress',    color: 'text-blue-700',    bg: 'bg-blue-100'    },
  pending_review: { label: 'Pending Review', color: 'text-amber-700',   bg: 'bg-amber-100'   },
  approved:       { label: 'Approved',       color: 'text-emerald-700', bg: 'bg-emerald-100' },
  rejected:       { label: 'Rejected',       color: 'text-red-700',     bg: 'bg-red-100'     },
  requires_update:{ label: 'Needs Update',   color: 'text-orange-700',  bg: 'bg-orange-100'  },
};

export const alertSeverityConfig: Record<AlertSeverity, { label: string; color: string; bg: string }> = {
  low:      { label: 'Low',      color: 'text-blue-700',   bg: 'bg-blue-100'   },
  medium:   { label: 'Medium',   color: 'text-amber-700',  bg: 'bg-amber-100'  },
  high:     { label: 'High',     color: 'text-red-700',    bg: 'bg-red-100'    },
  critical: { label: 'Critical', color: 'text-purple-700', bg: 'bg-purple-100' },
};

export const alertStatusConfig: Record<AlertStatus, { label: string; color: string }> = {
  open:                 { label: 'Open',               color: 'text-red-600'    },
  under_investigation:  { label: 'Investigating',      color: 'text-amber-600'  },
  escalated:            { label: 'Escalated',          color: 'text-orange-600' },
  resolved:             { label: 'Resolved',           color: 'text-emerald-600'},
  false_positive:       { label: 'False Positive',     color: 'text-gray-600'   },
  sar_filed:            { label: 'SAR Filed',          color: 'text-purple-600' },
};

export const ticketStatusConfig: Record<TicketStatus, { label: string; color: string; bg: string }> = {
  new:           { label: 'New',           color: 'text-blue-700',    bg: 'bg-blue-100'    },
  assigned:      { label: 'Assigned',      color: 'text-indigo-700',  bg: 'bg-indigo-100'  },
  in_progress:   { label: 'In Progress',   color: 'text-amber-700',   bg: 'bg-amber-100'   },
  under_review:  { label: 'Under Review',  color: 'text-purple-700',  bg: 'bg-purple-100'  },
  escalated:     { label: 'Escalated',     color: 'text-orange-700',  bg: 'bg-orange-100'  },
  closed:        { label: 'Closed',        color: 'text-emerald-700', bg: 'bg-emerald-100' },
};

export const ticketPriorityConfig: Record<TicketPriority, { label: string; color: string; bg: string }> = {
  low:      { label: 'Low',      color: 'text-emerald-700', bg: 'bg-emerald-100' },
  medium:   { label: 'Medium',   color: 'text-amber-700',   bg: 'bg-amber-100'   },
  high:     { label: 'High',     color: 'text-red-700',     bg: 'bg-red-100'     },
  critical: { label: 'Critical', color: 'text-purple-700',  bg: 'bg-purple-100'  },
};

export const classificationConfig: Record<IncidentClassification, { label: string; color: string; bg: string }> = {
  real_incident:  { label: 'Real Incident',  color: 'text-red-700',  bg: 'bg-red-100'  },
  false_positive: { label: 'False Positive', color: 'text-gray-700', bg: 'bg-gray-200' },
};

export const fpReasonLabels: Record<FalsePositiveReason, string> = {
  threshold_too_sensitive:    'Threshold Too Sensitive',
  incorrect_correlation_rule: 'Incorrect Correlation Rule',
  whitelisted_activity:       'Whitelisted Activity',
  legitimate_user_behavior:   'Legitimate User Behavior',
  data_quality_issue:         'Data Quality Issue',
  configuration_error:        'Configuration Error',
  other:                      'Other',
};
