import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from 'recharts';
import { analyticsApi } from '@/services/api';
import { StatCard } from '@/components/shared/StatCard';
import type { RootState } from '@/store';
import type { DashboardStats } from '@/types';
import {
  Users, ShieldAlert, TrendingUp, FileText, AlertTriangle, CheckCircle, XCircle, Clock
} from 'lucide-react';

const RISK_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function DashboardPage() {
  const { user } = useSelector((s: RootState) => s.auth);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([analyticsApi.getDashboard(), analyticsApi.getMonthlyTrend()])
      .then(([s, t]) => { setStats(s.data); setTrend(t.data); })
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

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name?.split(' ')[0]}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Here's what's happening on the KYC/AML platform today.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Clients"
          value={stats?.clients.total ?? 0}
          subtitle={`${stats?.clients.approval_rate ?? 0}% approval rate`}
          icon={Users}
          color="blue"
        />
        <StatCard
          title="Pending Reviews"
          value={stats?.clients.pending_review ?? 0}
          subtitle={`${stats?.documents_pending_review ?? 0} docs pending`}
          icon={Clock}
          color="amber"
        />
        <StatCard
          title="Open AML Alerts"
          value={stats?.aml.open_alerts ?? 0}
          subtitle={`${stats?.aml.critical_alerts ?? 0} critical`}
          icon={AlertTriangle}
          color="red"
        />
        <StatCard
          title="Flagged Transactions"
          value={stats?.transactions.flagged ?? 0}
          subtitle={`of ${stats?.transactions.total ?? 0} total`}
          icon={ShieldAlert}
          color="purple"
        />
      </div>

      {/* Second row */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Approved Clients" value={stats?.clients.approved ?? 0} icon={CheckCircle} color="green" />
        <StatCard title="Rejected Clients" value={stats?.clients.rejected ?? 0} icon={XCircle} color="red" />
        <StatCard
          title="Total Volume"
          value={`$${((stats?.transactions.total_volume ?? 0) / 1000).toFixed(0)}K`}
          icon={TrendingUp}
          color="blue"
        />
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Monthly trend */}
        <div className="card p-6 lg:col-span-2">
          <h3 className="mb-4 font-semibold text-gray-900">Monthly Activity</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="new_clients" stroke="#3b82f6" name="New Clients" strokeWidth={2} />
              <Line type="monotone" dataKey="aml_alerts" stroke="#ef4444" name="AML Alerts" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk distribution */}
        <div className="card p-6">
          <h3 className="mb-4 font-semibold text-gray-900">Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={riskPieData} cx="50%" cy="50%" outerRadius={75} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false} fontSize={11}>
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
      </div>

      {/* AML bar chart */}
      <div className="card p-6">
        <h3 className="mb-4 font-semibold text-gray-900">Monthly AML Alerts vs New Clients</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={trend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="new_clients" fill="#3b82f6" name="New Clients" radius={[4,4,0,0]} />
            <Bar dataKey="aml_alerts" fill="#ef4444" name="AML Alerts" radius={[4,4,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
