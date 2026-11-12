import { FormEvent, useState } from 'react';
import { api, Machine, Scenario, Challenge } from './client';
import { SelectorMaquina } from './SelectorMaquina';

export function FormularioReto({ machines, scenarios, onSaved, onBusyChange }: { machines: Machine[]; scenarios: Scenario[]; onSaved: (challenge: Challenge) => Promise<void>; onBusyChange?: (busy: boolean) => void }) {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [difficulty, setDifficulty] = useState('medio');
  const [victim, setVictim] = useState('');
  const [strategy, setStrategy] = useState('SSH-PASSWORD-LAB');
  const [points, setPoints] = useState(250);
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [duration, setDuration] = useState('');
  const [hints, setHints] = useState(['', '', '']);
  const [resourceTitle, setResourceTitle] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');
  const [unique, setUnique] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const scenario = scenarios.find(s => s.strategy === strategy);
  const valid = /^[A-Z0-9_-]{3,40}$/.test(code) && unique === code && name.trim().length >= 3 && victim && points > 0;
  async function checkCode(value: string) {
    setUnique(null);
    if (!/^[A-Z0-9_-]{3,40}$/.test(value)) { setError('Código: usa 3–40 letras mayúsculas, números, guiones o _.'); return; }
    try {
      const result = await api<{available: boolean}>(`/challenges/code-available?code=${encodeURIComponent(value)}`);
      setUnique(result.available ? value : null);
      setError(result.available ? '' : 'Ese código ya existe.');
    } catch (e) { setError((e as Error).message); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!valid) return; setBusy(true); onBusyChange?.(true); setError('');
    try { const created = await api<Challenge>('/challenges', { code, name, difficulty, victim_id: victim, strategy, points, description, instructions, duration_minutes: duration ? Number(duration) : null, hints: hints.filter(h => h.trim()).map(text => ({text,penalty:0})), resources: resourceUrl ? [{title:resourceTitle,url:resourceUrl}] : [] }); await onSaved(created); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); onBusyChange?.(false); }
  }
  return <form onSubmit={submit} className="fresh-form">
    <p className="fresh-kicker">NUEVO RETO · BORRADOR</p><h2>Prepara una práctica</h2>
    <div className="fresh-grid">
      <label>Código<input placeholder="Ej: ESC-02-BRUTEFORCE" value={code} onChange={e => { const value = e.target.value.toUpperCase(); setCode(value); setUnique(null); const match = scenarios.find(s => s.code === value); if (match) { setStrategy(match.strategy); setDifficulty(match.difficulty); setPoints(match.points); setVictim(''); } }} onBlur={() => void checkCode(code)} required /></label>
      <label>Nombre<input placeholder="Ej: Acceso SSH de práctica" minLength={3} value={name} onChange={e => setName(e.target.value)} required /></label>
      <label>Dificultad<select value={difficulty} onChange={e => { setDifficulty(e.target.value); setPoints(({basico:100,medio:250,avanzado:500})[e.target.value as 'medio']); }}><option value="basico">Básico</option><option value="medio">Medio</option><option value="avanzado">Avanzado</option></select></label>
      <label>Víctima<SelectorMaquina machines={machines.filter(m => scenario?.victims.includes(m.name))} tipo="victima" value={victim} onChange={values => setVictim(values[0])} /></label>
    </div>
    <p>{points} puntos · {strategy}. Se guardará como borrador.</p>
    <details><summary>Opciones avanzadas</summary><div className="fresh-grid">
      <label>Estrategia<select value={strategy} onChange={e => { setStrategy(e.target.value); setVictim(''); }}>{scenarios.map(s => <option key={s.strategy} value={s.strategy}>{s.strategy}{s.enabled ? '' : ' · integración deshabilitada'}</option>)}</select></label>
      <label>Puntos<input type="number" min={1} max={10000} value={points} onChange={e => setPoints(Number(e.target.value))} /></label>
      <label>Descripción<textarea value={description} onChange={e => setDescription(e.target.value)} /></label>
      <label>Instrucciones<textarea value={instructions} onChange={e => setInstructions(e.target.value)} /></label>
      <label>Tiempo en minutos<input type="number" min={5} max={120} value={duration} onChange={e => setDuration(e.target.value)} placeholder="Por dificultad: 30 / 45 / 60" /></label>
      {hints.map((hint, index) => <label key={index}>Pista {index + 1}<textarea value={hint} onChange={e => setHints(values => values.map((v, i) => i === index ? e.target.value : v))} placeholder="Orientación sin revelar la bandera" /></label>)}
      <label>Título del recurso<input value={resourceTitle} onChange={e => setResourceTitle(e.target.value)} minLength={resourceUrl ? 3 : undefined} required={Boolean(resourceUrl)} placeholder="Ej: Introducción a SQL" /></label>
      <label>Recurso educativo HTTPS<input type="url" value={resourceUrl} onChange={e => setResourceUrl(e.target.value)} placeholder="https://..." /></label>
    </div></details>
    {error && <p role="alert" className="fresh-error">{error}</p>}
    <button disabled={!valid || busy}>{busy ? 'Guardando…' : 'Crear borrador'}</button>
  </form>;
}
