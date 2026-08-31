/** Account page: sign in / sign up, profile editing, library, saved projects. */
import React, { useEffect, useState } from 'react';
import { Crown, KeyRound, LogOut, User as UserIcon } from 'lucide-react';
import { api, type Me, type Quota } from '../api';
import {
  Button,
  Empty,
  Field,
  Input,
  Panel,
  SectionTitle,
  Spinner,
  Status,
  Textarea,
  Uploader,
} from '../ui';
import { go } from '../routes';
import type { T } from '../i18n';

export function Profile({
  t,
  me,
  quota,
  reload,
}: {
  t: T;
  me: Me | null;
  quota: Quota | null;
  reload: () => void;
}) {
  if (me === null) return <Spinner text={t('loading')} />;
  if (!me.logged_in) return <AuthCard t={t} onDone={reload} />;
  return <Account t={t} me={me} quota={quota} reload={reload} />;
}

/* ------------------------------------------------------------------ */
function AuthCard({ t, onDone }: { t: T; onDone: () => void }) {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  async function submit() {
    setBusy(true);
    setMsg('');
    setKind('busy');
    try {
      if (tab === 'login') await api.login(email, password);
      else await api.register(email, password);
      setMsg(t('done'));
      setKind('ok');
      onDone();
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <Panel>
        <UserIcon className="mx-auto mb-5 text-cyan" size={34} />
        <div className="mb-6 flex gap-2">
          {(['login', 'register'] as const).map((x) => (
            <button
              key={x}
              onClick={() => setTab(x)}
              className={`flex-1 rounded-full px-4 py-2.5 text-xs uppercase tracking-widest transition ${
                tab === x ? 'bg-white text-black' : 'bg-white/5 text-white/50 hover:text-white'
              }`}
            >
              {x === 'login' ? t('login') : t('register')}
            </button>
          ))}
        </div>

        <div className="grid gap-4">
          <Field label={t('email')}>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </Field>
          <Field label={t('password')}>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
            />
          </Field>
          <Button onClick={submit} busy={busy}>
            {tab === 'login' ? t('login') : t('register')}
          </Button>
          <Status text={msg} kind={kind} />
        </div>

        <div className="my-6 flex items-center gap-3 text-[10px] uppercase tracking-widest text-white/25">
          <span className="h-px flex-1 bg-white/10" />
          or
          <span className="h-px flex-1 bg-white/10" />
        </div>

        <div className="grid gap-2">
          <a href="/api/auth/steam/login">
            <Button variant="outline" className="w-full">
              Steam
            </Button>
          </a>
          <a href="/api/auth/discord/login">
            <Button variant="outline" className="w-full">
              Discord
            </Button>
          </a>
          <a href="/api/auth/google/login">
            <Button variant="outline" className="w-full">
              Google
            </Button>
          </a>
        </div>
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
function Account({
  t,
  me,
  quota,
  reload,
}: {
  t: T;
  me: Me;
  quota: Quota | null;
  reload: () => void;
}) {
  const [library, setLibrary] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [display, setDisplay] = useState(me.display_name || '');
  const [username, setUsername] = useState(me.username || '');
  const [bio, setBio] = useState(me.bio || '');
  const [avatar, setAvatar] = useState<File | null>(null);
  const [code, setCode] = useState('');
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.profileLibrary().then((r) => setLibrary(r.items || [])).catch(() => setLibrary([]));
    if (me.is_pro) api.projects().then((r) => setProjects(r.items || [])).catch(() => setProjects([]));
  }, [me.is_pro]);

  async function save() {
    setBusy(true);
    setMsg('');
    setKind('busy');
    try {
      const fd = new FormData();
      fd.append('display_name', display);
      fd.append('username', username);
      fd.append('bio', bio);
      if (avatar) fd.append('avatar', avatar);
      await api.saveProfile(fd);
      setMsg(t('done'));
      setKind('ok');
      reload();
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  async function unlock() {
    if (!code.trim()) return;
    setBusy(true);
    try {
      await api.unlock(code.trim());
      setMsg(t('done'));
      setKind('ok');
      setCode('');
      reload();
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await api.logout().catch(() => undefined);
    reload();
    go('/');
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <Panel className="h-fit">
        <div className="grid h-20 w-20 place-items-center overflow-hidden rounded-2xl bg-white/10">
          {me.avatar_url ? (
            <img src={me.avatar_url} alt="" className="h-full w-full object-cover" />
          ) : (
            <UserIcon />
          )}
        </div>
        <h2 className="mt-5 font-podium text-xl uppercase tracking-wide">
          {me.display_name || me.username || me.email}
        </h2>
        <p className="mt-1 truncate text-sm text-white/40">{me.email}</p>

        <span
          className={`mt-5 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs ${
            quota?.pro ? 'bg-cyan/15 text-cyan' : 'bg-white/10 text-white/50'
          }`}
        >
          {quota?.pro && <Crown size={12} />}
          {quota?.pro ? quota.label || t('pro') : t('free')}
        </span>
        {quota && !quota.pro && (
          <p className="mt-3 text-xs text-white/40">
            {t('quota_left')}: {quota.left}/{quota.limit}
          </p>
        )}

        <div className="mt-6 grid gap-2">
          <Field label={t('access_code')}>
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="XXXX-XXXX" />
          </Field>
          <Button variant="outline" onClick={unlock} busy={busy} disabled={!code.trim()}>
            <KeyRound size={14} />
            {t('unlock')}
          </Button>
          {!quota?.pro && <Button onClick={() => go('/billing')}>{t('buy_pro')}</Button>}
          <Button variant="ghost" onClick={logout}>
            <LogOut size={14} />
            {t('sign_out')}
          </Button>
        </div>
      </Panel>

      <div className="grid gap-4">
        <Panel>
          <SectionTitle>{t('settings')}</SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t('display_name')}>
              <Input value={display} onChange={(e) => setDisplay(e.target.value)} />
            </Field>
            <Field label={t('username')}>
              <Input value={username} onChange={(e) => setUsername(e.target.value)} />
            </Field>
          </div>
          <div className="mt-4 grid gap-4">
            <Field label={t('bio')}>
              <Textarea value={bio} onChange={(e) => setBio(e.target.value)} />
            </Field>
            <Uploader title={t('avatar')} accept="image/*" file={avatar} onFile={setAvatar} />
          </div>
          <Button className="mt-5" onClick={save} busy={busy}>
            {t('save')}
          </Button>
          <Status text={msg} kind={kind} />
        </Panel>

        <Panel>
          <SectionTitle>{t('my_library')}</SectionTitle>
          {library.length ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {library.map((x, i) => (
                <img
                  key={x.id || i}
                  src={x.url || x.image_url}
                  alt=""
                  loading="lazy"
                  className="aspect-square w-full rounded-xl object-cover"
                />
              ))}
            </div>
          ) : (
            <Empty text={t('empty')} />
          )}
        </Panel>

        <Panel>
          <SectionTitle>{t('projects')}</SectionTitle>
          {!me.is_pro ? (
            <p className="text-sm text-white/45">
              {t('pro_only')} — {t('no_projects')}
            </p>
          ) : projects.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {projects.map((p) => (
                <div key={p.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <b className="text-sm">{p.name}</b>
                  <p className="mt-1 text-[11px] text-white/40">{p.project_type || 'builder'}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-white/45">{t('no_projects')}</p>
          )}
        </Panel>
      </div>
    </div>
  );
}
