/** Community gallery — approved feed, likes, comments, publishing and moderation. */
import React, { useCallback, useEffect, useState } from 'react';
import { Heart, MessageCircle, Shield, Trash2, Upload } from 'lucide-react';
import { api } from '../api';
import {
  Button,
  Empty,
  Field,
  Input,
  Modal,
  Panel,
  Select,
  Spinner,
  Status,
  Textarea,
  Uploader,
} from '../ui';
import type { Me } from '../api';
import type { T } from '../i18n';

type Item = {
  id: number;
  title?: string;
  url?: string;
  image_url?: string;
  likes?: number;
  like_count?: number;
  liked?: boolean;
  comments?: number;
  comment_count?: number;
  author?: string;
  author_name?: string;
  status?: string;
};

export function Gallery({ t, me }: { t: T; me: Me | null }) {
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(true);
  const [status, setStatus] = useState('approved');
  const [isMod, setIsMod] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState<Item | null>(null);
  const [err, setErr] = useState('');

  const load = useCallback(
    async (st = status) => {
      setBusy(true);
      setErr('');
      try {
        const r = await api.galleryList(st, 60, 0);
        setItems(r.items || []);
      } catch (e: any) {
        setErr(e.message || t('error'));
        setItems([]);
      } finally {
        setBusy(false);
      }
    },
    [status, t],
  );

  useEffect(() => {
    load(status);
  }, [status, load]);

  useEffect(() => {
    api
      .galleryAmAdmin()
      .then((r) => setIsMod(!!(r.ok ?? r.admin ?? r.is_admin)))
      .catch(() => setIsMod(false));
  }, []);

  async function like(it: Item) {
    try {
      const r = await api.galleryLike(it.id);
      setItems((list) =>
        list.map((x) =>
          x.id === it.id
            ? { ...x, liked: r.liked ?? !x.liked, likes: r.likes ?? (x.likes || 0) + (x.liked ? -1 : 1) }
            : x,
        ),
      );
    } catch (e: any) {
      setErr(e.message || t('login_required'));
    }
  }

  async function moderate(it: Item, action: string) {
    try {
      await api.galleryMod(it.id, action);
      load(status);
    } catch (e: any) {
      setErr(e.message || t('error'));
    }
  }

  async function remove(it: Item) {
    try {
      await api.galleryDelete(it.id);
      setItems((l) => l.filter((x) => x.id !== it.id));
    } catch (e: any) {
      setErr(e.message || t('error'));
    }
  }

  return (
    <div>
      <Panel className="mb-5 flex flex-wrap items-center gap-3">
        {isMod && (
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-48">
            <option value="approved">approved</option>
            <option value="pending">pending</option>
          </Select>
        )}
        <div className="ml-auto">
          <Button onClick={() => (me?.logged_in ? setOpen(true) : (location.href = '/profile'))}>
            <Upload size={14} />
            {t('g_publish')}
          </Button>
        </div>
      </Panel>
      <Status text={err} kind={err ? 'err' : undefined} />

      {busy ? (
        <Spinner text={t('loading')} />
      ) : !items.length ? (
        <Empty text={t('empty')} />
      ) : (
        <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4">
          {items.map((it) => (
            <article key={it.id} className="glass mb-4 break-inside-avoid overflow-hidden rounded-2xl">
              <button onClick={() => setActive(it)} className="block w-full">
                <img
                  src={it.url || it.image_url || api.galleryImageUrl(it.id)}
                  alt={it.title || ''}
                  loading="lazy"
                  className="w-full object-cover"
                />
              </button>
              <div className="p-4">
                <h3 className="truncate text-sm font-semibold">{it.title || 'Showcase'}</h3>
                {(it.author || it.author_name) && (
                  <p className="mt-0.5 truncate text-[11px] text-white/35">
                    {it.author || it.author_name}
                  </p>
                )}
                <div className="mt-3 flex items-center gap-4 text-xs text-white/40">
                  <button
                    onClick={() => like(it)}
                    className={`flex items-center gap-1.5 transition hover:text-white ${it.liked ? 'text-red-400' : ''}`}
                  >
                    <Heart size={13} fill={it.liked ? 'currentColor' : 'none'} />
                    {it.likes ?? it.like_count ?? 0}
                  </button>
                  <button
                    onClick={() => setActive(it)}
                    className="flex items-center gap-1.5 transition hover:text-white"
                  >
                    <MessageCircle size={13} />
                    {it.comments ?? it.comment_count ?? 0}
                  </button>
                  {isMod && status === 'pending' && (
                    <span className="ml-auto flex gap-2">
                      <button onClick={() => moderate(it, 'approve')} className="text-cyan hover:underline">
                        {t('g_approve')}
                      </button>
                      <button onClick={() => moderate(it, 'reject')} className="text-red-300 hover:underline">
                        {t('g_reject')}
                      </button>
                    </span>
                  )}
                  {isMod && status === 'approved' && (
                    <button onClick={() => remove(it)} className="ml-auto text-white/30 hover:text-red-300">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <PublishModal open={open} onClose={() => setOpen(false)} onDone={() => load(status)} t={t} />
      <DetailModal item={active} onClose={() => setActive(null)} me={me} t={t} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
function PublishModal({
  open,
  onClose,
  onDone,
  t,
}: {
  open: boolean;
  onClose: () => void;
  onDone: () => void;
  t: T;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState('workshop');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  async function send() {
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
      fd.append('title', title);
      fd.append('mode', mode);
      await api.galleryPublish(fd);
      setMsg(t('g_pending'));
      setKind('ok');
      onDone();
      setTimeout(onClose, 1400);
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t('g_publish')}>
      <div className="grid gap-4">
        <Uploader title={t('upload')} accept="image/*" file={file} onFile={setFile} />
        <Field label={t('g_title')}>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label={t('mode')}>
          <Select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="workshop">{t('mode_workshop')}</option>
            <option value="featured">{t('mode_featured')}</option>
            <option value="split">{t('mode_split')}</option>
          </Select>
        </Field>
        <Button onClick={send} busy={busy}>
          {t('g_publish')}
        </Button>
        <Status text={msg} kind={kind} />
        <p className="text-[11px] leading-snug text-white/35">
          <Shield size={11} className="mr-1 inline" />
          {t('g_pending')}
        </p>
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------ */
function DetailModal({
  item,
  onClose,
  me,
  t,
}: {
  item: Item | null;
  onClose: () => void;
  me: Me | null;
  t: T;
}) {
  const [comments, setComments] = useState<any[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!item) return;
    api
      .galleryComments(item.id)
      .then((r) => setComments(r.items || r.comments || []))
      .catch(() => setComments([]));
  }, [item]);

  async function send() {
    if (!item || !text.trim()) return;
    setBusy(true);
    try {
      await api.galleryComment(item.id, text.trim());
      setText('');
      const r = await api.galleryComments(item.id);
      setComments(r.items || r.comments || []);
    } catch {
      /* surfaced by the disabled state */
    } finally {
      setBusy(false);
    }
  }

  if (!item) return null;

  return (
    <Modal open={!!item} onClose={onClose} title={item.title || 'Showcase'}>
      <img
        src={item.url || item.image_url || api.galleryImageUrl(item.id)}
        alt=""
        className="mb-5 w-full rounded-2xl"
      />
      <div className="grid gap-3">
        <div className="text-[10px] uppercase tracking-[0.18em] text-white/45">
          {t('g_comments')} · {comments.length}
        </div>
        <div className="thin-scroll grid max-h-52 gap-3 overflow-auto">
          {comments.length ? (
            comments.map((c, i) => (
              <div key={c.id || i} className="rounded-xl border border-white/10 bg-black/25 p-3">
                <div className="text-[11px] text-cyan/80">{c.author || c.author_name || 'user'}</div>
                <div className="mt-1 text-sm leading-snug text-white/75">{c.text || c.body}</div>
              </div>
            ))
          ) : (
            <p className="text-xs text-white/30">{t('empty')}</p>
          )}
        </div>
        {me?.logged_in ? (
          <div className="grid gap-2">
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={t('g_comment_ph')}
            />
            <Button onClick={send} busy={busy} disabled={!text.trim()}>
              {t('g_send')}
            </Button>
          </div>
        ) : (
          <p className="text-xs text-white/35">{t('login_required')}</p>
        )}
      </div>
    </Modal>
  );
}
