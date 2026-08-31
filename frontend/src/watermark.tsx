/**
 * Watermark controls + drag-positionable live preview.
 *
 * Mirrors the parameters main.py accepts (wm_text, wm_font, wm_opacity,
 * wm_enable, wm_corner, wm_scale, wm_color, wm_x, wm_y, auto_contrast) and
 * renders the server preview from /api/preview_wm.
 *
 * On the free plan the server forces its own mark, so the controls lock and a
 * note explains why instead of letting the user fiddle with settings that will
 * be overridden.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Lock } from 'lucide-react';
import { api } from './api';
import { Field, Input, Range, Select, Toggle, useObjectUrl } from './ui';
import type { T } from './i18n';

export type Wm = {
  enable: boolean;
  text: string;
  font: string;
  opacity: number;
  color: string;
  corner: string;
  scale: number;
  x: string; // '' = use corner anchor, otherwise 0..1
  y: string;
  autoContrast: boolean;
};

export const defaultWm: Wm = {
  enable: true,
  text: 'Showcase Maker',
  font: 'lap',
  opacity: 22,
  color: '#ffffff',
  corner: 'bl',
  scale: 1,
  x: '',
  y: '',
  autoContrast: false,
};

/** Serialise into the exact field names the backend expects. */
export function wmToForm(fd: FormData, wm: Wm) {
  fd.append('wm_enable', wm.enable ? '1' : '0');
  fd.append('wm_text', wm.text);
  fd.append('wm_font', wm.font);
  fd.append('wm_opacity', String(Math.round(wm.opacity)));
  fd.append('wm_color', wm.color);
  fd.append('wm_corner', wm.corner);
  fd.append('wm_scale', String(wm.scale));
  fd.append('wm_x', wm.x);
  fd.append('wm_y', wm.y);
  fd.append('auto_contrast', wm.autoContrast ? '1' : '0');
}

export function WatermarkPanel({
  wm,
  setWm,
  file,
  isPro,
  t,
}: {
  wm: Wm;
  setWm: (w: Wm) => void;
  file: File | null;
  isPro: boolean;
  t: T;
}) {
  const [blob, setBlob] = useState<Blob | null>(null);
  const [busy, setBusy] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const url = useObjectUrl(blob);
  const set = (patch: Partial<Wm>) => setWm({ ...wm, ...patch });

  // Debounced server preview — the mark is rendered by Pillow, not CSS, so what
  // you see is what the export produces.
  useEffect(() => {
    if (!file) {
      setBlob(null);
      return;
    }
    let dead = false;
    const timer = setTimeout(async () => {
      setBusy(true);
      try {
        const fd = new FormData();
        fd.append('file', file);
        wmToForm(fd, wm);
        const res = await api.previewWm(fd);
        if (!res.ok) throw new Error('preview failed');
        const b = await res.blob();
        if (!dead) setBlob(b);
      } catch {
        if (!dead) setBlob(null);
      } finally {
        if (!dead) setBusy(false);
      }
    }, 350);
    return () => {
      dead = true;
      clearTimeout(timer);
    };
  }, [file, wm]);

  // Click / drag on the preview sets a normalised 0..1 position.
  const place = useCallback(
    (e: React.MouseEvent) => {
      const box = boxRef.current;
      if (!box || !file) return;
      const r = box.getBoundingClientRect();
      const nx = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
      const ny = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height));
      set({ x: nx.toFixed(4), y: ny.toFixed(4) });
    },
    [file, wm],
  );

  const locked = !isPro;

  return (
    <div className="grid gap-4">
      {locked && (
        <div className="flex items-start gap-2.5 rounded-2xl border border-cyan/25 bg-cyan/8 p-3.5 text-[11px] leading-snug text-cyan/90">
          <Lock size={14} className="mt-0.5 shrink-0" />
          <span>{t('wm_locked')}</span>
        </div>
      )}

      <Toggle
        label={t('wm_on')}
        checked={locked ? true : wm.enable}
        onChange={(v) => set({ enable: v })}
        disabled={locked}
      />

      <Field label={t('wm_text')}>
        <Input
          value={locked ? 'Showcase Maker' : wm.text}
          disabled={locked}
          onChange={(e) => set({ text: e.target.value })}
          placeholder="Showcase Maker"
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label={t('wm_font')}>
          <Select value={wm.font} disabled={locked} onChange={(e) => set({ font: e.target.value })}>
            <option value="lap">Lapsus</option>
            <option value="mont">Montserrat</option>
            <option value="mulish">Mulish</option>
          </Select>
        </Field>
        <Field label={t('wm_corner')}>
          <Select
            value={wm.corner}
            disabled={locked}
            onChange={(e) => set({ corner: e.target.value, x: '', y: '' })}
          >
            <option value="tl">{t('corner_tl')}</option>
            <option value="tr">{t('corner_tr')}</option>
            <option value="bl">{t('corner_bl')}</option>
            <option value="br">{t('corner_br')}</option>
          </Select>
        </Field>
      </div>

      <Range
        label={t('wm_opacity')}
        value={wm.opacity}
        min={0}
        max={100}
        suffix="%"
        onChange={(v) => set({ opacity: v })}
      />
      <Range
        label={t('wm_scale')}
        value={wm.scale}
        min={0.4}
        max={2.5}
        step={0.05}
        suffix="×"
        onChange={(v) => set({ scale: v })}
      />

      <div className="grid grid-cols-2 items-end gap-3">
        <Field label={t('wm_color')}>
          <input
            type="color"
            value={wm.color}
            disabled={locked}
            onChange={(e) => set({ color: e.target.value })}
            className="h-11 w-full cursor-pointer rounded-xl border border-white/12 bg-black/35 p-1"
          />
        </Field>
        <Toggle
          label={t('auto_contrast')}
          checked={wm.autoContrast}
          onChange={(v) => set({ autoContrast: v })}
        />
      </div>

      {file && (
        <div className="grid gap-2">
          <span className="text-[10px] uppercase tracking-[0.18em] text-white/45">
            {t('preview')} — {t('wm_drag')}
          </span>
          <div
            ref={boxRef}
            onClick={place}
            className="checker relative grid min-h-40 cursor-crosshair place-items-center overflow-hidden rounded-2xl border border-white/12 bg-black/40"
          >
            {url ? (
              <img src={url} alt="watermark preview" className="max-h-[46vh] w-full object-contain" />
            ) : (
              <span className="p-8 text-xs text-white/35">
                {busy ? t('loading') : t('preview')}
              </span>
            )}
            {busy && url && (
              <span className="absolute right-2 top-2 rounded-full bg-black/70 px-2 py-1 text-[10px] text-white/60">
                {t('loading')}
              </span>
            )}
          </div>
          {(wm.x || wm.y) && (
            <button
              onClick={() => set({ x: '', y: '' })}
              className="justify-self-start text-[11px] text-white/40 underline hover:text-white/70"
            >
              {t('reset')} → {t('wm_corner')}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
