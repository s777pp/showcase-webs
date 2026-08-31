/**
 * Achievement showcase helper — pick achievements from a game and compose the
 * line that goes into the Steam achievement showcase.
 * Data comes from /api/steam/achievements/{appid} (public pages, cached).
 */
import React, { useState } from 'react';
import { Check, Copy, Trophy } from 'lucide-react';
import { api } from '../api';
import { Button, Empty, Field, Input, Panel, SectionTitle, Spinner, Status } from '../ui';
import type { T } from '../i18n';

type Ach = { name: string; description?: string; image?: string; percent?: string };

export function Achievements({ t }: { t: T }) {
  const [appid, setAppid] = useState('730');
  const [filter, setFilter] = useState('');
  const [items, setItems] = useState<Ach[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [copied, setCopied] = useState(false);

  async function load() {
    if (!appid.trim()) return;
    setBusy(true);
    setMsg(t('loading'));
    setKind('busy');
    setPicked([]);
    try {
      const r = await api.achievements(appid.trim());
      setItems(r.items || []);
      setMsg(r.items?.length ? '' : t('empty'));
      setKind(r.items?.length ? undefined : 'err');
    } catch (e: any) {
      setItems([]);
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  const shown = items.filter(
    (x) => !filter || x.name.toLowerCase().includes(filter.toLowerCase()),
  );

  function toggle(name: string) {
    setPicked((p) => (p.includes(name) ? p.filter((x) => x !== name) : [...p, name]));
    setCopied(false);
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(picked.join(' '));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked */
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <Panel className="h-fit">
        <Trophy className="mb-5 text-cyan" size={28} />
        <SectionTitle>{t('t_achievements')}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{t('ach_hint')}</p>

        <div className="grid gap-4">
          <Field label={t('ach_appid')} hint="CS2 = 730, Dota 2 = 570, TF2 = 440">
            <Input
              value={appid}
              onChange={(e) => setAppid(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && load()}
              placeholder="730"
            />
          </Field>
          <Button onClick={load} busy={busy}>
            {t('ach_load')}
          </Button>
          {items.length > 0 && (
            <Field label={t('ach_filter')}>
              <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="A, S, Love…" />
            </Field>
          )}
        </div>
        <Status text={msg} kind={kind} />

        {picked.length > 0 && (
          <div className="mt-6 border-t border-white/10 pt-5">
            <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-white/45">
              {t('ach_picked')}: {picked.length}
            </div>
            <div className="thin-scroll max-h-40 overflow-auto rounded-xl border border-white/10 bg-black/30 p-3 text-sm leading-relaxed text-white/80">
              {picked.join(' ')}
            </div>
            <Button variant="outline" className="mt-3 w-full" onClick={copy}>
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? t('done') : 'Copy'}
            </Button>
            <button
              onClick={() => setPicked([])}
              className="mt-2 w-full text-[11px] text-white/40 underline hover:text-white/70"
            >
              {t('reset')}
            </button>
          </div>
        )}
      </Panel>

      <div>
        {busy ? (
          <Spinner text={t('loading')} />
        ) : !shown.length ? (
          <Empty text={t('empty')} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {shown.map((a, i) => {
              const on = picked.includes(a.name);
              return (
                <button
                  key={a.name + i}
                  onClick={() => toggle(a.name)}
                  className={`glass flex gap-3 rounded-2xl p-3 text-left transition ${
                    on ? 'border-cyan/50 bg-cyan/10' : 'hover:border-white/25'
                  }`}
                >
                  {a.image ? (
                    <img src={a.image} alt="" loading="lazy" className="h-14 w-14 shrink-0 rounded-lg object-cover" />
                  ) : (
                    <div className="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-white/5 text-white/25">
                      <Trophy size={18} />
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate text-sm font-semibold">{a.name}</h3>
                    {a.description && (
                      <p className="line-clamp-2 mt-1 text-[11px] leading-snug text-white/40">
                        {a.description}
                      </p>
                    )}
                    {a.percent && <span className="mt-1 block text-[10px] text-cyan">{a.percent}</span>}
                  </div>
                  {on && <Check size={16} className="shrink-0 text-cyan" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
