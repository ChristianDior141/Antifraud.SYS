import React, { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line,
} from 'recharts';
import { analyticsApi } from '@/services/api';
import { StatCard } from '@/components/shared/StatCard';
import type { IncidentMetrics, FalsePositiveMetrics } from '@/types';
import { Ticket, FolderOpen, Timer, Percent, ShieldAlert, CheckCircle } from 'lucide-react';

const RISK_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function IncidentDashboardPage() {
  const [inc, setInc] = useState<IncidentMetrics | null>(null);
  const [fp, setFp] = useState<FalsePositiveMetrics | null>(null);
  const [risk, setRisk] = useState<{ low: number; medium: number; high: number; critical: number } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      analyticsApi.getIncidentMetrics(),
      analyticsApi.getFalsePositiveMetrics(),
      analyticsApi.getRiskMetrics(),
    ])
      .then(([i, f, r]) => { setInc(i.data); setFp(f.data); setRisk(r.data); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const statusData = inc ? Object.entries(inc.by_status).map(([k, v]) => ({ name: k.replace(/_/g, ' '), value: v })) : [];
  const byRuleData = fp ? Object.entries(fp.by_rule).map(([k, v]) => ({ name: k, value: v })) : [];
  const bySourceData = fp ? Object.entries(fp.by_source).map(([k, v]) => ({ name: k, value: v })) : [];
  const riskData = risk ? [
    { name: 'Low', value: risk.low }, { name: 'Medium', value: risk.medium },
    { name: 'High', value: risk.high }, { name: 'Critical', value: risk.critical },
  ] : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Incident &amp; False Positive Analytics</h1>
        <p className="text-sm text-gray-500">Executive view of detection quality and team performance.</p>
      </div>

      {/* Incident KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Incidents" value={inc?.total_incidents ?? 0} icon={Ticket} color="blue" />
        <StatCard title="Open Incidents" value={inc?.open_incidents ?? 0} icon={FolderOpen} color="amber" />
        <StatCard title="MTTR / MTTA" value={`${inc?.mttr_hours ?? 0}h`} subtitle={`Acknowledge ${inc?.mtta_hours ?? 0}h`} icon={Timer} color="purple" />
        <StatCard title="False Positive Rate" value={`${fp?.false_positive_rate ?? 0}%`} subtitle={`${fp?.total_false_positives ?? 0} false positives`} icon={Percent} color="red" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* FP rate trend */}
        <div className="card p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <CheckCircle className="h-5 w-5 text-emerald-500" /> False Positive Rate — Monthly Trend
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={fp?.monthly_trend ?? []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" fontSize={12} />
              <YAxis unit="%" fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="false_positive_rate" name="FP rate" stroke="#ef4444" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
          <p className="mt-2 text-center text-xs text-gray-400">Declining trend reflects rule tuning over time.</p>
        </div>

        {/* Incidents by status */}
        <div className="card p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Incidents by Status</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" fontSize={11} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Bar dataKey="value" name="Incidents" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* FP by rule */}
        <div className="card p-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <ShieldAlert className="h-5 w-5 text-red-500" /> False Positives by Rule
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={byRuleData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" fontSize={12} />
              <YAxis type="category" dataKey="name" width={150} fontSize={11} />
              <Tooltip />
              <Bar dataKey="value" name="False positives" fill="#f59e0b" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Risk distribution */}
        <div className="card p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Incidents by Risk Level</h2>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={riskData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                {riskData.map((_, i) => <Cell key={i} fill={RISK_COLORS[i % RISK_COLORS.length]} />)}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* FP by source */}
      {bySourceData.length > 0 && (
        <div className="card p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">False Positives by Source System</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={bySourceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Bar dataKey="value" name="False positives" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
