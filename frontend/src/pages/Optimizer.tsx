/** GIF optimizer — wraps /api/optimizer, which reuses processor.ensure_under_mb. */
import React, { useState } from 'react';
import { Sparkles, Download } from 'lucide-react';
import { api, saveBlob } from '../api';
import { Button, Field, Panel, Range, SectionTitle, Select, Status, Toggle, Uploader } from '../ui';
import type { T } from '../i18n';

export function Optimizer({ t }: { t: T }) {
  const [file, setFile] = useState<File | null>(null);
  const [targetMb, setTargetMb] = useState(5);
  const [fps, setFps] = useState(0); // 0 = keep source
  const [width, setWidth] = useState(0); // 0 = keep source
  const [lossy, setLossy] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [stats, setStats] = useState<{ before: number; after: number } | null>(null);

  async function run() {
    if (!file) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    setStats(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('target_mb', String(targetMb));
      fd.append('fps', String(fps));
      fd.append('width', String(width));
      fd.append('lossy', lossy ? '1' : '0');
      const res = await api.optimize(fd);
      if (!res.ok) {
        const txt = await res.text();
        let m = `HTTP ${res.status}`;
        try {
          m = JSON.parse(txt).msg || m;
        } catch {
          /* not json */
        }
        throw new Error(m);
      }
      const blob = await res.blob();
      setStats({ before: file.size, after: blob.size });
      await saveBlob(new Response(blob, { status: 200 }), `optimized_${file.name.replace(/\.[^.]+$/, '')}.gif`);
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  const mb = (n: number) => (n / 1024 / 1024).toFixed(2) + ' MB';

  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <Panel>
        <Sparkles className="mb-5 text-cyan" size={28} />
        <SectionTitle>{t('t_optimizer')}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{t('opt_hint')}</p>

        <Uploader
          title={t('upload')}
          hint="GIF"
          accept="image/gif,.gif"
          file={file}
          onFile={(f) => {
            setFile(f);
            setStats(null);
          }}
        />

        <div className="mt-5 grid gap-4">
          <Range
            label={t('opt_target')}
            value={targetMb}
            min={0.5}
            max={20}
            step={0.5}
            suffix=" MB"
            onChange={setTargetMb}
          />
          <div className="grid grid-cols-2 gap-3">
            <Field label={`${t('fps')} (0 = auto)`}>
              <Select value={fps} onChange={(e) => setFps(Number(e.target.value))}>
                {[0, 8, 10, 12, 15, 20, 24].map((v) => (
                  <option key={v} value={v}>
                    {v || 'auto'}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={`${t('size')} (0 = auto)`}>
              <Select value={width} onChange={(e) => setWidth(Number(e.target.value))}>
                {[0, 320, 506, 630, 750, 1000].map((v) => (
                  <option key={v} value={v}>
                    {v ? v + ' px' : 'auto'}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <Toggle label="Lossy" checked={lossy} onChange={setLossy} />
        </div>

        <Button className="mt-6 w-full" onClick={run} busy={busy}>
          {t('start')}
        </Button>
        <Status text={msg} kind={kind} />
      </Panel>

      <Panel className="grid min-h-[480px] place-items-center">
        {stats ? (
          <div className="text-center">
            <Download className="mx-auto mb-6 text-cyan" size={46} />
            <div className="flex items-center justify-center gap-6">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-white/40">before</div>
                <b className="font-inter text-2xl">{mb(stats.before)}</b>
              </div>
              <div className="text-2xl text-white/25">→</div>
              <div>
                <div className="text-[10px] uppercase tracking-widest text-cyan/70">after</div>
                <b className="font-inter text-2xl text-cyan">{mb(stats.after)}</b>
              </div>
            </div>
            <p className="mt-4 text-sm text-white/45">
              −{Math.max(0, Math.round((1 - stats.after / stats.before) * 100))}%
            </p>
          </div>
        ) : (
          <div className="max-w-sm p-6 text-center text-white/35">
            <Sparkles className="mx-auto mb-4" size={46} />
            <p className="text-sm leading-relaxed">{t('d_optimizer')}</p>
          </div>
        )}
      </Panel>
    </div>
  );
}
