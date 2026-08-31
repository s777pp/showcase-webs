/**
 * Steam profile mockup — fills the slots of the profile template and opens the
 * generated overlay page. Backed by /api/preview-slots and /api/preview-build,
 * so GIFs stay animated and MP4 slots render as <video>.
 */
import React, { useEffect, useState } from 'react';
import { ArrowDown, ArrowUp, ExternalLink, LayoutTemplate, Search, User } from 'lucide-react';
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
  const [profileUrl, setProfileUrl] = useState('');
  const [profile, setProfile] = useState<any>(null);
  const [profileBusy, setProfileBusy] = useState(false);

  async function importProfile() {
    if (!profileUrl.trim()) return;
    setProfileBusy(true);
    setMsg('');
    try {
      const r = await api.steamProfile(profileUrl.trim());
      setProfile(r.profile);
      setMsg(t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setProfileBusy(false);
    }
  }

  function moveSlot(index: number, delta: number) {
    setSlots((current) => {
      const next = [...current];
      const to = index + delta;
      if (to < 0 || to >= next.length) return current;
      [next[index], next[to]] = [next[to], next[index]];
      return next;
    });
  }

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
      const url = r.url || r.open || (r.job_id ? `/preview/${r.job_id}` : '');
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

        <div className="mb-5 rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="mb-2 text-[10px] uppercase tracking-[0.18em] text-white/45">
            Steam profile URL
          </div>
          <div className="flex gap-2">
            <input
              value={profileUrl}
              onChange={(e) => setProfileUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && importProfile()}
              placeholder="https://steamcommunity.com/id/..."
              className="min-w-0 flex-1 rounded-xl border border-white/12 bg-black/35 px-3 py-2.5 text-sm outline-none focus:border-cyan/60"
            />
            <Button onClick={importProfile} busy={profileBusy}><Search size={14} /></Button>
          </div>
          <p className="mt-2 text-[11px] text-white/35">Импортирует открытые данные профиля. Ничего в Steam не изменяет.</p>
        </div>

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

          {slots.map((s, index) => (
            <div key={s.id}>
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-[0.18em] text-white/45">
                <span>{s.label}</span>
                <span className="flex items-center gap-1 text-white/25">
                  {s.type}
                  <button onClick={() => moveSlot(index, -1)} disabled={index === 0} className="p-1 disabled:opacity-20"><ArrowUp size={12} /></button>
                  <button onClick={() => moveSlot(index, 1)} disabled={index === slots.length - 1} className="p-1 disabled:opacity-20"><ArrowDown size={12} /></button>
                </span>
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
        ) : profile ? (
          <div className="relative w-full max-w-4xl overflow-hidden rounded-2xl border border-white/12 bg-[#171a21] shadow-2xl">
            <div className="h-40 bg-[radial-gradient(circle_at_25%_10%,rgba(0,210,255,.25),transparent_38%),linear-gradient(120deg,#142a3a,#101318_60%)]" />
            <div className="relative -mt-16 flex flex-col gap-5 p-6 sm:flex-row">
              <img src={profile.avatar} alt="" className="h-32 w-32 rounded-lg border-4 border-[#171a21] object-cover" />
              <div className="min-w-0 flex-1 pt-12 sm:pt-8">
                <input value={profile.name || ''} onChange={(e) => setProfile({...profile,name:e.target.value})} className="w-full bg-transparent text-2xl font-semibold outline-none" />
                <input value={profile.location || ''} onChange={(e) => setProfile({...profile,location:e.target.value})} className="mt-1 w-full bg-transparent text-sm text-white/45 outline-none" />
                <textarea value={profile.summary || ''} onChange={(e) => setProfile({...profile,summary:e.target.value})} className="mt-5 min-h-28 w-full resize-none rounded-xl border border-white/10 bg-black/20 p-3 text-sm leading-relaxed text-white/65 outline-none" />
              </div>
              <div className="pt-9 text-right">
                <span className="inline-flex h-16 w-16 items-center justify-center rounded-full border-2 border-cyan text-xl font-semibold">{profile.level || '—'}</span>
                <div className="mt-2 text-[10px] uppercase tracking-wider text-white/35">Steam level</div>
              </div>
            </div>
            <div className="grid gap-3 border-t border-white/10 p-5 sm:grid-cols-2">
              {slots.map((slot) => <div key={slot.id} className="checker grid min-h-28 place-items-center rounded-xl border border-white/10 text-xs text-white/35">{picked[slot.id]?.name || slot.label}</div>)}
            </div>
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
