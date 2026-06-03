import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { incidentsApi, analyticsApi } from '@/services/api';
import { StatCard } from '@/components/shared/StatCard';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { cn } from '@/utils/cn';
import {
  ticketStatusConfig, ticketPriorityConfig, classificationConfig, formatDateTime,
} from '@/utils/formatters';
import type { IncidentTicket, IncidentMetrics } from '@/types';
import { Ticket, FolderOpen, CheckCircle, Timer } from 'lucide-react';

const STATUSES = ['', 'new', 'assigned', 'in_progress', 'under_review', 'escalated', 'closed'];
const PRIORITIES = ['', 'low', 'medium', 'high', 'critical'];

export default function IncidentsPage() {
  const [tickets, setTickets] = useState<IncidentTicket[]>([]);
  const [metrics, setMetrics] = useState<IncidentMetrics | null>(null);
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    const params: Record<string, any> = { page_size: 100 };
    if (status) params.status = status;
    if (priority) params.priority = priority;
    Promise.all([incidentsApi.list(params), analyticsApi.getIncidentMetrics()])
      .then(([t, m]) => { setTickets(t.data); setMetrics(m.data); })
      .finally(() => setLoading(false));
  };

  useEffect(load, [status, priority]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Incident Management</h1>
        <p className="text-sm text-gray-500">Triage and investigate alerts as incident tickets.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Incidents" value={metrics?.total_incidents ?? '—'} icon={Ticket} color="blue" />
        <StatCard title="Open Incidents" value={metrics?.open_incidents ?? '—'} icon={FolderOpen} color="amber" />
        <StatCard title="Closed Incidents" value={metrics?.closed_incidents ?? '—'} icon={CheckCircle} color="green" />
        <StatCard title="MTTR" value={metrics ? `${metrics.mttr_hours}h` : '—'}
          subtitle={metrics ? `MTTA ${metrics.mtta_hours}h` : undefined} icon={Timer} color="purple" />
      </div>

      <div className="flex flex-wrap gap-3">
        <select className="input w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => <option key={s} value={s}>{s ? ticketStatusConfig[s as keyof typeof ticketStatusConfig].label : 'All statuses'}</option>)}
        </select>
        <select className="input w-44" value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map((p) => <option key={p} value={p}>{p ? ticketPriorityConfig[p as keyof typeof ticketPriorityConfig].label : 'All priorities'}</option>)}
        </select>
      </div>

      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Ticket</th>
              <th className="px-4 py-3">Alert Type</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Classification</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : tickets.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No incidents match the filters.</td></tr>
            ) : tickets.map((t) => {
              const sc = ticketStatusConfig[t.status];
              const pc = ticketPriorityConfig[t.priority];
              return (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">
                    <Link to={`/incidents/${t.id}`} className="text-primary hover:underline">INC-{t.id}</Link>
                  </td>
                  <td className="px-4 py-3 capitalize text-gray-700">{(t.alert_type || '').replace(/_/g, ' ')}</td>
                  <td className="px-4 py-3"><span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', pc.bg, pc.color)}>{pc.label}</span></td>
                  <td className="px-4 py-3"><RiskBadge level={t.risk_level} /></td>
                  <td className="px-4 py-3"><span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', sc.bg, sc.color)}>{sc.label}</span></td>
                  <td className="px-4 py-3">
                    {t.classification
                      ? <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-semibold', classificationConfig[t.classification].bg, classificationConfig[t.classification].color)}>{classificationConfig[t.classification].label}</span>
                      : <span className="text-gray-400">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatDateTime(t.created_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
