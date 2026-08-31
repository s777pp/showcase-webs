/** App shell: sticky header, tool navigation, language toggle, account pill. */
import React, { useEffect, useState } from 'react';
import { Languages, Menu, User, X, Crown } from 'lucide-react';
import { GradientField } from './ui';
import type { Lang, T } from './i18n';
import type { Me, Quota } from './api';
import { go, TOOLS } from './routes';

export function Shell({
  page,
  lang,
  setLang,
  t,
  me,
  quota,
  children,
}: {
  page: string;
  lang: Lang;
  setLang: (l: Lang) => void;
  t: T;
  me: Me | null;
  quota: Quota | null;
  children: React.ReactNode;
}) {
  const [mobile, setMobile] = useState(false);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => setMobile(false), [page]);

  const active = TOOLS.find((x) => x.slug === page);

  return (
    <div className="relative min-h-screen bg-ink text-white">
      <div className="fixed inset-0 -z-10">
        <GradientField />
      </div>

      <header className="sticky top-0 z-40 border-b border-white/10 bg-black/70 backdrop-blur-2xl">
        <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-4 py-3.5 sm:px-6 lg:px-8">
          <button
            onClick={() => go('/')}
            className="shrink-0 font-podium text-lg uppercase tracking-wider sm:text-xl"
          >
            {t('brand')}
          </button>

          <nav className="thin-scroll hidden flex-1 items-center gap-1 overflow-x-auto lg:flex">
            {TOOLS.filter((x) => x.nav).map((x) => (
              <button
                key={x.slug}
                onClick={() => go('/' + x.slug)}
                className={`shrink-0 rounded-full px-3 py-2 text-xs transition ${
                  page === x.slug ? 'bg-white/12 text-white' : 'text-white/55 hover:text-white'
                }`}
              >
                {t(x.key)}
              </button>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {quota && !quota.pro && (
              <span className="hidden rounded-full border border-white/10 px-3 py-1.5 text-[11px] text-white/50 sm:inline">
                {t('quota_left')}: {quota.left < 0 ? '∞' : quota.left}
              </span>
            )}
            {quota?.pro && (
              <span className="hidden items-center gap-1 rounded-full border border-cyan/40 bg-cyan/10 px-3 py-1.5 text-[11px] font-semibold text-cyan sm:inline-flex">
                <Crown size={12} /> PRO
              </span>
            )}
            <button
              onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}
              className="rounded-full border border-white/10 p-2.5 text-white/65 transition hover:text-white"
              aria-label="Language"
              title={lang === 'ru' ? 'English' : 'Русский'}
            >
              <Languages size={16} />
            </button>
            <button
              onClick={() => go('/profile')}
              className="hidden items-center gap-2 rounded-full border border-white/10 py-1.5 pl-1.5 pr-3 text-xs text-white/70 transition hover:text-white sm:flex"
            >
              {me?.avatar_url ? (
                <img src={me.avatar_url} alt="" className="h-6 w-6 rounded-full object-cover" />
              ) : (
                <span className="grid h-6 w-6 place-items-center rounded-full bg-white/10">
                  <User size={13} />
                </span>
              )}
              <span className="max-w-28 truncate">
                {me?.logged_in ? me.display_name || me.username || me.email : t('sign_in')}
              </span>
            </button>
            <button
              onClick={() => setMobile(!mobile)}
              className="rounded-full border border-white/10 p-2.5 lg:hidden"
              aria-label="Menu"
            >
              {mobile ? <X size={17} /> : <Menu size={17} />}
            </button>
          </div>
        </div>

        {mobile && (
          <div className="max-h-[70vh] overflow-auto border-t border-white/10 p-4 lg:hidden">
            <div className="grid grid-cols-2 gap-2">
              {TOOLS.filter((x) => x.nav).map((x) => (
                <button
                  key={x.slug}
                  onClick={() => go('/' + x.slug)}
                  className={`rounded-xl p-3 text-left text-sm transition ${
                    page === x.slug ? 'bg-cyan/15 text-cyan' : 'bg-white/5 text-white/75'
                  }`}
                >
                  {t(x.key)}
                </button>
              ))}
            </div>
            <button
              onClick={() => go('/profile')}
              className="mt-2 w-full rounded-xl bg-white/5 p-3 text-left text-sm text-white/75"
            >
              {me?.logged_in ? t('nav_profile') : t('sign_in')}
            </button>
          </div>
        )}
      </header>

      <main className="relative z-10 mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div className="animate-fade-up">
            <div className="mb-1.5 text-[10px] uppercase tracking-[0.28em] text-cyan/70">
              {t('brand')} / {page}
            </div>
            <h1 className="font-podium text-3xl uppercase leading-none tracking-tight sm:text-4xl lg:text-5xl">
              {active ? t(active.key) : page}
            </h1>
          </div>
          {page !== 'billing' && !quota?.pro && (
            <button
              onClick={() => go('/billing')}
              className="animate-fade-up rounded-full bg-white px-5 py-3 text-[11px] font-bold uppercase tracking-widest text-black transition hover:bg-frost"
            >
              PRO
            </button>
          )}
        </div>
        <div className="animate-fade-up-delay-1">{children}</div>
      </main>

      <footer className="relative z-10 mt-16 border-t border-white/10 px-4 py-8 text-center text-[11px] text-white/30 sm:px-6">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-center gap-x-5 gap-y-2">
          <span>© {new Date().getFullYear()} {t('brand')}</span>
          <button onClick={() => go('/faq')} className="hover:text-white/60">
            {t('nav_faq')}
          </button>
          <button onClick={() => go('/legal/terms')} className="hover:text-white/60">
            Terms
          </button>
          <button onClick={() => go('/legal/privacy')} className="hover:text-white/60">
            Privacy
          </button>
          <button onClick={() => go('/legal/dmca')} className="hover:text-white/60">
            DMCA
          </button>
          <span className="text-white/20">
            Not affiliated with Valve Corporation. Steam is a trademark of Valve.
          </span>
        </div>
      </footer>
    </div>
  );
}
