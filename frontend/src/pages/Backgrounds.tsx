/** Steam background catalog — searches /api/steam/backgrounds (Steam Market, cached). */
import React, { useEffect, useState } from 'react';
import { ArrowUpRight, Palette, Search } from 'lucide-react';
import { api } from '../api';
import { Button, Empty, Field, Input, Panel, Select, Spinner, Status } from '../ui';
import { go } from '../routes';
import type { T } from '../i18n';

type Bg = {
  name: string;
  game?: string;
  image?: string;
  animated?: boolean;
  price?: string;
  market_url?: string;
};

export function Backgrounds({ t }: { t: T }) {
  const [q, setQ] = useState('');
  const [kind, setKind] = useState('all');
  const [page, setPage] = useState(0);
  const [items, setItems] = useState<Bg[]>([]);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState('');
  const [total, setTotal] = useState(0);

  async function load(next = 0, query = q, k = kind) {
    setBusy(true);
    setErr('');
    try {
      const r = await api.backgrounds(query, next, k);
      setItems(r.items || []);
      setTotal(Number(r.total || 0));
      setPage(next);
    } catch (e: any) {
      setErr(e.message || t('error'));
      setItems([]);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Hand the chosen background to the builder through sessionStorage. */
  function useInBuilder(b: Bg) {
    if (!b.image) return;
    try {
      sessionStorage.setItem('sm_pick_bg', b.image);
    } catch {
      /* private mode */
    }
    go('/builder');
  }

  return (
    <div>
      <Panel className="mb-5">
        <div className="grid gap-3 sm:grid-cols-[1fr_180px_auto] sm:items-end">
          <Field label={t('bg_search')}>
            <div className="relative">
              <Search className="absolute left-3 top-3 text-white/30" size={16} />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && load(0)}
                placeholder={t('bg_search')}
                className="pl-9"
              />
            </div>
          </Field>
          <Field label={t('bg_kind')}>
            <Select
              value={kind}
              onChange={(e) => {
                setKind(e.target.value);
                load(0, q, e.target.value);
              }}
            >
              <option value="all">{t('bg_all')}</option>
              <option value="static">{t('bg_static')}</option>
              <option value="animated">{t('bg_animated')}</option>
            </Select>
          </Field>
          <Button onClick={() => load(0)} busy={busy}>
            {t('search')}
          </Button>
        </div>
        <Status text={err} kind={err ? 'err' : undefined} />
      </Panel>

      {busy ? (
        <Spinner text={t('loading')} />
      ) : !items.length ? (
        <Empty text={t('empty')} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((b, i) => (
            <article key={(b.market_url || '') + i} className="glass group overflow-hidden rounded-2xl">
              <div className="checker relative aspect-video overflow-hidden bg-black/40">
                {b.image ? (
                  <img
                    src={b.image}
                    alt={b.name}
                    loading="lazy"
                    className="h-full w-full object-cover transition group-hover:scale-105"
                  />
                ) : (
                  <div className="grid h-full place-items-center text-white/20">
                    <Palette />
                  </div>
                )}
                {b.animated && (
                  <span className="absolute left-2 top-2 rounded-full bg-cyan/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-black">
                    GIF
                  </span>
                )}
              </div>
              <div className="p-4">
                <h3 className="truncate text-sm font-semibold" title={b.name}>
                  {b.name}
                </h3>
                {b.game && <p className="mt-1 truncate text-[11px] text-white/40">{b.game}</p>}
                <div className="mt-4 flex items-center justify-between gap-2">
                  <button
                    onClick={() => useInBuilder(b)}
                    className="rounded-full bg-white/10 px-3 py-1.5 text-[11px] uppercase tracking-wider text-white/80 transition hover:bg-cyan hover:text-black"
                  >
                    {t('bg_use')}
                  </button>
                  {b.market_url && (
                    <a
                      href={b.market_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="rounded-full border border-white/15 p-2 text-white/60 transition hover:text-white"
                      title={t('bg_open')}
                    >
                      <ArrowUpRight size={14} />
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {!busy && items.length > 0 && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <Button variant="outline" disabled={page === 0} onClick={() => load(page - 1)}>
            ←
          </Button>
          <span className="px-3 text-sm text-white/45">
            {page + 1}
            {total ? ` / ${Math.max(1, Math.ceil(total / 24))}` : ''}
          </span>
          <Button variant="outline" onClick={() => load(page + 1)}>
            →
          </Button>
        </div>
      )}
    </div>
  );
}
