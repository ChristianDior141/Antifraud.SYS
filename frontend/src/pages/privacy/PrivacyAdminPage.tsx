import React, { useEffect, useState } from 'react';
import { privacyApi } from '@/services/api';
import { ShieldCheck, Trash2, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

export default function PrivacyAdminPage() {
  const [requests, setRequests] = useState<any[]>([]);
  const [integrity, setIntegrity] = useState<any>(null);
  const [purgeResult, setPurgeResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    const r = await privacyApi.allRequests();
    setRequests(r.data);
  };

  useEffect(() => { load(); }, []);

  const process = async (id: number, status: string) => {
    setBusy(true);
    setError('');
    try {
      await privacyApi.processRequest(id, { status });
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка обработки запроса');
    } finally {
      setBusy(false);
    }
  };

  const runPurge = async () => {
    setBusy(true);
    try {
      const res = await privacyApi.runRetentionPurge();
      setPurgeResult(res.data);
    } finally {
      setBusy(false);
    }
  };

  const checkIntegrity = async () => {
    setBusy(true);
    try {
      const res = await privacyApi.auditIntegrity();
      setIntegrity(res.data);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">GDPR-администрирование</h1>
          <p className="text-sm text-gray-500">Запросы субъектов, ретеншен, целостность аудита</p>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {/* Tools */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <h3 className="mb-2 font-semibold text-gray-900">Политика хранения</h3>
          <p className="mb-3 text-sm text-gray-500">
            Анонимизировать профили с истёкшим сроком хранения (Art.5(1)(e)).
          </p>
          <button
            onClick={runPurge}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" /> Запустить purge
          </button>
          {purgeResult && (
            <p className="mt-3 text-sm text-gray-600">
              Проверено: {purgeResult.checked}, анонимизировано: {purgeResult.purged}
            </p>
          )}
        </div>

        <div className="rounded-xl border bg-white p-5">
          <h3 className="mb-2 font-semibold text-gray-900">Целостность аудита</h3>
          <p className="mb-3 text-sm text-gray-500">
            Проверить hash-цепочку журнала на подделку (A.12.4.2).
          </p>
          <button
            onClick={checkIntegrity}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <ShieldCheck className="h-4 w-4" /> Проверить
          </button>
          {integrity && (
            <p className={`mt-3 text-sm font-medium ${integrity.valid ? 'text-green-600' : 'text-red-600'}`}>
              {integrity.valid
                ? `Цепочка цела (${integrity.total} записей)`
                : `Нарушение на записи #${integrity.broken_at_id}`}
            </p>
          )}
        </div>
      </div>

      {/* DSAR table */}
      <div className="rounded-xl border bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Запросы субъектов данных (DSAR)</h2>
          <button onClick={load} className="text-gray-400 hover:text-gray-600">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2">ID</th>
                <th className="px-4 py-2">Польз.</th>
                <th className="px-4 py-2">Тип</th>
                <th className="px-4 py-2">Статус</th>
                <th className="px-4 py-2">Hold</th>
                <th className="px-4 py-2">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {requests.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-4 text-center text-gray-400">Нет запросов</td></tr>
              )}
              {requests.map((r) => (
                <tr key={r.id}>
                  <td className="px-4 py-2">{r.id}</td>
                  <td className="px-4 py-2">{r.user_id}</td>
                  <td className="px-4 py-2">{r.request_type}</td>
                  <td className="px-4 py-2">{r.status}</td>
                  <td className="px-4 py-2">{r.legal_hold ? 'да' : '—'}</td>
                  <td className="px-4 py-2">
                    {r.status !== 'completed' && r.status !== 'rejected' && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => process(r.id, 'completed')}
                          disabled={busy}
                          className="inline-flex items-center gap-1 rounded bg-green-100 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-200 disabled:opacity-50"
                        >
                          <CheckCircle className="h-3 w-3" /> Выполнить
                        </button>
                        <button
                          onClick={() => process(r.id, 'rejected')}
                          disabled={busy}
                          className="inline-flex items-center gap-1 rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-200 disabled:opacity-50"
                        >
                          <XCircle className="h-3 w-3" /> Отклонить
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
