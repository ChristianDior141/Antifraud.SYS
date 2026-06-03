import React, { useEffect, useState } from 'react';
import { adminApi } from '@/services/api';
import { StatCard } from '@/components/shared/StatCard';
import { formatDateTime } from '@/utils/formatters';
import { Users, Activity, Shield, Plus, Trash2 } from 'lucide-react';
import type { User } from '@/types';

export default function AdminPage() {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [tab, setTab] = useState<'users' | 'logs'>('users');
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', full_name: '', password: '', role: 'compliance_officer' });
  const [createError, setCreateError] = useState('');

  useEffect(() => {
    Promise.all([adminApi.getStats(), adminApi.listUsers(), adminApi.getAuditLogs()])
      .then(([s, u, l]) => { setStats(s.data); setUsers(u.data); setLogs(l.data); })
      .finally(() => setLoading(false));
  }, []);

  const handleDeactivate = async (id: number) => {
    if (!confirm('Deactivate this user?')) return;
    await adminApi.deactivateUser(id);
    setUsers(u => u.map(x => x.id === id ? { ...x, is_active: false } : x));
  };

  const handleCreate = async () => {
    setCreateError('');
    try {
      const { data } = await adminApi.createUser(newUser);
      setUsers(u => [data, ...u]);
      setShowCreate(false);
      setNewUser({ email: '', full_name: '', password: '', role: 'compliance_officer' });
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || 'Failed');
    }
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Administration Panel</h1>
        <button onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> Add User
        </button>
      </div>

      {stats && (
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard title="Total Users" value={stats.total_users} icon={Users} color="blue" />
          <StatCard title="Active Users" value={stats.active_users} icon={Shield} color="green" />
          <StatCard title="Audit Log Entries" value={stats.total_audit_logs} icon={Activity} color="purple" />
        </div>
      )}

      {/* Create user modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="card p-6 w-full max-w-md">
            <h3 className="mb-4 font-semibold text-gray-900">Create Staff User</h3>
            {createError && <p className="mb-3 text-sm text-red-600">{createError}</p>}
            <div className="space-y-3">
              {[
                { key: 'full_name', label: 'Full Name', type: 'text' },
                { key: 'email', label: 'Email', type: 'email' },
                { key: 'password', label: 'Password', type: 'password' },
              ].map(({ key, label, type }) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-gray-700">{label}</label>
                  <input type={type} value={(newUser as any)[key]}
                    onChange={e => setNewUser(u => ({ ...u, [key]: e.target.value }))}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none" />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <select value={newUser.role} onChange={e => setNewUser(u => ({ ...u, role: e.target.value }))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
                  <option value="compliance_officer">Compliance Officer</option>
                  <option value="risk_analyst">Risk Analyst</option>
                  <option value="admin">Administrator</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={handleCreate}
                className="flex-1 rounded-lg bg-primary py-2 text-sm font-semibold text-white hover:bg-blue-700">
                Create
              </button>
              <button onClick={() => setShowCreate(false)}
                className="flex-1 rounded-lg border border-gray-300 py-2 text-sm font-medium hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="card overflow-hidden">
        <div className="flex border-b">
          {(['users', 'logs'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-6 py-3 text-sm font-medium capitalize transition-colors ${tab === t ? 'border-b-2 border-primary text-primary' : 'text-gray-500 hover:text-gray-700'}`}>
              {t === 'users' ? 'User Management' : 'Audit Logs'}
            </button>
          ))}
        </div>

        {tab === 'users' && (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                {['Name', 'Email', 'Role', 'Status', 'Created', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map(u => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.full_name}</td>
                  <td className="px-4 py-3 text-gray-600">{u.email}</td>
                  <td className="px-4 py-3 capitalize">
                    <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
                      {u.role.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${u.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatDateTime(u.created_at)}</td>
                  <td className="px-4 py-3">
                    {u.is_active && (
                      <button onClick={() => handleDeactivate(u.id)}
                        className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700">
                        <Trash2 className="h-3 w-3" /> Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === 'logs' && (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                {['Action', 'Resource', 'Description', 'IP Address', 'Time'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((l: any) => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700">{l.action}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{l.resource_type}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{l.description}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{l.ip_address}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDateTime(l.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
