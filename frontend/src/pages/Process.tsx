/**
 * Showcase pipeline — the legacy "Process" tab.
 * Uploads go to /api/process/start, then the job id is polled until the ZIP is
 * ready. Watermark settings come from the shared panel.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Download, Film, Layers } from 'lucide-react';
import { api } from '../api';
import { Button, Field, Panel, Progress, SectionTitle, Select, Status, Toggle, Uploader } from '../ui';
import { WatermarkPanel, defaultWm, wmToForm, type Wm } from '../watermark';
import type { T } from '../i18n';

type JobState = { id: string; progress: number; state: string; msg?: string };

export function Process({ t, isPro }: { t: T; isPro: boolean }) {
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState('workshop');
  const [allModes, setAllModes] = useState(false);
  const [fps, setFps] = useState(12);
  const [size, setSize] = useState(750);
  const [encoder, setEncoder] = useState('gifski');
  const [wm, setWm] = useState<Wm>(defaultWm);

  const [job, setJob] = useState<JobState | null>(null);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [ready, setReady] = useState<string>('');
  const poll = useRef<number | null>(null);

  // Stop polling when the component goes away mid-job.
  useEffect(() => () => {
    if (poll.current) clearInterval(poll.current);
  }, []);

  async function start() {
    if (!files.length) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setReady('');
    setMsg(t('processing'));
    setKind('busy');

    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    fd.append('mode', mode);
    fd.append('all_modes', allModes ? '1' : '0');
    fd.append('fps', String(fps));
    fd.append('size', String(size));
    fd.append('gif_encoder', encoder);
    wmToForm(fd, wm);

    try {
      const r = await api.processStart(fd);
      const id = r.job_id || r.id;
      if (!id) throw new Error(r.msg || 'no job id');
      setJob({ id, progress: 0, state: 'queued' });

      poll.current = window.setInterval(async () => {
        try {
          // main.py reports {status, pct, stage, error, download} — not
          // {state, progress}. Reading the wrong keys left the bar at 0 and
          // surfaced a bogus "internal error".
          const s = await api.processStatus(id);
          const st = String(s.status || '').toLowerCase();
          setJob({
            id,
            progress: Number(s.pct || 0),
            state: String(s.stage || st),
            msg: s.error || undefined,
          });
          if (st === 'done') {
            if (poll.current) clearInterval(poll.current);
            setReady(s.download || api.processDownloadUrl(id));
            setMsg(t('done'));
            setKind('ok');
          } else if (st === 'error' || s.error) {
            if (poll.current) clearInterval(poll.current);
            setMsg(s.error || t('error'));
            setKind('err');
          }
        } catch (e: any) {
          if (poll.current) clearInterval(poll.current);
          setMsg(e.message || t('error'));
          setKind('err');
        }
      }, 1200);
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[400px_1fr]">
      <Panel className="thin-scroll max-h-[calc(100vh-190px)] overflow-auto">
        <SectionTitle>{t('settings')}</SectionTitle>

        <Uploader
          title={t('upload')}
          hint={t('upload_hint')}
          accept="image/*,video/*,.gif"
          multiple
          file={files[0] || null}
          onFile={() => setFiles([])}
          onFiles={(f) => setFiles(f)}
        />
        {files.length > 1 && (
          <p className="mt-2 text-[11px] text-white/40">
            {files.length} {t('more').toLowerCase()}
          </p>
        )}

        <div className="mt-5 grid gap-4">
          <Field label={t('mode')}>
            <Select value={mode} onChange={(e) => setMode(e.target.value)} disabled={allModes}>
              <option value="workshop">{t('mode_workshop')}</option>
              <option value="featured">{t('mode_featured')}</option>
              <option value="split">{t('mode_split')}</option>
            </Select>
          </Field>
          <Toggle label={t('all_modes')} checked={allModes} onChange={setAllModes} />

          <div className="grid grid-cols-2 gap-3">
            <Field label={t('fps')}>
              <Select value={fps} onChange={(e) => setFps(Number(e.target.value))}>
                {[8, 10, 12, 15, 20, 24, 30].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t('size')}>
              <Select value={size} onChange={(e) => setSize(Number(e.target.value))}>
                {[630, 640, 750, 800, 1920].map((v) => (
                  <option key={v} value={v}>
                    {v} px
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field label={t('encoder')}>
            <Select value={encoder} onChange={(e) => setEncoder(e.target.value)}>
              <option value="gifski">gifski</option>
              <option value="ffmpeg">ffmpeg</option>
              <option value="pillow">pillow</option>
            </Select>
          </Field>
        </div>

        <div className="my-5 h-px bg-white/10" />
        <SectionTitle>{t('wm')}</SectionTitle>
        <WatermarkPanel wm={wm} setWm={setWm} file={files[0] || null} isPro={isPro} t={t} />

        <Button className="mt-6 w-full" onClick={start} busy={kind === 'busy'}>
          {t('start')}
        </Button>
        <Status text={msg} kind={kind} />
      </Panel>

      <Panel className="grid min-h-[520px] place-items-center">
        {ready ? (
          <div className="text-center">
            <Download className="mx-auto mb-5 text-cyan" size={46} />
            <h3 className="font-podium text-2xl uppercase tracking-wide">{t('done')}</h3>
            <p className="mx-auto mt-3 max-w-sm text-sm text-white/45">
              {t('mode')}: {allModes ? 'workshop + featured + split' : mode}
            </p>
            <a href={ready} download>
              <Button className="mt-6">{t('download')} ZIP</Button>
            </a>
          </div>
        ) : job ? (
          <div className="w-full max-w-md text-center">
            <Layers className="mx-auto mb-5 animate-pulse text-cyan" size={46} />
            <Progress value={job.progress} />
            <p className="mt-3 text-sm text-white/50">
              {job.msg || job.state} — {Math.round(job.progress)}%
            </p>
          </div>
        ) : (
          <div className="max-w-md p-6 text-center text-white/35">
            <Film className="mx-auto mb-4" size={46} />
            <p className="text-sm leading-relaxed">
              {t('d_process')}
              <br />
              PNG, JPG, GIF, MP4, WebM.
            </p>
          </div>
        )}
      </Panel>
    </div>
  );
}
