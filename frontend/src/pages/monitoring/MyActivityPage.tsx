import React, { useEffect, useState } from 'react';
import { monitoringApi } from '@/services/api';
import { MonitorSmartphone, Globe, History, ShieldCheck } from 'lucide-react';

export default function MyActivityPage() {
  const [devices, setDevices] = useState<any[]>([]);
  const [logins, setLogins] = useState<any[]>([]);
  const [activity, setActivity] = useState<any[]>([]);

  const load = async () => {
    const [d, l, a] = await Promise.all([
      monitoringApi.myDevices(),
      monitoringApi.myLoginHistory(),
      monitoringApi.myActivity(),
    ]);
    setDevices(d.data); setLogins(l.data); setActivity(a.data);
  };
  useEffect(() => { load(); }, []);

  const trust = async (id: number) => { await monitoringApi.trustDevice(id); await load(); };
  const fmt = (s?: string) => (s ? new Date(s).toLocaleString() : '—');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <History className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Моя активность</h1>
          <p className="text-sm text-gray-500">Устройства, входы и действия по аккаунту</p>
        </div>
      </div>

      {/* Devices */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <MonitorSmartphone className="h-5 w-5" /> Мои устройства
        </h2>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr><th className="px-4 py-2">Устройство</th><th className="px-4 py-2">ОС / Браузер</th><th className="px-4 py-2">Тип</th><th className="px-4 py-2">Последний раз</th><th className="px-4 py-2">Доверие</th></tr>
            </thead>
            <tbody className="divide-y">
              {devices.length === 0 && <tr><td colSpan={5} className="px-4 py-4 text-center text-gray-400">Нет устройств</td></tr>}
              {devices.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-2">{d.device_name || d.device_id}</td>
                  <td className="px-4 py-2">{d.operating_system} / {d.browser}</td>
                  <td className="px-4 py-2">{d.device_type}</td>
                  <td className="px-4 py-2 text-gray-500">{fmt(d.last_seen)}</td>
                  <td className="px-4 py-2">
                    {d.is_trusted
                      ? <span className="inline-flex items-center gap-1 text-green-600"><ShieldCheck className="h-4 w-4" />доверенное</span>
                      : <button onClick={() => trust(d.id)} className="rounded bg-gray-100 px-2 py-1 text-xs hover:bg-gray-200">Отметить доверенным</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Login history */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-900">
          <Globe className="h-5 w-5" /> История входов
        </h2>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr><th className="px-4 py-2">Время</th><th className="px-4 py-2">IP</th><th className="px-4 py-2">Результат</th></tr>
            </thead>
            <tbody className="divide-y">
              {logins.length === 0 && <tr><td colSpan={3} className="px-4 py-4 text-center text-gray-400">Нет данных</td></tr>}
              {logins.map((l) => (
                <tr key={l.id}>
                  <td className="px-4 py-2 text-gray-500">{fmt(l.created_at)}</td>
                  <td className="px-4 py-2">{l.ip_address || '—'}</td>
                  <td className="px-4 py-2">{l.success ? <span className="text-green-600">успех</span> : <span className="text-red-600">неудача</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Activity */}
      <div className="rounded-xl border bg-white p-6">
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Действия</h2>
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr><th className="px-4 py-2">Время</th><th className="px-4 py-2">Действие</th><th className="px-4 py-2">Объект</th><th className="px-4 py-2">Детали</th></tr>
            </thead>
            <tbody className="divide-y">
              {activity.length === 0 && <tr><td colSpan={4} className="px-4 py-4 text-center text-gray-400">Нет действий</td></tr>}
              {activity.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-2 text-gray-500">{fmt(a.created_at)}</td>
                  <td className="px-4 py-2">{a.action_type}</td>
                  <td className="px-4 py-2">{a.entity_type ? `${a.entity_type} #${a.entity_id ?? ''}` : '—'}</td>
                  <td className="px-4 py-2 text-gray-500">{a.details || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
