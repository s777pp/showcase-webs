/** Tools hub + the compact single-purpose media tools ported from app.html. */
import React, { useEffect, useState } from 'react';
import {
  ChevronRight,
  Download as DownloadIcon,
  Image as ImageIcon,
  Layers,
  Link as LinkIcon,
  Palette,
  Repeat,
  Sparkles,
  User,
  Wand2,
} from 'lucide-react';
import { api, saveBlob } from '../api';
import { Button, Empty, Field, Input, Panel, SectionTitle, Select, Status, Uploader } from '../ui';
import { go, TOOLS } from '../routes';
import type { T } from '../i18n';

const ICONS: Record<string, any> = {
  builder: Layers,
  process: ImageIcon,
  mockup: User,
  backgrounds: Palette,
  optimizer: Sparkles,
  achievements: Wand2,
  converter: Repeat,
  upscale: Wand2,
  hex: Palette,
  download: LinkIcon,
  steam: User,
  deviantart: ImageIcon,
};

/** Card grid linking to every tool. */
export function ToolsHub({ t }: { t: T }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {TOOLS.filter((x) => x.hub).map((x) => {
        const Icon = ICONS[x.slug] || Sparkles;
        return (
          <button
            key={x.slug}
            onClick={() => go('/' + x.slug)}
            className="glass group min-h-44 rounded-3xl p-6 text-left transition hover:-translate-y-1 hover:border-cyan/30"
          >
            <Icon className="mb-7 text-cyan" size={26} />
            <h2 className="font-podium text-xl uppercase tracking-wide">{t(x.key)}</h2>
            <p className="mt-2 text-sm leading-relaxed text-white/45">{t(x.desc)}</p>
            <ChevronRight className="ml-auto mt-5 text-white/25 transition group-hover:translate-x-1 group-hover:text-cyan" />
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Converter — /api/convert                                            */
/* ------------------------------------------------------------------ */
export function Converter({ t }: { t: T }) {
  const [file, setFile] = useState<File | null>(null);
  const [target, setTarget] = useState('gif');
  const [fps, setFps] = useState(12);
  const [width, setWidth] = useState(0);
  const [duration, setDuration] = useState(0);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  async function run() {
    if (!file) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('target', target);
      fd.append('fps', String(fps));
      fd.append('width', String(width));
      fd.append('duration', String(duration));
      await saveBlob(await api.convert(fd), `converted.${target}`);
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <ToolLayout
      t={t}
      icon={Repeat}
      title={t('t_converter')}
      desc={t('d_converter')}
      side={
        <>
          <Uploader title={t('upload')} hint={t('upload_hint')} file={file} onFile={setFile} />
          <div className="mt-4 grid gap-4">
            <Field label="→">
              <Select value={target} onChange={(e) => setTarget(e.target.value)}>
                {['gif', 'mp4', 'webm', 'png', 'jpg', 'webp'].map((v) => (
                  <option key={v} value={v}>
                    {v.toUpperCase()}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t('fps')}>
                <Input type="number" value={fps} onChange={(e) => setFps(Number(e.target.value))} />
              </Field>
              <Field label={`${t('size')} (0 = auto)`}>
                <Input type="number" value={width} onChange={(e) => setWidth(Number(e.target.value))} />
              </Field>
            </div>
            <Field label="Duration, s (0 = full)">
              <Input
                type="number"
                step="0.1"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
              />
            </Field>
          </div>
          <Button className="mt-5 w-full" onClick={run} busy={busy}>
            {t('start')}
          </Button>
          <Status text={msg} kind={kind} />
        </>
      }
    />
  );
}

/* ------------------------------------------------------------------ */
/* HEX21 — /api/hex21                                                  */
/* ------------------------------------------------------------------ */
export function Hex({ t }: { t: T }) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  async function run() {
    if (!files.length) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append('files', f));
      await saveBlob(await api.hex21(fd), 'hex21.zip');
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <ToolLayout
      t={t}
      icon={Palette}
      title={t('t_hex')}
      desc={t('d_hex')}
      side={
        <>
          <Uploader
            title={t('upload')}
            hint="PNG / GIF"
            accept="image/png,image/gif,.png,.gif"
            multiple
            file={files[0] || null}
            onFile={() => setFiles([])}
            onFiles={setFiles}
          />
          {files.length > 1 && <p className="mt-2 text-[11px] text-white/40">{files.length}</p>}
          <Button className="mt-5 w-full" onClick={run} busy={busy}>
            {t('start')}
          </Button>
          <Status text={msg} kind={kind} />
        </>
      }
    />
  );
}

/* ------------------------------------------------------------------ */
/* Upscale — /api/upscale (Pro only, enforced server-side)             */
/* ------------------------------------------------------------------ */
export function Upscale({ t }: { t: T }) {
  const [file, setFile] = useState<File | null>(null);
  const [model, setModel] = useState('4xBHI_dat2_real');
  const [models, setModels] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  useEffect(() => {
    api
      .upscaleModels()
      .then((r) => {
        const list = (r.models || r.items || []).map((m: any) => (typeof m === 'string' ? m : m.id || m.name));
        setModels(list.filter(Boolean));
      })
      .catch(() => setModels([]));
  }, []);

  async function run() {
    if (!file) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('model', model);
      await saveBlob(await api.upscale(fd), 'upscaled.png');
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <ToolLayout
      t={t}
      icon={Wand2}
      title={t('t_upscale')}
      desc={t('d_upscale')}
      side={
        <>
          <Uploader
            title={t('upload')}
            hint="PNG / JPG / WebP · max 15 MB"
            accept="image/*"
            file={file}
            onFile={setFile}
          />
          <div className="mt-4">
            <Field label="Model">
              {models.length ? (
                <Select value={model} onChange={(e) => setModel(e.target.value)}>
                  {models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input value={model} onChange={(e) => setModel(e.target.value)} />
              )}
            </Field>
          </div>
          <Button className="mt-5 w-full" onClick={run} busy={busy}>
            {t('start')}
          </Button>
          <Status text={msg} kind={kind} />
        </>
      }
    />
  );
}

/* ------------------------------------------------------------------ */
/* Download by URL — /api/download-url                                 */
/* ------------------------------------------------------------------ */
export function DownloadUrl({ t }: { t: T }) {
  const [url, setUrl] = useState('');
  const [quality, setQuality] = useState('best');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [result, setResult] = useState<{ download?: string; name?: string } | null>(null);

  async function run() {
    if (!url.startsWith('http')) {
      setMsg('http(s)://…');
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    setResult(null);
    try {
      const r = await api.downloadUrl(url, quality);
      setResult(r);
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <ToolLayout
      t={t}
      icon={LinkIcon}
      title={t('t_download')}
      desc={t('d_download')}
      side={
        <>
          <Field label="URL">
            <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
          </Field>
          <div className="mt-4">
            <Field label="Quality">
              <Select value={quality} onChange={(e) => setQuality(e.target.value)}>
                <option value="best">best</option>
                <option value="1080">1080p</option>
                <option value="720">720p</option>
                <option value="480">480p</option>
              </Select>
            </Field>
          </div>
          <Button className="mt-5 w-full" onClick={run} busy={busy}>
            {t('start')}
          </Button>
          <Status text={msg} kind={kind} />
          {result?.download && (
            <a href={result.download} download={result.name || ''}>
              <Button variant="outline" className="mt-3 w-full">
                <DownloadIcon size={14} />
                {t('download')}
              </Button>
            </a>
          )}
        </>
      }
    />
  );
}

/* ------------------------------------------------------------------ */
/* Shared two-column tool scaffold                                     */
/* ------------------------------------------------------------------ */
function ToolLayout({
  t,
  icon: Icon,
  title,
  desc,
  side,
  children,
}: {
  t: T;
  icon: any;
  title: string;
  desc: string;
  side: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <Panel className="thin-scroll max-h-[calc(100vh-190px)] overflow-auto">
        <Icon className="mb-5 text-cyan" size={28} />
        <SectionTitle>{title}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{desc}</p>
        {side}
      </Panel>
      <Panel className="grid min-h-[480px] place-items-center">
        {children || <Empty text={desc} />}
      </Panel>
    </div>
  );
}

export { ToolLayout };
