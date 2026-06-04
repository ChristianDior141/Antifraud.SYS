import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { authApi } from '@/services/api';
import type { RootState } from '@/store';
import { ShieldCheck, KeyRound } from 'lucide-react';

export default function SecurityPage() {
  const { user } = useSelector((s: RootState) => s.auth);
  const [enabled, setEnabled] = useState<boolean>(false);
  const [setupSecret, setSetupSecret] = useState('');
  const [otpUri, setOtpUri] = useState('');
  const [code, setCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setEnabled(Boolean((user as any)?.mfa_enabled));
  }, [user]);

  const startSetup = async () => {
    setError(''); setMsg(''); setBackupCodes([]); setBusy(true);
    try {
      const { data } = await authApi.mfaSetup();
      setSetupSecret(data.secret);
      setOtpUri(data.otpauth_uri);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось начать настройку');
    } finally { setBusy(false); }
  };

  const verify = async () => {
    setError(''); setMsg(''); setBusy(true);
    try {
      const { data } = await authApi.mfaVerify(code);
      setEnabled(true);
      setSetupSecret(''); setOtpUri(''); setCode('');
      setBackupCodes(data.backup_codes || []);
      setMsg('Двухфакторная аутентификация включена. Сохраните резервные коды!');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Неверный код');
    } finally { setBusy(false); }
  };

  const disable = async () => {
    setError(''); setMsg(''); setBusy(true);
    try {
      await authApi.mfaDisable(code);
      setEnabled(false); setCode('');
      setMsg('Двухфакторная аутентификация отключена.');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Неверный код');
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <ShieldCheck className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">Безопасность аккаунта</h1>
          <p className="text-sm text-gray-500">Двухфакторная аутентификация (TOTP)</p>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {msg && <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">{msg}</div>}

      <div className="rounded-xl border bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Статус 2FA</h2>
          <span className={`rounded-full px-3 py-1 text-xs font-medium ${
            enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
          }`}>
            {enabled ? 'Включена' : 'Отключена'}
          </span>
        </div>

        {!enabled && !otpUri && (
          <button
            onClick={startSetup}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <KeyRound className="h-4 w-4" /> Настроить 2FA
          </button>
        )}

        {otpUri && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">
              Добавьте секрет в приложение-аутентификатор (Google Authenticator, Authy и т.п.):
            </p>
            <code className="block break-all rounded-lg bg-gray-50 p-3 text-xs text-gray-800">{setupSecret}</code>
            <p className="break-all text-xs text-gray-400">{otpUri}</p>
            <div className="flex gap-2">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Код из приложения"
                className="rounded-lg border px-3 py-2 text-sm"
              />
              <button
                onClick={verify}
                disabled={busy || !code}
                className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Подтвердить
              </button>
            </div>
          </div>
        )}

        {enabled && (
          <div className="space-y-3">
            <p className="text-sm text-gray-600">Чтобы отключить 2FA, введите текущий код:</p>
            <div className="flex gap-2">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Код 2FA"
                className="rounded-lg border px-3 py-2 text-sm"
              />
              <button
                onClick={disable}
                disabled={busy || !code}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Отключить
              </button>
            </div>
          </div>
        )}

        {backupCodes.length > 0 && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="mb-2 text-sm font-semibold text-amber-800">
              Резервные коды (показываются один раз):
            </p>
            <div className="grid grid-cols-2 gap-2 font-mono text-sm text-amber-900">
              {backupCodes.map((c) => <span key={c}>{c}</span>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
