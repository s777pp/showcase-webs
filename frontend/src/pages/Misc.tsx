/** Billing, FAQ, legal pages, Steam lookup and the DeviantArt publisher. */
import React, { useEffect, useState } from 'react';
import { Check, Crown, ExternalLink, HelpCircle, Search, Upload } from 'lucide-react';
import { api } from '../api';
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
import type { T } from '../i18n';

/* ------------------------------------------------------------------ */
/* Pricing                                                             */
/* ------------------------------------------------------------------ */
export function Billing({ t, isPro }: { t: T; isPro: boolean }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  async function buy() {
    setBusy(true);
    try {
      const r = await api.checkout();
      if (r.url) location.href = r.url;
      else setMsg(r.msg || t('error'));
    } catch (e: any) {
      setMsg(e.message || t('error'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2">
      <Panel className="p-8">
        <span className="text-xs uppercase tracking-[0.25em] text-white/40">{t('price_free_t')}</span>
        <h2 className="mt-4 font-inter text-4xl font-bold">0 €</h2>
        <ul className="mt-8 grid gap-3 text-sm text-white/55">
          {[t('f_free_1'), t('f_free_2'), t('f_free_3')].map((x) => (
            <li key={x} className="flex gap-2">
              <Check size={15} className="mt-0.5 shrink-0 text-white/30" />
              {x}
            </li>
          ))}
        </ul>
      </Panel>

      <div className="rounded-3xl border border-cyan/35 bg-gradient-to-br from-cyan/15 to-deep/20 p-8 shadow-2xl">
        <span className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-cyan">
          <Crown size={14} />
          {t('price_pro_t')}
        </span>
        <h2 className="mt-4 font-inter text-4xl font-bold">Unlimited</h2>
        <ul className="mt-8 grid gap-3 text-sm text-white/75">
          {[t('f_pro_1'), t('f_pro_2'), t('f_pro_3'), t('f_pro_4')].map((x) => (
            <li key={x} className="flex gap-2">
              <Check size={15} className="mt-0.5 shrink-0 text-cyan" />
              {x}
            </li>
          ))}
        </ul>
        <Button className="mt-8 w-full" onClick={buy} busy={busy} disabled={isPro}>
          {isPro ? t('pro') : t('buy_pro')}
        </Button>
        <Status text={msg} kind={msg ? 'err' : undefined} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* FAQ                                                                 */
/* ------------------------------------------------------------------ */
const FAQ_RU: [string, string][] = [
  [
    'Какие форматы витрин поддерживаются?',
    'Мастерская (5 частей), Featured (630 px) и Артворк-сплит (506 + 100). Каждый формат собирается из изображения, GIF или видео.',
  ],
  [
    'Как загрузить готовую витрину в Steam?',
    'Скачай ZIP и загрузи части как отдельные артворки в профиле Steam, соблюдая порядок из имён файлов.',
  ],
  [
    'Почему GIF не проходит в Steam?',
    'Steam ограничивает артворк примерно 5 МБ. Прогони файл через оптимизатор GIF — он подберёт палитру, FPS и разрешение под лимит.',
  ],
  [
    'Как работает хромакей для персонажа?',
    'Загрузи персонажа на однотонном фоне. Режим «Автоматически» определяет цвет по краям кадра, либо выбери зелёный или синий вручную и подстрой допуск и смягчение края.',
  ],
  [
    'Можно ли использовать анимированного персонажа?',
    'Да — GIF, MP4 и WebM. Анимация сохраняется при сборке, фон тоже может быть анимированным.',
  ],
  [
    'Зачем нужен HEX21?',
    'Приём с байтом 0x21 делает часть изображения прозрачной в интерфейсе Steam. Загрузи PNG или GIF, получишь обработанный файл в архиве.',
  ],
  [
    'Что даёт Pro?',
    'Снимается водяной знак сервиса, пропадает дневной лимит, открывается сохранение проектов билдера и максимальное качество экспорта.',
  ],
  [
    'Почему на моих работах водяной знак?',
    'На бесплатном тарифе водяной знак сервиса накладывается на все выходные файлы. Pro его убирает, а свой собственный знак можно ставить на любом тарифе.',
  ],
];

const FAQ_EN: [string, string][] = [
  [
    'Which showcase formats are supported?',
    'Workshop (5 parts), Featured (630 px) and Artwork split (506 + 100). Each is built from an image, GIF or video.',
  ],
  [
    'How do I upload a finished showcase to Steam?',
    'Download the ZIP and upload the parts as separate artworks in your Steam profile, keeping the order encoded in the file names.',
  ],
  [
    'Why does Steam reject my GIF?',
    'Steam caps artwork at roughly 5 MB. Run the file through the GIF optimizer — it tunes palette, FPS and resolution to fit.',
  ],
  [
    'How does character chroma key work?',
    'Upload a character on a flat background. "Automatic" samples the frame edges, or pick green or blue manually and tune tolerance and edge feather.',
  ],
  [
    'Can I use an animated character?',
    'Yes — GIF, MP4 and WebM. Animation survives the composite, and the background can be animated too.',
  ],
  [
    'What is HEX21 for?',
    'The 0x21 byte trick makes part of an image render transparent in the Steam interface. Upload a PNG or GIF and get the processed file back in an archive.',
  ],
  [
    'What does Pro give me?',
    'The service watermark is removed, the daily limit disappears, builder projects can be saved and exports run at maximum quality.',
  ],
  [
    'Why is there a watermark on my artwork?',
    'On the free plan the service watermark is applied to every export. Pro removes it; your own custom mark is available on any plan.',
  ],
];

export function Faq({ t, lang }: { t: T; lang: string }) {
  const rows = lang === 'ru' ? FAQ_RU : FAQ_EN;
  const [open, setOpen] = useState<number | null>(0);

  return (
    <div className="mx-auto max-w-3xl">
      <Panel>
        <HelpCircle className="mb-5 text-cyan" size={30} />
        <SectionTitle>{t('nav_faq')}</SectionTitle>
        <div className="mt-4 grid gap-2">
          {rows.map(([q, a], i) => (
            <div key={q} className="overflow-hidden rounded-2xl border border-white/10 bg-black/20">
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 p-4 text-left text-sm font-medium transition hover:bg-white/5"
              >
                {q}
                <span className={`shrink-0 text-cyan transition ${open === i ? 'rotate-45' : ''}`}>+</span>
              </button>
              {open === i && (
                <p className="border-t border-white/10 p-4 text-sm leading-relaxed text-white/55">{a}</p>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Legal                                                               */
/* ------------------------------------------------------------------ */
export function Legal({ kind, t }: { kind: string; t: T }) {
  const titles: Record<string, string> = {
    terms: 'Terms of Service',
    privacy: 'Privacy Policy',
    dmca: 'DMCA / Copyright',
  };
  const bodies: Record<string, string[]> = {
    terms: [
      'Сервис предоставляется «как есть». Мы не гарантируем непрерывную работу и не несём ответственности за материалы, которые загружают пользователи.',
      'Загружая файлы, ты подтверждаешь, что имеешь право их обрабатывать и публиковать. Материалы, нарушающие права третьих лиц, удаляются.',
      'Оплаченная подписка Pro привязана к аккаунту. Возврат средств рассматривается индивидуально по обращению.',
      'Сервис не связан с Valve Corporation. Steam — товарный знак Valve.',
    ],
    privacy: [
      'Мы храним почту, хешированный пароль, идентификаторы привязанных аккаунтов (Discord, Google, Telegram) и загруженные тобой файлы.',
      'Файлы обрабатываются на сервере и удаляются по истечении срока хранения задания. Галерея хранит только то, что ты опубликовал сам.',
      'Cookie сессии — HttpOnly, используется только для входа. Аналитику третьих сторон мы не подключаем.',
      'Запрос на удаление аккаунта и связанных данных обрабатывается по обращению через страницу помощи.',
    ],
    dmca: [
      'Если ты правообладатель и считаешь, что размещённый в галерее материал нарушает твои права, отправь обращение с описанием работы, ссылкой на неё и подтверждением прав.',
      'Мы снимаем спорный материал с публикации на время рассмотрения обращения.',
      'Повторные нарушения приводят к блокировке аккаунта загрузившего.',
    ],
  };
  const body = bodies[kind] || bodies.terms;

  return (
    <div className="mx-auto max-w-3xl">
      <Panel>
        <SectionTitle>{titles[kind] || 'Legal'}</SectionTitle>
        <div className="grid gap-4 text-sm leading-relaxed text-white/55">
          {body.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
      </Panel>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Steam lookup                                                        */
/* ------------------------------------------------------------------ */
export function Steam({ t }: { t: T }) {
  const [q, setQ] = useState('');
  const [items, setItems] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  async function search() {
    if (!q.trim()) return;
    setBusy(true);
    setMsg('');
    try {
      const r = await api.steamApps(q.trim());
      setItems(r.items || []);
      if (!r.items?.length) setMsg(t('empty'));
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setItems([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
      <Panel className="h-fit">
        <SectionTitle>{t('t_steam')}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{t('d_steam')}</p>
        <Field label={t('search')}>
          <div className="relative">
            <Search className="absolute left-3 top-3 text-white/30" size={16} />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              className="pl-9"
              placeholder="Counter-Strike…"
            />
          </div>
        </Field>
        <Button className="mt-4 w-full" onClick={search} busy={busy}>
          {t('search')}
        </Button>
        <Status text={msg} kind={msg ? 'err' : undefined} />
      </Panel>

      <div>
        {busy ? (
          <Spinner text={t('loading')} />
        ) : !items.length ? (
          <Empty text={t('empty')} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((a) => (
              <article key={a.appid} className="glass overflow-hidden rounded-2xl">
                {a.image && <img src={a.image} alt="" loading="lazy" className="aspect-[92/43] w-full object-cover" />}
                <div className="p-4">
                  <h3 className="truncate text-sm font-semibold">{a.name}</h3>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-white/40">
                    <span>AppID {a.appid}</span>
                    <a
                      href={`https://store.steampowered.com/app/${a.appid}`}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-cyan hover:underline"
                    >
                      <ExternalLink size={13} />
                    </a>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* DeviantArt publisher                                                */
/* ------------------------------------------------------------------ */
export function DeviantArt({ t }: { t: T }) {
  const [status, setStatus] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [desc, setDesc] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [kind, setKind] = useState<'ok' | 'err' | 'busy' | undefined>();

  const load = () => api.daStatus().then(setStatus).catch(() => setStatus({ connected: false }));
  useEffect(() => {
    load();
  }, []);

  async function upload() {
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
      fd.append('tags', tags);
      fd.append('description', desc);
      const r = await api.daUpload(fd);
      setMsg(r.url || t('done'));
      setKind('ok');
    } catch (e: any) {
      setMsg(e.message || t('error'));
      setKind('err');
    } finally {
      setBusy(false);
    }
  }

  const connected = !!(status?.connected ?? status?.ok ?? status?.logged_in);

  return (
    <div className="mx-auto grid max-w-3xl gap-4">
      <Panel>
        <SectionTitle>{t('t_da')}</SectionTitle>
        <p className="mb-5 -mt-2 text-sm leading-relaxed text-white/45">{t('d_da')}</p>

        {status === null ? (
          <Spinner text={t('loading')} />
        ) : connected ? (
          <>
            <div className="mb-5 flex items-center gap-2 rounded-2xl border border-cyan/25 bg-cyan/8 p-3.5 text-xs text-cyan">
              <Check size={14} />
              {status.username || 'connected'}
            </div>
            <div className="grid gap-4">
              <Uploader title={t('upload')} accept="image/*" file={file} onFile={setFile} />
              <Field label={t('g_title')}>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </Field>
              <Field label="Tags">
                <Input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="steam, showcase" />
              </Field>
              <Field label={t('bio')}>
                <Textarea value={desc} onChange={(e) => setDesc(e.target.value)} />
              </Field>
              <Button onClick={upload} busy={busy}>
                <Upload size={14} />
                {t('g_publish')}
              </Button>
              <Status text={msg} kind={kind} />
              <button
                onClick={() => api.daLogout().then(load)}
                className="justify-self-start text-[11px] text-white/40 underline hover:text-white/70"
              >
                {t('sign_out')}
              </button>
            </div>
          </>
        ) : (
          <div className="text-center">
            <p className="mb-5 text-sm text-white/45">{t('login_required')}</p>
            <a href="/api/da/login">
              <Button>
                <ExternalLink size={14} />
                DeviantArt
              </Button>
            </a>
          </div>
        )}
      </Panel>
    </div>
  );
}
