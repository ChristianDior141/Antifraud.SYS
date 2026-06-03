import React, { useEffect, useState } from 'react';
import { amlApi } from '@/services/api';
import { AlertSeverityBadge } from '@/components/shared/RiskBadge';
import { StatCard } from '@/components/shared/StatCard';
import type { AMLAlert } from '@/types';
import { formatDateTime, formatCurrency, alertStatusConfig } from '@/utils/formatters';
import { AlertTriangle, ShieldAlert, Activity, CheckCircle } from 'lucide-react';

export default function AMLMonitoringPage() {
  const [alerts, setAlerts] = useState<AMLAlert[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [selected, setSelected] = useState<AMLAlert | null>(null);

  const fetch = () => {
    setLoading(true);
    Promise.all([
      amlApi.listAlerts({ status: statusFilter || undefined, severity: severityFilter || undefined }),
      amlApi.getStats(),
    ]).then(([a, s]) => { setAlerts(a.data); setStats(s.data); })
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const handleUpdateStatus = async (id: number, status: string) => {
    await amlApi.updateAlert(id, { status });
    fetch();
    setSelected(null);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-gray-900">AML Monitoring</h1>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard title="Open Alerts" value={stats.open_alerts} icon={AlertTriangle} color="red" />
          <StatCard title="Critical Alerts" value={stats.critical_alerts} icon={ShieldAlert} color="purple" />
          <StatCard title="Total Alerts" value={stats.total_alerts} icon={Activity} color="blue" />
        </div>
      )}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="under_investigation">Under Investigation</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
          </select>
          <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <button onClick={fetch} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Filter
          </button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Alert list */}
        <div className="card lg:col-span-2 overflow-hidden">
          {loading ? (
            <div className="flex h-40 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b bg-gray-50">
                <tr>
                  {['Alert', 'Severity', 'Status', 'Amount', 'Date'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {alerts.map(a => (
                  <tr key={a.id} onClick={() => setSelected(a)}
                    className="cursor-pointer hover:bg-blue-50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 line-clamp-1">{a.title}</p>
                      <p className="text-xs text-gray-400 capitalize">{a.alert_type.replace(/_/g, ' ')}</p>
                    </td>
                    <td className="px-4 py-3"><AlertSeverityBadge severity={a.severity} /></td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium ${alertStatusConfig[a.status]?.color}`}>
                        {alertStatusConfig[a.status]?.label ?? a.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium">
                      {a.amount_involved ? formatCurrency(a.amount_involved) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatDateTime(a.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Detail panel */}
        <div className="card p-5">
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-gray-900">{selected.title}</h3>
                <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-lg">×</button>
              </div>
              <AlertSeverityBadge severity={selected.severity} />
              <p className="text-sm text-gray-600">{selected.description}</p>
              {selected.amount_involved && (
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Amount Involved</p>
                  <p className="font-semibold text-gray-900">{formatCurrency(selected.amount_involved)}</p>
                </div>
              )}
              <div className="space-y-2">
                <p className="text-xs font-medium text-gray-500 uppercase">Update Status</p>
                {['under_investigation', 'resolved', 'false_positive', 'sar_filed'].map(s => (
                  <button key={s} onClick={() => handleUpdateStatus(selected.id, s)}
                    className="block w-full rounded-lg border border-gray-200 px-3 py-2 text-left text-sm hover:bg-gray-50 capitalize">
                    {s.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-40 flex-col items-center justify-center text-gray-400">
              <AlertTriangle className="mb-2 h-8 w-8" />
              <p className="text-sm">Select an alert to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
