/** Router + global state (language, session, quota). */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api, type Me, type Quota } from './api';
import { makeT, readLang, writeLang, type Lang } from './i18n';
import { Shell } from './shell';
import { Home } from './pages/Home';
import { Process } from './pages/Process';
import { Builder } from './pages/Builder';
import { Mockup } from './pages/Mockup';
import { Optimizer } from './pages/Optimizer';
import { Backgrounds } from './pages/Backgrounds';
import { Achievements } from './pages/Achievements';
import { Gallery } from './pages/Gallery';
import { Profile } from './pages/Profile';
import { ToolsHub, Converter, Hex, Upscale, DownloadUrl } from './pages/Tools';
import { Billing, Faq, Legal, Steam, DeviantArt } from './pages/Misc';

export default function App() {
  const [path, setPath] = useState(location.pathname);
  const [lang, setLangState] = useState<Lang>(readLang);
  const [me, setMe] = useState<Me | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null);

  const t = useMemo(() => makeT(lang), [lang]);

  useEffect(() => {
    const onPop = () => setPath(location.pathname);
    addEventListener('popstate', onPop);
    return () => removeEventListener('popstate', onPop);
  }, []);

  const reload = useCallback(() => {
    api.me().then(setMe).catch(() => setMe({ logged_in: false }));
    api.quota().then(setQuota).catch(() => setQuota(null));
  }, []);

  useEffect(reload, [reload]);

  // Keep <html lang> in sync for screen readers and hyphenation.
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = (l: Lang) => {
    setLangState(l);
    writeLang(l);
  };

  const segments = path.replace(/^\//, '').split('/');
  const page = segments[0] || 'home';
  const isPro = !!(quota?.pro ?? me?.is_pro);

  if (page === 'home') return <Home lang={lang} setLang={setLang} t={t} />;

  let view: React.ReactNode;
  switch (page) {
    case 'app':
      view = <ToolsHub t={t} />;
      break;
    case 'process':
      view = <Process t={t} isPro={isPro} />;
      break;
    case 'builder':
      view = <Builder t={t} isPro={isPro} />;
      break;
    case 'mockup':
      view = <Mockup t={t} />;
      break;
    case 'optimizer':
      view = <Optimizer t={t} />;
      break;
    case 'backgrounds':
      view = <Backgrounds t={t} />;
      break;
    case 'achievements':
      view = <Achievements t={t} />;
      break;
    case 'converter':
      view = <Converter t={t} />;
      break;
    case 'upscale':
      view = <Upscale t={t} />;
      break;
    case 'hex':
      view = <Hex t={t} />;
      break;
    case 'download':
      view = <DownloadUrl t={t} />;
      break;
    case 'steam':
      view = <Steam t={t} />;
      break;
    case 'deviantart':
      view = <DeviantArt t={t} />;
      break;
    case 'gallery':
      view = <Gallery t={t} me={me} />;
      break;
    case 'profile':
      view = <Profile t={t} me={me} quota={quota} reload={reload} />;
      break;
    case 'billing':
      view = <Billing t={t} isPro={isPro} />;
      break;
    case 'faq':
      view = <Faq t={t} lang={lang} />;
      break;
    case 'legal':
      view = <Legal kind={segments[1] || 'terms'} t={t} />;
      break;
    default:
      view = <ToolsHub t={t} />;
  }

  return (
    <Shell page={page} lang={lang} setLang={setLang} t={t} me={me} quota={quota}>
      {view}
    </Shell>
  );
}
