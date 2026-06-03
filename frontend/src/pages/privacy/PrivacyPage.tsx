import React, { useEffect, useState } from 'react';
import { privacyApi } from '@/services/api';
import { Download, Shield, Send, RefreshCw } from 'lucide-react';

const CONSENT_PURPOSES = [
  { key: 'kyc_processing', label: 'Обработка KYC-данных' },
  { key: 'aml_monitoring', label: 'AML-мониторинг операций' },
  { key: 'marketing', label: 'Маркетинговые сообщения' },
];

const DSAR_TYPES = [
  { key: 'access', label: 'Доступ к данным (Art.15)' },
  { key: 'rectification', label: 'Исправление данных (Art.16)' },
  { key: 'erasure', label: 'Удаление данных (Art.17)' },
  { key: 'restriction', label: 'Ограничение обработки (Art.18)' },
  { key: 'export', label: 'Экспорт / переносимость (Art.20)' },
];

export default function PrivacyPage() {
  const [consents, setConsents] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [reqType, setReqType] = useState('access');
  const [details, setDetails] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const load = async () => {
    const [c, r] = await Promise.all([privacyApi.listConsents(), privacyApi.myRequests()]);
    setConsents(c.data);
    setRequests(r.data);
  };

  useEffect(() => { load(); }, []);

  const consentGranted = (purpose: string) =>
    consents.find((c) => c.purpose === purpose)?.granted ?? false;

  const toggleConsent = async (purpose: string, granted: boolean) => {
    await privacyApi.upsertConsent({ purpose, granted });
    await load();
  };

  const exportData = async () => {
    setBusy(true);
    try {
      const res = await privacyApi.exportMyData();
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `my-data-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setBusy(false);
    }
  };

  const submitRequest = async () => {
    setBusy(true);
    setMsg('');
    try {
      await privacyApi.createRequest({ request_type: reqType, details: details || undefined });
      setDetails('');
      setMsg('Запрос отправлен. Срок ответа — до 30 дней.');
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Shield className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Приватность и мои данные</h1>
          <p className="text-sm text-gray-500">Управление согласиями и правами по GDPR</p>
        </div>
      </div>

      {/* Export */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">Экспорт моих данных</h2>
        <p className="mb-4 text-sm text-gray-500">
          Скачать копию всех персональных данных, которые хранит система (Art.15 / 20).
        </p>
        <button
          onClick={exportData}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Download className="h-4 w-4" /> Скачать JSON
        </button>
      </div>

      {/* Consents */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Согласия на обработку</h2>
        <ul className="space-y-3">
          {CONSENT_PURPOSES.map((p) => {
            const granted = consentGranted(p.key);
            return (
              <li key={p.key} className="flex items-center justify-between">
                <span className="text-sm text-gray-700">{p.label}</span>
                <button
                  onClick={() => toggleConsent(p.key, !granted)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                    granted
                      ? 'bg-green-100 text-green-700 hover:bg-green-200'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {granted ? 'Согласие дано — отозвать' : 'Дать согласие'}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      {/* DSAR */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Запрос по моим данным</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <select
            value={reqType}
            onChange={(e) => setReqType(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm"
          >
            {DSAR_TYPES.map((t) => (
              <option key={t.key} value={t.key}>{t.label}</option>
            ))}
          </select>
          <input
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            placeholder="Комментарий (необязательно)"
            className="flex-1 rounded-lg border px-3 py-2 text-sm"
          />
          <button
            onClick={submitRequest}
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Send className="h-4 w-4" /> Отправить
          </button>
        </div>
        {msg && <p className="mt-3 text-sm text-green-600">{msg}</p>}

        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700">История запросов</h3>
            <button onClick={load} className="text-gray-400 hover:text-gray-600">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-2">Тип</th>
                  <th className="px-4 py-2">Статус</th>
                  <th className="px-4 py-2">Создан</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {requests.length === 0 && (
                  <tr><td colSpan={3} className="px-4 py-4 text-center text-gray-400">Нет запросов</td></tr>
                )}
                {requests.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2">{r.request_type}</td>
                    <td className="px-4 py-2">{r.status}</td>
                    <td className="px-4 py-2 text-gray-500">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
