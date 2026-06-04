import React, { useEffect, useState } from 'react';
import { monitoringApi } from '@/services/api';
import { ClipboardList, Download, Search } from 'lucide-react';

type Tab = 'audit' | 'activity' | 'devices' | 'sessions' | 'login-history' | 'security-events';

const TABS: { key: Tab; label: string; exportable: boolean }[] = [
  { key: 'audit', label: 'Аудит', exportable: true },
  { key: 'activity', label: 'Действия', exportable: true },
  { key: 'devices', label: 'Устройства', exportable: false },
  { key: 'sessions', label: 'Сессии', exportable: false },
  { key: 'login-history', label: 'Входы', exportable: true },
  { key: 'security-events', label: 'События ИБ', exportable: true },
];

export default function AuditDashboardPage() {
  const [tab, setTab] = useState<Tab>('audit');
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [action, setAction] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      let res;
      if (tab === 'audit') {
        res = await monitoringApi.audit({ q: q || undefined, action: action || undefined,
          date_from: dateFrom || undefined, date_to: dateTo || undefined });
      } else if (tab === 'activity') res = await monitoringApi.activity();
      else if (tab === 'devices') res = await monitoringApi.devices();
      else if (tab === 'sessions') res = await monitoringApi.sessions();
      else if (tab === 'login-history') res = await monitoringApi.loginHistory();
      else res = await monitoringApi.securityEvents();
      setRows(res.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [tab]);

  const doExport = async (format: string) => {
    const res = await monitoringApi.exportLogs(tab, format);
    const blob = new Blob([res.data]);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${tab}.${format === 'xlsx' ? 'xlsx' : format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const columns = rows.length ? Object.keys(rows[0]).filter((k) => k !== 'event_metadata') : [];
  const fmt = (v: any) => {
    if (v === null || v === undefined) return '—';
    if (typeof v === 'boolean') return v ? '✓' : '—';
    if (typeof v === 'string' && /\d{4}-\d{2}-\d{2}T/.test(v)) return new Date(v).toLocaleString();
    return String(v);
  };
  const currentTab = TABS.find((t) => t.key === tab)!;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Аудит и мониторинг</h1>
          <p className="text-sm text-gray-500">Полная история активности, устройств и событий безопасности</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${tab === t.key ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters (audit only) + export */}
      <div className="flex flex-wrap items-end gap-2">
        {tab === 'audit' && (
          <>
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск (пользователь/IP/детали)"
                className="rounded-lg border py-2 pl-8 pr-3 text-sm" />
            </div>
            <input value={action} onChange={(e) => setAction(e.target.value)} placeholder="Действие"
              className="rounded-lg border px-3 py-2 text-sm" />
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="rounded-lg border px-3 py-2 text-sm" />
            <button onClick={load} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white">Применить</button>
          </>
        )}
        <div className="ml-auto flex gap-2">
          {currentTab.exportable && ['csv', 'xlsx', 'pdf'].map((f) => (
            <button key={f} onClick={() => doExport(f)}
              className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              <Download className="h-4 w-4" /> {f.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>{columns.map((c) => <th key={c} className="px-3 py-2 whitespace-nowrap">{c}</th>)}</tr>
          </thead>
          <tbody className="divide-y">
            {loading && <tr><td className="px-4 py-6 text-center text-gray-400">Загрузка…</td></tr>}
            {!loading && rows.length === 0 && <tr><td className="px-4 py-6 text-center text-gray-400">Нет данных</td></tr>}
            {!loading && rows.map((r, i) => (
              <tr key={i}>
                {columns.map((c) => <td key={c} className="px-3 py-2 whitespace-nowrap text-gray-700">{fmt(r[c])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
