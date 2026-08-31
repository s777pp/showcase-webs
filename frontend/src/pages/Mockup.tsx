/**
 * Steam profile mockup — fills the slots of the profile template and opens the
 * generated overlay page. Backed by /api/preview-slots and /api/preview-build,
 * so GIFs stay animated and MP4 slots render as <video>.
 */
import React, { useEffect, useState } from 'react';
import { ExternalLink, LayoutTemplate, User } from 'lucide-react';
import { api } from '../api';
import { Button, Field, Panel, SectionTitle, Select, Status, Uploader } from '../ui';
import type { T } from '../i18n';

type Slot = { id: string; label: string; type: string };

export function Mockup({ t }: { t: T }) {
  const [mode, setMode] = useState('workshop');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [picked, setPicked] = useState<Record<string, File>>({});
  const [avatar, setAvatar] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [built, setBuilt] = useState('');

  useEffect(() => {
    let dead = false;
    api
      .previewSlots(mode)
      .then((r) => {
        if (!dead) setSlots(r.slots || []);
      })
      .catch(() => {
        if (!dead) setSlots([]);
      });
    setPicked({});
    setBuilt('');
    return () => {
      dead = true;
    };
  }, [mode]);

  async function build() {
    if (!Object.keys(picked).length) {
      setMsg(t('choose_file'));
      setKind('err');
      return;
    }
    setBusy(true);
    setMsg(t('processing'));
    setKind('busy');
    try {
      const fd = new FormData();
      fd.append('mode', mode);
      if (avatar) fd.append('avatar', avatar);
      Object.entries(picked).forEach(([id, f]) => fd.append(`slot_${id}`, f));
      const r = await api.previewBuild(fd);
      const url = r.url || (r.job_id ? `/preview/${r.job_id}` : '');
      if (!url) throw new Error(r.msg || t('error'));
      setBuilt(url);
      setMsg(t('done'));
      setKind('ok');
      window.open(url, '_blank', 'noopener');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[400px_1fr]">
      <Panel className="thin-scroll max-h-[calc(100vh-190px)] overflow-auto">
        <LayoutTemplate className="mb-5 text-cyan" size={28} />
        <SectionTitle>{t('t_mockup')}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{t('d_mockup')}</p>

        <Field label={t('mode')}>
          <Select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="workshop">{t('mode_workshop')}</option>
            <option value="featured">{t('mode_featured')}</option>
            <option value="split">{t('mode_split')}</option>
          </Select>
        </Field>

        <div className="mt-5 grid gap-4">
          <div>
            <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-white/45">
              {t('avatar')}
            </div>
            <Uploader
              title={t('avatar')}
              accept="image/*"
              file={avatar}
              onFile={setAvatar}
            />
          </div>

          {slots.map((s) => (
            <div key={s.id}>
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-white/45">
                <span>{s.label}</span>
                <span className="text-white/25">{s.type}</span>
              </div>
              <Uploader
                title={t('upload')}
                accept="image/*,video/*,.gif"
                file={picked[s.id] || null}
                onFile={(f) =>
                  setPicked((p) => {
                    const n = { ...p };
                    if (f) n[s.id] = f;
                    else delete n[s.id];
                    return n;
                  })
                }
              />
            </div>
          ))}
        </div>

        <Button className="mt-6 w-full" onClick={build} busy={busy}>
          {t('preview')}
        </Button>
        <Status text={msg} kind={kind} />
      </Panel>

      <Panel className="grid min-h-[520px] place-items-center overflow-hidden">
        {built ? (
          <div className="w-full text-center">
            <a href={built} target="_blank" rel="noreferrer noopener">
              <Button variant="outline">
                <ExternalLink size={14} />
                {t('preview')}
              </Button>
            </a>
            <iframe
              title="mockup"
              src={built}
              className="mt-4 h-[64vh] w-full rounded-2xl border border-white/10 bg-black"
            />
          </div>
        ) : (
          <div className="max-w-sm p-6 text-center text-white/35">
            <img
              src={api.previewTemplateUrl(mode)}
              alt=""
              className="mx-auto mb-5 max-h-[42vh] rounded-xl opacity-40"
              onError={(e) => ((e.target as HTMLImageElement).style.display = 'none')}
            />
            <User className="mx-auto mb-3" size={32} />
            <p className="text-sm leading-relaxed">{t('d_mockup')}</p>
          </div>
        )}
      </Panel>
    </div>
  );
}
