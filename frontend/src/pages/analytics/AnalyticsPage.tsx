import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, AreaChart, Area, Legend,
} from 'recharts';
import { analyticsApi, clientsApi } from '@/services/api';
import { StatCard } from '@/components/shared/StatCard';
import { RiskBadge } from '@/components/shared/RiskBadge';
import type { DashboardStats, ClientProfile } from '@/types';
import {
  Users, ShieldAlert, TrendingUp, AlertTriangle, CheckCircle, XCircle, Clock, Percent, ChevronRight,
} from 'lucide-react';

const RISK_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
const STATUS_COLORS = ['#10b981', '#ef4444', '#f59e0b'];

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [topRisk, setTopRisk] = useState<ClientProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      analyticsApi.getDashboard(),
      analyticsApi.getMonthlyTrend(),
      clientsApi.listClients({ page_size: 100 }),
    ])
      .then(([s, t, c]) => {
        setStats(s.data);
        setTrend(t.data);
        const sorted = [...c.data].sort((a, b) => b.risk_score - a.risk_score).slice(0, 8);
        setTopRisk(sorted);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  const riskPieData = stats ? [
    { name: 'Low', value: stats.risk_distribution.low },
    { name: 'Medium', value: stats.risk_distribution.medium },
    { name: 'High', value: stats.risk_distribution.high },
    { name: 'Critical', value: stats.risk_distribution.critical },
  ] : [];

  const statusData = stats ? [
    { name: 'Approved', value: stats.clients.approved },
    { name: 'Rejected', value: stats.clients.rejected },
    { name: 'Pending', value: stats.clients.pending_review },
  ] : [];

  const flaggedRate = stats && stats.transactions.total > 0
    ? ((stats.transactions.flagged / stats.transactions.total) * 100).toFixed(1)
    : '0';

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="mt-1 text-sm text-gray-500">
          Compliance and risk metrics across the platform.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Clients" value={stats?.clients.total ?? 0} icon={Users} color="blue" />
        <StatCard
          title="Approval Rate"
          value={`${stats?.clients.approval_rate ?? 0}%`}
          icon={Percent}
          color="green"
        />
        <StatCard title="Open AML Alerts" value={stats?.aml.open_alerts ?? 0} subtitle={`${stats?.aml.critical_alerts ?? 0} critical`} icon={AlertTriangle} color="red" />
        <StatCard
          title="Total Volume"
          value={`$${((stats?.transactions.total_volume ?? 0) / 1000).toFixed(0)}K`}
          icon={TrendingUp}
          color="purple"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Approved" value={stats?.clients.approved ?? 0} icon={CheckCircle} color="green" />
        <StatCard title="Rejected" value={stats?.clients.rejected ?? 0} icon={XCircle} color="red" />
        <StatCard title="Pending Review" value={stats?.clients.pending_review ?? 0} icon={Clock} color="amber" />
        <StatCard title="Flagged Txn Rate" value={`${flaggedRate}%`} subtitle={`${stats?.transactions.flagged ?? 0} flagged`} icon={ShieldAlert} color="purple" />
      </div>

      {/* Charts row 1 */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Risk distribution */}
        <div className="card p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={riskPieData} cx="50%" cy="50%" outerRadius={85} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>
                {riskPieData.map((_, i) => <Cell key={i} fill={RISK_COLORS[i % RISK_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {riskPieData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[i] }} />
                <span className="text-xs text-gray-600">{d.name}: {d.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* KYC status breakdown */}
        <div className="card p-6">
          <h3 className="mb-4 font-semibold text-gray-900">KYC Status Breakdown</h3>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={statusData} cx="50%" cy="50%" innerRadius={50} outerRadius={85} dataKey="value" label={({ name, value }) => `${name}: ${value}`} labelLine={false} fontSize={11}>
                {statusData.map((_, i) => <Cell key={i} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-3 flex justify-center gap-4">
            {statusData.map((d, i) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full" style={{ background: STATUS_COLORS[i] }} />
                <span className="text-xs text-gray-600">{d.name}: {d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Monthly trend area */}
      <div className="card p-6">
        <h3 className="mb-4 font-semibold text-gray-900">New Clients & AML Alerts Over Time</h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={trend}>
            <defs>
              <linearGradient id="clientsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="alertsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Area type="monotone" dataKey="new_clients" stroke="#3b82f6" fill="url(#clientsGrad)" name="New Clients" strokeWidth={2} />
            <Area type="monotone" dataKey="aml_alerts" stroke="#ef4444" fill="url(#alertsGrad)" name="AML Alerts" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Transactions bar */}
      <div className="card p-6">
        <h3 className="mb-4 font-semibold text-gray-900">Monthly Activity</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="new_clients" fill="#3b82f6" name="New Clients" radius={[4, 4, 0, 0]} />
            <Bar dataKey="aml_alerts" fill="#ef4444" name="AML Alerts" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top high-risk clients */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b p-4">
          <div>
            <h3 className="font-semibold text-gray-900">Top High-Risk Clients</h3>
            <p className="text-xs text-gray-500">Clients ranked by risk score — click to review transactions</p>
          </div>
          <Link to="/clients" className="text-sm text-primary hover:underline">View all</Link>
        </div>
        <table className="w-full text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              {['Client', 'Nationality', 'Risk Level', 'Risk Score', 'Flags', ''].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {topRisk.map(c => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{c.first_name} {c.last_name}</p>
                  <p className="text-xs text-gray-400">ID #{c.id}</p>
                </td>
                <td className="px-4 py-3 text-gray-600">{c.nationality || '—'}</td>
                <td className="px-4 py-3"><RiskBadge level={c.risk_level} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 rounded-full bg-gray-200">
                      <div className="h-1.5 rounded-full" style={{
                        width: `${c.risk_score}%`,
                        background: c.risk_score > 60 ? '#ef4444' : c.risk_score > 30 ? '#f59e0b' : '#10b981',
                      }} />
                    </div>
                    <span className="text-xs font-medium">{c.risk_score.toFixed(0)}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {c.is_pep && <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">PEP</span>}
                    {c.is_sanctioned && <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs font-semibold text-purple-700">SAN</span>}
                    {c.is_high_risk_country && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">HRC</span>}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Link to={`/clients/${c.id}`} className="flex items-center gap-1 text-primary hover:underline">
                    Review <ChevronRight className="h-3 w-3" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
