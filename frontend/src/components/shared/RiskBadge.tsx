import React from 'react';
import { cn } from '@/utils/cn';
import { riskLevelConfig, kycStatusConfig, alertSeverityConfig } from '@/utils/formatters';
import type { RiskLevel, KYCStatus, AlertSeverity } from '@/types';

export function RiskBadge({ level }: { level: RiskLevel }) {
  const cfg = riskLevelConfig[level];
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  );
}

export function KYCStatusBadge({ status }: { status: KYCStatus }) {
  const cfg = kycStatusConfig[status];
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  );
}

export function AlertSeverityBadge({ severity }: { severity: AlertSeverity }) {
  const cfg = alertSeverityConfig[severity];
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  );
}
