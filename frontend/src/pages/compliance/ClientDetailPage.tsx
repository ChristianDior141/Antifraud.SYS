import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clientsApi, transactionsApi } from '@/services/api';
import { RiskBadge, KYCStatusBadge } from '@/components/shared/RiskBadge';
import type { ClientProfile, Transaction } from '@/types';
import { formatCurrency, formatDateTime } from '@/utils/formatters';
import {
  ArrowLeft, AlertTriangle, ShieldAlert, Flag, User, Briefcase,
  Globe, Wallet, TrendingUp, CheckCircle, Lightbulb, Gauge,
} from 'lucide-react';

interface RiskFactor {
  factor: string;
  score: number;
  description?: string;
  recommended_action?: string;
}

interface RiskAssessment {
  total_score: number;
  risk_level: string;
  factors: RiskFactor[];
}

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const clientId = Number(id);

  const [client, setClient] = useState<ClientProfile | null>(null);
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [risk, setRisk] = useState<RiskAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [suspiciousOnly, setSuspiciousOnly] = useState(false);

  useEffect(() => {
    Promise.all([
      clientsApi.getClient(clientId),
      transactionsApi.getClientTransactions(clientId),
    ])
      .then(([c, t]) => { setClient(c.data); setTxns(t.data); })
      .finally(() => setLoading(false));
    // Risk assessment loads independently (may compute on the fly)
    clientsApi.getRiskAssessment(clientId)
      .then(r => setRisk(r.data))
      .catch(() => setRisk(null));
  }, [clientId]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!client) {
    return (
      <div className="card p-8 text-center text-gray-500">
        Client not found.
        <div className="mt-3">
          <Link to="/clients" className="text-primary hover:underline">← Back to clients</Link>
        </div>
      </div>
    );
  }

  const flagged = txns.filter(t => t.is_flagged);
  const flaggedVolume = flagged.reduce((sum, t) => sum + t.amount, 0);
  const totalVolume = txns.reduce((sum, t) => sum + t.amount, 0);
  const isElevated = client.risk_score > 30;

  const visibleTxns = suspiciousOnly ? flagged : txns;

  const scoreColor = client.risk_score > 60 ? '#ef4444' : client.risk_score > 30 ? '#f59e0b' : '#10b981';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Back link */}
      <Link to="/clients" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
        <ArrowLeft className="h-4 w-4" /> Back to clients
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              {client.first_name} {client.last_name}
            </h1>
            <p className="mt-1 text-sm text-gray-400">Client ID #{client.id}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <RiskBadge level={client.risk_level} />
              <KYCStatusBadge status={client.kyc_status} />
              {client.is_pep && (
                <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700">PEP</span>
              )}
              {client.is_sanctioned && (
                <span className="rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-semibold text-purple-700">Sanctioned</span>
              )}
              {client.is_high_risk_country && (
                <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-700">High-Risk Country</span>
              )}
            </div>
          </div>

          {/* Risk score gauge */}
          <div className="text-center">
            <div className="relative h-24 w-24">
              <svg className="h-24 w-24 -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#e5e7eb" strokeWidth="10" />
                <circle
                  cx="50" cy="50" r="42" fill="none" stroke={scoreColor} strokeWidth="10"
                  strokeDasharray={`${(client.risk_score / 100) * 264} 264`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold" style={{ color: scoreColor }}>
                  {client.risk_score.toFixed(0)}
                </span>
                <span className="text-[10px] text-gray-400">RISK SCORE</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Elevated risk warning */}
      {isElevated && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
          <div className="text-sm text-amber-800">
            <p className="font-semibold">Elevated risk client</p>
            <p>This client's risk score is above the standard threshold. Transaction history is shown below with suspicious activity highlighted for enhanced due diligence.</p>
          </div>
        </div>
      )}

      {/* Risk factors with explanations */}
      {risk && risk.factors.length > 0 && (
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 border-b p-4">
            <Gauge className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-gray-900">Risk Factors & Recommendations</h3>
            <span className="ml-auto text-sm text-gray-500">
              {risk.factors.length} factor{risk.factors.length !== 1 ? 's' : ''} contributing to score {risk.total_score.toFixed(0)}
            </span>
          </div>
          <div className="divide-y divide-gray-100">
            {risk.factors.map((f, i) => (
              <div key={i} className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{f.factor}</span>
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
                        +{f.score} pts
                      </span>
                    </div>
                    {f.description && (
                      <p className="mt-1 text-sm text-gray-600">{f.description}</p>
                    )}
                    {f.recommended_action && (
                      <div className="mt-2 flex items-start gap-1.5 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
                        <Lightbulb className="mt-0.5 h-4 w-4 flex-shrink-0" />
                        <span><span className="font-semibold">Recommended:</span> {f.recommended_action}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Profile facts */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Fact icon={Globe} label="Nationality" value={client.nationality || '—'} />
        <Fact icon={Briefcase} label="Occupation" value={client.occupation || '—'} />
        <Fact icon={Wallet} label="Source of Funds" value={client.source_of_funds || '—'} />
        <Fact icon={User} label="Country of Residence" value={client.country_of_residence || client.country || '—'} />
      </div>

      {/* Transaction summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <SummaryCard icon={TrendingUp} color="blue" label="Total Transactions"
          value={txns.length.toString()} sub={formatCurrency(totalVolume)} />
        <SummaryCard icon={Flag} color="red" label="Suspicious Transactions"
          value={flagged.length.toString()} sub={`${txns.length > 0 ? ((flagged.length / txns.length) * 100).toFixed(0) : 0}% of total`} />
        <SummaryCard icon={ShieldAlert} color="purple" label="Suspicious Volume"
          value={formatCurrency(flaggedVolume)} sub="flagged amount" />
      </div>

      {/* Transactions table */}
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b p-4">
          <h3 className="font-semibold text-gray-900">Transaction History</h3>
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={suspiciousOnly}
              onChange={e => setSuspiciousOnly(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            Show suspicious only
          </label>
        </div>

        {visibleTxns.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center text-gray-400">
            <CheckCircle className="mb-2 h-8 w-8" />
            <p>{suspiciousOnly ? 'No suspicious transactions' : 'No transactions found'}</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b bg-gray-50">
              <tr>
                {['Reference', 'Type', 'Amount', 'Counterparty', 'Country', 'Date', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {visibleTxns.map(t => (
                <tr
                  key={t.id}
                  className={t.is_flagged ? 'bg-red-50 hover:bg-red-100/70' : 'hover:bg-gray-50'}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {t.is_flagged && <Flag className="h-3.5 w-3.5 flex-shrink-0 text-red-500" />}
                      <span className="font-mono text-xs text-gray-700">{t.transaction_ref}</span>
                    </div>
                    {t.is_flagged && t.flag_reason && (
                      <p className="mt-1 text-xs text-red-600">{t.flag_reason}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 capitalize text-gray-600">{t.type}</td>
                  <td className="px-4 py-3 font-medium text-gray-900">{formatCurrency(t.amount, t.currency)}</td>
                  <td className="px-4 py-3 text-gray-600">{t.counterparty_name || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{t.counterparty_country || '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDateTime(t.transaction_date)}</td>
                  <td className="px-4 py-3">
                    {t.is_flagged ? (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">Suspicious</span>
                    ) : (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700">Clear</span>
                    )}
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

function Fact({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-gray-400">
        <Icon className="h-4 w-4" />
        <span className="text-xs uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-1.5 font-medium text-gray-900">{value}</p>
    </div>
  );
}

function SummaryCard({ icon: Icon, color, label, value, sub }: {
  icon: any; color: 'blue' | 'red' | 'purple'; label: string; value: string; sub: string;
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-600',
    red: 'bg-red-100 text-red-600',
    purple: 'bg-purple-100 text-purple-600',
  };
  return (
    <div className="card flex items-center justify-between p-5">
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-xs text-gray-400">{sub}</p>
      </div>
      <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${colors[color]}`}>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  );
}
