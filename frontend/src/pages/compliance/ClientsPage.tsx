import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { clientsApi } from '@/services/api';
import { RiskBadge, KYCStatusBadge } from '@/components/shared/RiskBadge';
import type { ClientProfile } from '@/types';
import { Search, Filter, ChevronRight, Users } from 'lucide-react';
import { formatDate } from '@/utils/formatters';

export default function ClientsPage() {
  const [clients, setClients] = useState<ClientProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchClients = () => {
    setLoading(true);
    clientsApi.listClients({ search: search || undefined, risk_level: riskFilter || undefined, kyc_status: statusFilter || undefined })
      .then(r => setClients(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchClients(); }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Client Management</h1>
          <p className="mt-1 text-sm text-gray-500">{clients.length} total clients</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name..."
              className="w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
            <option value="">All Risk Levels</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
            <option value="">All Statuses</option>
            <option value="pending_review">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="in_progress">In Progress</option>
          </select>
          <button onClick={fetchClients}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Search
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        {loading ? (
          <div className="flex h-40 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : clients.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center text-gray-400">
            <Users className="mb-2 h-10 w-10" />
            <p>No clients found</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                {['Client', 'Nationality', 'Risk Level', 'Risk Score', 'KYC Status', 'PEP', 'Registered', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {clients.map(c => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900">{c.first_name} {c.last_name}</p>
                      <p className="text-xs text-gray-400">ID #{c.id}</p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.nationality || '—'}</td>
                  <td className="px-4 py-3"><RiskBadge level={c.risk_level} /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-gray-200">
                        <div
                          className="h-1.5 rounded-full"
                          style={{
                            width: `${c.risk_score}%`,
                            background: c.risk_score > 60 ? '#ef4444' : c.risk_score > 30 ? '#f59e0b' : '#10b981'
                          }}
                        />
                      </div>
                      <span className="text-xs font-medium">{c.risk_score.toFixed(0)}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3"><KYCStatusBadge status={c.kyc_status} /></td>
                  <td className="px-4 py-3">
                    {c.is_pep && <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">PEP</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(c.created_at)}</td>
                  <td className="px-4 py-3">
                    <Link to={`/clients/${c.id}`} className="flex items-center gap-1 text-primary hover:underline">
                      View <ChevronRight className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
