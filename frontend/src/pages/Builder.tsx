/**
 * Profile Builder — background + character + text + frame + effects on layers.
 *
 * Live preview is composed in the DOM (fast, animated GIF/video keep playing);
 * the final artwork is rendered server-side by /api/builder/render so chroma
 * key removal, feathering and the watermark match the export exactly.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Download, Eye, Image as ImageIcon, Layers, Save, Sparkles, Type, User, Square } from 'lucide-react';
import { api, saveBlob } from '../api';
import {
  Button,
  Field,
  Input,
  Panel,
  Range,
  SectionTitle,
  Select,
  Status,
  Toggle,
  Uploader,
  useObjectUrl,
} from '../ui';
import { WatermarkPanel, defaultWm, wmToForm, type Wm } from '../watermark';
import { go } from '../routes';
import type { T } from '../i18n';

type Tab = 'bg' | 'char' | 'text' | 'frame' | 'fx';

const SHOWCASE_SIZES = [
  { value: 750, label: 'Workshop — 5 × 150 px (750 px)' },
  { value: 630, label: 'Featured Artwork — 630 px' },
  { value: 606, label: 'Artwork — 506 + 100 px' },
  { value: 640, label: 'Profile crop — 640 px' },
  { value: 800, label: 'Wide — 800 px' },
  { value: 1920, label: 'Source — 1920 px' },
];

const FRAME_PRESETS = [
  { id: 'none', name: 'Без рамки', style: 'none', width: 0, color: '#ffffff' },
  { id: 'steam', name: 'Steam glass', style: 'inset', width: 3, color: '#66c0f4' },
  { id: 'neon', name: 'Neon cyan', style: 'glow', width: 5, color: '#00d2ff' },
  { id: 'violet', name: 'Violet glow', style: 'glow', width: 7, color: '#8b5cf6' },
  { id: 'clean', name: 'Clean white', style: 'solid', width: 2, color: '#ffffff' },
  { id: 'dark', name: 'Dark inset', style: 'inset', width: 10, color: '#111827' },
];

export type Scene = {
  width: number;
  chromaKey: string;
  chromaTol: number;
  feather: number;
  charScale: number;
  charX: number;
  charY: number;
  charRotate: number;
  charOpacity: number;
  text: string;
  textFont: string;
  textSize: number;
  textColor: string;
  textX: number;
  textY: number;
  textShadow: boolean;
  frameStyle: string;
  frameWidth: number;
  frameColor: string;
  vignette: number;
  bgBlur: number;
  bgDim: number;
  fps: number;
};

const defaultScene: Scene = {
  width: 750,
  chromaKey: 'auto',
  chromaTol: 55,
  feather: 1.6,
  charScale: 1,
  charX: 0.5,
  charY: 1,
  charRotate: 0,
  charOpacity: 100,
  text: '',
  textFont: 'mont',
  textSize: 48,
  textColor: '#ffffff',
  textX: 0.5,
  textY: 0.12,
  textShadow: true,
  frameStyle: 'none',
  frameWidth: 6,
  frameColor: '#00d2ff',
  vignette: 0,
  bgBlur: 0,
  bgDim: 0,
  fps: 12,
};

export function Builder({ t, isPro }: { t: T; isPro: boolean }) {
  const [tab, setTab] = useState<Tab>('bg');
  const [bg, setBg] = useState<File | null>(null);
  const [bgUrl, setBgUrl] = useState<string>(''); // background chosen from the catalog
  const [char, setChar] = useState<File | null>(null);
  const [s, setS] = useState<Scene>(defaultScene);
  const [wm, setWm] = useState<Wm>(defaultWm);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  const bgObj = useObjectUrl(bg);
  const charObj = useObjectUrl(char);
  const bgSrc = bgObj || bgUrl;

  const set = (patch: Partial<Scene>) => setS({ ...s, ...patch });

  // A background picked in the catalog hands off through sessionStorage.
  useEffect(() => {
    try {
      const picked = sessionStorage.getItem('sm_pick_bg');
      if (picked) {
        setBgUrl(picked);
        sessionStorage.removeItem('sm_pick_bg');
      }
    } catch {
      /* private mode */
    }
  }, []);

  const frameCss = useMemo(() => {
    if (s.frameStyle === 'none') return {};
    if (s.frameStyle === 'solid')
      return { border: `${s.frameWidth}px solid ${s.frameColor}` };
    if (s.frameStyle === 'glow')
      return {
        border: `${s.frameWidth}px solid ${s.frameColor}`,
        boxShadow: `0 0 ${s.frameWidth * 5}px ${s.frameColor}, inset 0 0 ${s.frameWidth * 4}px ${s.frameColor}55`,
      };
    if (s.frameStyle === 'inset')
      return { boxShadow: `inset 0 0 0 ${s.frameWidth}px ${s.frameColor}` };
    return {};
  }, [s.frameStyle, s.frameWidth, s.frameColor]);

  async function render(download: boolean) {
    if (!bg && !bgUrl) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    try {
      const fd = new FormData();
      if (bg) fd.append('background', bg);
      else fd.append('background_url', bgUrl);
      if (char) fd.append('character', char);
      fd.append('scene', JSON.stringify(s));
      wmToForm(fd, wm);

      const res = await api.builderRender(fd);
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
      const ext = blob.type.includes('gif') ? 'gif' : blob.type.includes('mp4') ? 'mp4' : 'png';
      if (download) {
        const r2 = new Response(blob, { status: 200 });
        await saveBlob(r2, `showcase.${ext}`);
      } else {
        // Hand the result to the showcase slicer.
        try {
          sessionStorage.setItem('sm_builder_done', '1');
        } catch {
          /* ignore */
        }
      }
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  const tabs: [Tab, string, any][] = [
    ['bg', t('layer_bg'), ImageIcon],
    ['char', t('layer_char'), User],
    ['text', t('layer_text'), Type],
    ['frame', t('layer_frame'), Square],
    ['fx', t('layer_fx'), Sparkles],
  ];

  return (
    <div className="grid gap-4 xl:grid-cols-[380px_1fr_240px]">
      {/* ----------------------- controls ----------------------- */}
      <Panel className="thin-scroll max-h-[calc(100vh-190px)] overflow-auto">
        <div className="mb-5 flex flex-wrap gap-2">
          {tabs.map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 rounded-full px-3 py-2 text-[11px] transition ${
                tab === id ? 'bg-white text-black' : 'bg-white/5 text-white/55 hover:text-white'
              }`}
            >
              <Icon size={12} />
              {label}
            </button>
          ))}
        </div>

        {tab === 'bg' && (
          <div className="grid gap-4">
            <Uploader
              title={t('layer_bg')}
              hint="PNG, JPG, GIF, MP4"
              accept="image/*,video/*,.gif"
              file={bg}
              onFile={(f) => {
                setBg(f);
                if (f) setBgUrl('');
              }}
            />
            <Button variant="outline" onClick={() => go('/backgrounds')}>
              {t('t_backgrounds')}
            </Button>
            {bgUrl && (
              <p className="truncate text-[11px] text-white/40" title={bgUrl}>
                {bgUrl}
              </p>
            )}
            <Field label={t('size')}>
              <Select value={s.width} onChange={(e) => set({ width: Number(e.target.value) })}>
                {SHOWCASE_SIZES.map((v) => (
                  <option key={v.value} value={v.value}>
                    {v.label}
                  </option>
                ))}
              </Select>
            </Field>
            <Range label={t('opacity')} value={s.bgDim} min={0} max={80} suffix="%" onChange={(v) => set({ bgDim: v })} />
            <Range label="Blur" value={s.bgBlur} min={0} max={20} suffix="px" onChange={(v) => set({ bgBlur: v })} />
          </div>
        )}

        {tab === 'char' && (
          <div className="grid gap-4">
            <Uploader
              title={t('layer_char')}
              hint="PNG, GIF, MP4, WebM"
              accept="image/*,video/*,.gif"
              file={char}
              onFile={setChar}
            />
            <Field label={t('chroma')}>
              <Select value={s.chromaKey} onChange={(e) => set({ chromaKey: e.target.value })}>
                <option value="auto">{t('chroma_auto')}</option>
                <option value="green">{t('chroma_green')}</option>
                <option value="blue">{t('chroma_blue')}</option>
                <option value="none">{t('chroma_off')}</option>
              </Select>
            </Field>
            {s.chromaKey !== 'none' && (
              <>
                <Range
                  label={t('chroma_tol')}
                  value={s.chromaTol}
                  min={5}
                  max={140}
                  onChange={(v) => set({ chromaTol: v })}
                />
                <Range
                  label={t('feather')}
                  value={s.feather}
                  min={0}
                  max={4}
                  step={0.1}
                  suffix="px"
                  onChange={(v) => set({ feather: v })}
                />
              </>
            )}
            <Range label={t('scale')} value={s.charScale} min={0.1} max={3} step={0.02} suffix="×" onChange={(v) => set({ charScale: v })} />
            <Range label={t('pos_x')} value={s.charX} min={0} max={1} step={0.01} onChange={(v) => set({ charX: v })} />
            <Range label={t('pos_y')} value={s.charY} min={0} max={1} step={0.01} onChange={(v) => set({ charY: v })} />
            <Range label={t('rotate')} value={s.charRotate} min={-180} max={180} suffix="°" onChange={(v) => set({ charRotate: v })} />
            <Range label={t('opacity')} value={s.charOpacity} min={0} max={100} suffix="%" onChange={(v) => set({ charOpacity: v })} />
          </div>
        )}

        {tab === 'text' && (
          <div className="grid gap-4">
            <Field label={t('layer_text')}>
              <Input value={s.text} onChange={(e) => set({ text: e.target.value })} placeholder="…" />
            </Field>
            <Field label={t('wm_font')}>
              <Select value={s.textFont} onChange={(e) => set({ textFont: e.target.value })}>
                <option value="mont">Montserrat</option>
                <option value="lap">Lapsus</option>
                <option value="mulish">Mulish</option>
              </Select>
            </Field>
            <Range label={t('font_size')} value={s.textSize} min={10} max={200} suffix="px" onChange={(v) => set({ textSize: v })} />
            <Field label={t('wm_color')}>
              <input
                type="color"
                value={s.textColor}
                onChange={(e) => set({ textColor: e.target.value })}
                className="h-11 w-full cursor-pointer rounded-xl border border-white/12 bg-black/35 p-1"
              />
            </Field>
            <Range label={t('pos_x')} value={s.textX} min={0} max={1} step={0.01} onChange={(v) => set({ textX: v })} />
            <Range label={t('pos_y')} value={s.textY} min={0} max={1} step={0.01} onChange={(v) => set({ textY: v })} />
            <Toggle label="Тень" checked={s.textShadow} onChange={(v) => set({ textShadow: v })} />
          </div>
        )}

        {tab === 'frame' && (
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-2">
              {FRAME_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => set({ frameStyle: preset.style, frameWidth: preset.width || 1, frameColor: preset.color })}
                  className={`rounded-xl border p-3 text-left text-[11px] transition ${s.frameStyle === preset.style && s.frameColor === preset.color ? 'border-cyan/60 bg-cyan/10' : 'border-white/10 bg-black/20 hover:border-white/25'}`}
                >
                  <span className="mb-2 block h-8 rounded-md bg-black/50" style={{ border: `${Math.max(1, Math.min(preset.width, 4))}px solid ${preset.color}`, boxShadow: preset.style === 'glow' ? `0 0 10px ${preset.color}` : undefined }} />
                  {preset.name}
                </button>
              ))}
            </div>
            <Field label={t('layer_frame')}>
              <Select value={s.frameStyle} onChange={(e) => set({ frameStyle: e.target.value })}>
                <option value="none">—</option>
                <option value="solid">Solid</option>
                <option value="glow">Glow</option>
                <option value="inset">Inset</option>
              </Select>
            </Field>
            {s.frameStyle !== 'none' && (
              <>
                <Range label={t('size')} value={s.frameWidth} min={1} max={40} suffix="px" onChange={(v) => set({ frameWidth: v })} />
                <Field label={t('wm_color')}>
                  <input
                    type="color"
                    value={s.frameColor}
                    onChange={(e) => set({ frameColor: e.target.value })}
                    className="h-11 w-full cursor-pointer rounded-xl border border-white/12 bg-black/35 p-1"
                  />
                </Field>
              </>
            )}
          </div>
        )}

        {tab === 'fx' && (
          <div className="grid gap-4">
            <Range label="Vignette" value={s.vignette} min={0} max={100} suffix="%" onChange={(v) => set({ vignette: v })} />
            <Field label={t('fps')}>
              <Select value={s.fps} onChange={(e) => set({ fps: Number(e.target.value) })}>
                {[8, 10, 12, 15, 20, 24, 30].map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="my-1 h-px bg-white/10" />
            <SectionTitle>{t('wm')}</SectionTitle>
            <WatermarkPanel wm={wm} setWm={setWm} file={bg} isPro={isPro} t={t} />
          </div>
        )}
      </Panel>

      {/* ----------------------- live preview ----------------------- */}
      <Panel className="grid place-items-center overflow-hidden">
        <div
          className="checker relative overflow-hidden rounded-xl bg-black shadow-2xl"
          style={{ width: '100%', maxWidth: 620, aspectRatio: '750 / 500', ...frameCss }}
        >
          {bgSrc ? (
            /\.(mp4|webm)(\?|$)/i.test(bgSrc) || bg?.type.startsWith('video') ? (
              <video
                src={bgSrc}
                autoPlay
                muted
                loop
                playsInline
                className="absolute inset-0 h-full w-full object-cover"
                style={{ filter: `blur(${s.bgBlur}px)` }}
              />
            ) : (
              <img
                src={bgSrc}
                alt=""
                className="absolute inset-0 h-full w-full object-cover"
                style={{ filter: `blur(${s.bgBlur}px)` }}
              />
            )
          ) : (
            <div className="absolute inset-0 grid place-items-center text-center text-white/25">
              <div>
                <Sparkles className="mx-auto mb-3" />
                <p className="text-xs">{t('d_builder')}</p>
              </div>
            </div>
          )}

          {s.bgDim > 0 && (
            <div className="absolute inset-0 bg-black" style={{ opacity: s.bgDim / 100 }} />
          )}

          {charObj && (char?.type.startsWith('video') ? (
            <video src={charObj} autoPlay muted loop playsInline className="absolute origin-bottom" style={{ left: `${s.charX * 100}%`, top: `${s.charY * 100}%`, transform: `translate(-50%,-100%) scale(${s.charScale}) rotate(${s.charRotate}deg)`, maxHeight: '100%', maxWidth: '100%', opacity: s.charOpacity / 100 }} />
          ) : (
            <img src={charObj} alt="" className="absolute origin-bottom" style={{ left: `${s.charX * 100}%`, top: `${s.charY * 100}%`, transform: `translate(-50%,-100%) scale(${s.charScale}) rotate(${s.charRotate}deg)`, maxHeight: '100%', opacity: s.charOpacity / 100 }} />
          ))}

          {s.text && (
            <div
              className="absolute whitespace-pre-wrap text-center leading-tight"
              style={{
                left: `${s.textX * 100}%`,
                top: `${s.textY * 100}%`,
                transform: 'translate(-50%,-50%)',
                color: s.textColor,
                fontSize: `${s.textSize / 3}px`,
                fontWeight: 700,
                textShadow: s.textShadow ? '0 2px 12px rgba(0,0,0,.8)' : 'none',
              }}
            >
              {s.text}
            </div>
          )}

          {s.vignette > 0 && (
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                background: `radial-gradient(ellipse at center, transparent 45%, rgba(0,0,0,${s.vignette / 100}) 100%)`,
              }}
            />
          )}
        </div>

        <p className="mt-3 flex items-center gap-1.5 text-[11px] text-white/35">
          <Eye size={12} /> {t('preview')} — {t('render')} → {t('result')}
        </p>
      </Panel>

      {/* ----------------------- layers + actions ----------------------- */}
      <Panel>
        <SectionTitle>{t('layers')}</SectionTitle>
        {[
          [t('layer_fx'), 'fx', s.vignette > 0],
          [t('layer_frame'), 'frame', s.frameStyle !== 'none'],
          [t('layer_text'), 'text', !!s.text],
          [t('layer_char'), 'char', !!char],
          [t('layer_bg'), 'bg', !!bgSrc],
        ].map(([label, id, on]) => (
          <button
            key={String(id)}
            onClick={() => setTab(id as Tab)}
            className={`mb-2 flex w-full items-center gap-2 rounded-xl border p-3 text-left text-xs transition ${
              on ? 'border-cyan/30 bg-cyan/10 text-white' : 'border-white/10 bg-black/20 text-white/40'
            }`}
          >
            <Layers size={13} />
            <span className="flex-1">{label}</span>
            <span className={on ? 'text-cyan' : 'text-white/20'}>●</span>
          </button>
        ))}

        <Button className="mt-5 w-full" onClick={() => render(true)} busy={busy}>
          <Download size={14} />
          {t('render')}
        </Button>
        <Button variant="outline" className="mt-2 w-full" onClick={() => go('/process')}>
          {t('send_to_process')}
        </Button>
        <Status text={msg} kind={kind} />

        {!isPro && (
          <p className="mt-4 text-[11px] leading-snug text-white/35">
            <Save size={11} className="mr-1 inline" />
            {t('pro_only')}: {t('projects').toLowerCase()}
          </p>
        )}
      </Panel>
    </div>
  );
}
