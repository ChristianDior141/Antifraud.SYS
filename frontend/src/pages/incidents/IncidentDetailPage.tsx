import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { incidentsApi } from '@/services/api';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { cn } from '@/utils/cn';
import {
  ticketStatusConfig, ticketPriorityConfig, classificationConfig, fpReasonLabels,
  formatDateTime, formatCurrency,
} from '@/utils/formatters';
import type { IncidentTicketDetail, RiskLevel, FalsePositiveReason } from '@/types';
import type { RootState } from '@/store';
import { ArrowLeft, UserPlus, AlertTriangle, MessageSquare, RotateCcw } from 'lucide-react';

const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'];
const STATUS_OPTIONS = ['new', 'assigned', 'in_progress', 'under_review', 'escalated', 'closed'];
const FP_REASONS: FalsePositiveReason[] = [
  'threshold_too_sensitive', 'incorrect_correlation_rule', 'whitelisted_activity',
  'legitimate_user_behavior', 'data_quality_issue', 'configuration_error', 'other',
];

export default function IncidentDetailPage() {
  const { id } = useParams();
  const ticketId = Number(id);
  const { user } = useSelector((s: RootState) => s.auth);
  const [ticket, setTicket] = useState<IncidentTicketDetail | null>(null);
  const [comment, setComment] = useState('');

  // risk assessment form
  const [ra, setRa] = useState({
    risk_level: 'medium' as RiskLevel, business_impact: '', financial_impact: '',
    technical_impact: '', confidence_score: '80', recommended_action: '',
  });
  // classification form
  const [cls, setCls] = useState<'real_incident' | 'false_positive'>('false_positive');
  const [fp, setFp] = useState({
    reason: 'threshold_too_sensitive' as FalsePositiveReason, root_cause: '',
    analyst_comments: '', suggested_rule_tuning: '',
  });
  const [resolution, setResolution] = useState('');
  const [reclassify, setReclassify] = useState(false);

  const load = () => incidentsApi.get(ticketId).then((r) => setTicket(r.data));
  useEffect(() => { load(); }, [ticketId]);

  if (!ticket) {
    return <div className="flex h-64 items-center justify-center text-gray-400">Loading…</div>;
  }

  const sc = ticketStatusConfig[ticket.status];
  const pc = ticketPriorityConfig[ticket.priority];
  const closed = ticket.status === 'closed';

  const assignToMe = async () => {
    if (!user) return;
    await incidentsApi.assign(ticketId, { assigned_to: user.id, note: 'Self-assigned' });
    load();
  };
  const setStatus = async (status: string) => { await incidentsApi.updateStatus(ticketId, { status }); load(); };
  const escalate = async () => { await incidentsApi.escalate(ticketId); load(); };
  const submitComment = async () => {
    if (!comment.trim()) return;
    await incidentsApi.addComment(ticketId, comment.trim()); setComment(''); load();
  };
  const submitRa = async () => {
    await incidentsApi.addRiskAssessment(ticketId, {
      risk_level: ra.risk_level,
      business_impact: ra.business_impact || undefined,
      financial_impact: ra.financial_impact ? Number(ra.financial_impact) : undefined,
      technical_impact: ra.technical_impact || undefined,
      confidence_score: ra.confidence_score ? Number(ra.confidence_score) : undefined,
      recommended_action: ra.recommended_action || undefined,
    });
    load();
  };
  const submitClassification = async () => {
    const payload: Record<string, any> = { classification: cls, resolution_notes: resolution || undefined };
    if (cls === 'false_positive') {
      payload.reason = fp.reason;
      payload.root_cause = fp.root_cause || undefined;
      payload.analyst_comments = fp.analyst_comments || undefined;
      payload.suggested_rule_tuning = fp.suggested_rule_tuning || undefined;
    }
    await incidentsApi.classify(ticketId, payload);
    setReclassify(false);
    load();
  };
  const reopen = async () => { await incidentsApi.updateStatus(ticketId, { status: 'under_review' }); load(); };

  return (
    <div className="space-y-6">
      <Link to="/incidents" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800">
        <ArrowLeft className="h-4 w-4" /> Back to incidents
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">INC-{ticket.id}</h1>
            <p className="text-sm capitalize text-gray-500">
              {(ticket.alert_type || '').replace(/_/g, ' ')} · {ticket.alert_source} · Alert #{ticket.alert_id}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', pc.bg, pc.color)}>{pc.label} priority</span>
            <RiskBadge level={ticket.risk_level} />
            <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', sc.bg, sc.color)}>{sc.label}</span>
            {ticket.classification && (
              <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', classificationConfig[ticket.classification].bg, classificationConfig[ticket.classification].color)}>
                {classificationConfig[ticket.classification].label}
              </span>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-4">
          <button className="btn-outline" onClick={assignToMe}><UserPlus className="h-4 w-4" /> Assign to me</button>
          <button className="btn-outline" onClick={escalate}><AlertTriangle className="h-4 w-4" /> Escalate</button>
          {closed && (
            <button className="btn-outline" onClick={reopen}><RotateCcw className="h-4 w-4" /> Reopen</button>
          )}
          <label className="ml-auto text-xs text-gray-500">Status</label>
          <select className="input" value={ticket.status} onChange={(e) => setStatus(e.target.value)}>
            {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{ticketStatusConfig[s as keyof typeof ticketStatusConfig].label}</option>)}
          </select>
        </div>
        {ticket.resolution_notes && (
          <p className="mt-3 rounded-lg bg-gray-50 p-3 text-sm text-gray-600"><b>Resolution:</b> {ticket.resolution_notes}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Risk assessment */}
        <div className="card p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Risk Assessment</h2>
          {ticket.risk_assessments.length > 0 && (
            <div className="mb-4 space-y-2">
              {ticket.risk_assessments.map((a) => (
                <div key={a.id} className="rounded-lg border p-3 text-sm">
                  <div className="flex items-center justify-between">
                    <RiskBadge level={a.risk_level} />
                    <span className="text-xs text-gray-400">{formatDateTime(a.created_at)}</span>
                  </div>
                  <p className="mt-1 text-gray-600">
                    Confidence {a.confidence_score ?? '—'}% · Financial {a.financial_impact != null ? formatCurrency(a.financial_impact) : '—'}
                  </p>
                  {a.recommended_action && <p className="text-gray-500">→ {a.recommended_action}</p>}
                </div>
              ))}
            </div>
          )}
          <div className="space-y-2">
            <select className="input w-full" value={ra.risk_level} onChange={(e) => setRa({ ...ra, risk_level: e.target.value as RiskLevel })}>
              {RISK_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
            </select>
            <input className="input w-full" placeholder="Business impact" value={ra.business_impact} onChange={(e) => setRa({ ...ra, business_impact: e.target.value })} />
            <input className="input w-full" type="number" placeholder="Financial impact ($)" value={ra.financial_impact} onChange={(e) => setRa({ ...ra, financial_impact: e.target.value })} />
            <input className="input w-full" placeholder="Technical impact" value={ra.technical_impact} onChange={(e) => setRa({ ...ra, technical_impact: e.target.value })} />
            <input className="input w-full" type="number" placeholder="Confidence score (0-100)" value={ra.confidence_score} onChange={(e) => setRa({ ...ra, confidence_score: e.target.value })} />
            <input className="input w-full" placeholder="Recommended action" value={ra.recommended_action} onChange={(e) => setRa({ ...ra, recommended_action: e.target.value })} />
            <button className="btn-primary w-full" onClick={submitRa}>Save assessment</button>
          </div>
        </div>

        {/* Classification */}
        <div className="card p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Classification</h2>
          {ticket.classification && !reclassify ? (
            <div className="space-y-2 text-sm">
              <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', classificationConfig[ticket.classification].bg, classificationConfig[ticket.classification].color)}>
                {classificationConfig[ticket.classification].label}
              </span>
              {ticket.false_positive && (
                <div className="rounded-lg border p-3">
                  <p><b>Reason:</b> {fpReasonLabels[ticket.false_positive.reason]}</p>
                  {ticket.false_positive.root_cause && <p><b>Root cause:</b> {ticket.false_positive.root_cause}</p>}
                  {ticket.false_positive.suggested_rule_tuning && <p><b>Suggested tuning:</b> {ticket.false_positive.suggested_rule_tuning}</p>}
                </div>
              )}
              <button className="btn-outline w-full" onClick={() => setReclassify(true)}>Reclassify</button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2">
                <button className={cn('btn-outline flex-1', cls === 'real_incident' && 'border-primary text-primary')} onClick={() => setCls('real_incident')}>Real Incident</button>
                <button className={cn('btn-outline flex-1', cls === 'false_positive' && 'border-primary text-primary')} onClick={() => setCls('false_positive')}>False Positive</button>
              </div>
              {cls === 'false_positive' && (
                <>
                  <select className="input w-full" value={fp.reason} onChange={(e) => setFp({ ...fp, reason: e.target.value as FalsePositiveReason })}>
                    {FP_REASONS.map((r) => <option key={r} value={r}>{fpReasonLabels[r]}</option>)}
                  </select>
                  <textarea className="input w-full" rows={2} placeholder="Root cause" value={fp.root_cause} onChange={(e) => setFp({ ...fp, root_cause: e.target.value })} />
                  <textarea className="input w-full" rows={2} placeholder="Analyst comments" value={fp.analyst_comments} onChange={(e) => setFp({ ...fp, analyst_comments: e.target.value })} />
                  <input className="input w-full" placeholder="Suggested rule tuning" value={fp.suggested_rule_tuning} onChange={(e) => setFp({ ...fp, suggested_rule_tuning: e.target.value })} />
                </>
              )}
              <textarea className="input w-full" rows={2} placeholder="Resolution notes" value={resolution} onChange={(e) => setResolution(e.target.value)} />
              <button className="btn-primary w-full" onClick={submitClassification}>Classify &amp; close</button>
            </div>
          )}
        </div>
      </div>

      {/* Investigation history */}
      <div className="card p-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <MessageSquare className="h-5 w-5 text-gray-400" /> Investigation History
        </h2>
        <div className="space-y-3">
          {ticket.assignments.map((a) => (
            <div key={`as-${a.id}`} className="text-sm text-gray-600">
              <span className="text-gray-400">{formatDateTime(a.created_at)}</span> · Assigned to analyst #{a.assigned_to}{a.note ? ` — ${a.note}` : ''}
            </div>
          ))}
          {ticket.comments.map((c) => (
            <div key={`c-${c.id}`} className="rounded-lg bg-gray-50 p-3 text-sm">
              <p className="text-gray-700">{c.comment}</p>
              <p className="mt-1 text-xs text-gray-400">analyst #{c.author_id} · {formatDateTime(c.created_at)}</p>
            </div>
          ))}
          {ticket.assignments.length === 0 && ticket.comments.length === 0 && (
            <p className="text-sm text-gray-400">No activity yet.</p>
          )}
        </div>
        <div className="mt-4 flex gap-2">
          <input className="input flex-1" placeholder="Add a comment…" value={comment}
            onChange={(e) => setComment(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submitComment()} />
          <button className="btn-primary" onClick={submitComment}>Post</button>
        </div>
      </div>
    </div>
  );
}
