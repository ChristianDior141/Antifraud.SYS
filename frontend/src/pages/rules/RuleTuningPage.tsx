import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { detectionRulesApi } from '@/services/api';
import { cn } from '@/utils/cn';
import { fpReasonLabels, formatDateTime } from '@/utils/formatters';
import type { DetectionRule, DetectionRuleDetail, FalsePositive } from '@/types';
import type { RootState } from '@/store';
import { Sliders, TrendingDown, ShieldCheck } from 'lucide-react';

function effColor(score: number) {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-red-600';
}

export default function RuleTuningPage() {
  const { user } = useSelector((s: RootState) => s.auth);
  const isAdmin = user?.role === 'admin';
  const [rules, setRules] = useState<DetectionRule[]>([]);
  const [selected, setSelected] = useState<DetectionRuleDetail | null>(null);
  const [fps, setFps] = useState<FalsePositive[]>([]);
  const [params, setParams] = useState('');
  const [desc, setDesc] = useState('');
  const [err, setErr] = useState('');

  const loadRules = () => detectionRulesApi.list().then((r) => setRules(r.data));
  useEffect(() => { loadRules(); }, []);

  const openRule = async (id: number) => {
    const [d, f] = await Promise.all([detectionRulesApi.get(id), detectionRulesApi.falsePositives(id)]);
    setSelected(d.data);
    setFps(f.data);
    setParams(JSON.stringify(d.data.parameters ?? {}, null, 2));
    setDesc('');
    setErr('');
  };

  const applyTuning = async () => {
    if (!selected) return;
    let parsed: any;
    try { parsed = JSON.parse(params); } catch { setErr('Parameters must be valid JSON'); return; }
    await detectionRulesApi.tune(selected.id, { new_parameters: parsed, change_description: desc || 'Manual tuning' });
    await loadRules();
    await openRule(selected.id);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <Sliders className="h-6 w-6 text-primary" /> Detection Rule Tuning
        </h1>
        <p className="text-sm text-gray-500">Monitor rule effectiveness and reduce false positives.</p>
      </div>

      <div className="card overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Rule</th>
              <th className="px-4 py-3">v</th>
              <th className="px-4 py-3">Total Alerts</th>
              <th className="px-4 py-3">Confirmed</th>
              <th className="px-4 py-3">False Positives</th>
              <th className="px-4 py-3">FP Rate</th>
              <th className="px-4 py-3">Effectiveness</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rules.map((r) => (
              <tr key={r.id} className={cn('cursor-pointer hover:bg-gray-50', selected?.id === r.id && 'bg-primary/5')} onClick={() => openRule(r.id)}>
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{r.name}</p>
                  <p className="text-xs text-gray-400">{r.rule_code}</p>
                </td>
                <td className="px-4 py-3 text-gray-500">{r.version}</td>
                <td className="px-4 py-3">{r.stats?.total_alerts ?? 0}</td>
                <td className="px-4 py-3 text-emerald-600">{r.stats?.confirmed_incidents ?? 0}</td>
                <td className="px-4 py-3 text-red-600">{r.stats?.false_positives ?? 0}</td>
                <td className="px-4 py-3">{r.stats?.false_positive_rate ?? 0}%</td>
                <td className={cn('px-4 py-3 font-semibold', effColor(r.stats?.effectiveness_score ?? 100))}>
                  {r.stats?.effectiveness_score ?? 100}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card p-6">
            <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-900">
              <ShieldCheck className="h-5 w-5 text-emerald-500" /> {selected.name}
            </h2>
            <p className="mb-3 text-sm text-gray-500">{selected.description}</p>
            <h3 className="text-sm font-semibold text-gray-700">Suggested improvements</h3>
            <ul className="mt-1 list-inside list-disc space-y-1 text-sm text-gray-600">
              {selected.suggested_improvements.map((s, i) => <li key={i}>{s}</li>)}
            </ul>

            <h3 className="mt-4 flex items-center gap-1 text-sm font-semibold text-gray-700">
              <TrendingDown className="h-4 w-4" /> Tuning history
            </h3>
            <div className="mt-1 space-y-2">
              {selected.tuning_history.length === 0 && <p className="text-sm text-gray-400">No tuning yet.</p>}
              {selected.tuning_history.map((h) => (
                <div key={h.id} className="rounded-lg border p-2 text-xs text-gray-600">
                  <b>v{h.version}</b> · {formatDateTime(h.created_at)} — {h.change_description}
                </div>
              ))}
            </div>

            {isAdmin && (
              <div className="mt-4 border-t pt-4">
                <h3 className="text-sm font-semibold text-gray-700">Apply tuning (admin)</h3>
                <textarea className="input mt-2 w-full font-mono text-xs" rows={5} value={params} onChange={(e) => setParams(e.target.value)} />
                <input className="input mt-2 w-full" placeholder="Change description" value={desc} onChange={(e) => setDesc(e.target.value)} />
                {err && <p className="mt-1 text-xs text-red-600">{err}</p>}
                <button className="btn-primary mt-2 w-full" onClick={applyTuning}>Save new version</button>
              </div>
            )}
          </div>

          <div className="card p-6">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">False positives for this rule</h2>
            <div className="space-y-2">
              {fps.length === 0 && <p className="text-sm text-gray-400">No false positives recorded.</p>}
              {fps.map((f) => (
                <div key={f.id} className="rounded-lg border p-3 text-sm">
                  <p className="font-medium text-gray-800">{fpReasonLabels[f.reason]}</p>
                  {f.root_cause && <p className="text-gray-600">{f.root_cause}</p>}
                  <p className="mt-1 text-xs text-gray-400">Ticket INC-{f.ticket_id} · {formatDateTime(f.created_at)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
