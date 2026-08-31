/** Landing page — cinematic video hero with a readable brand overlay. */
import React, { useState } from 'react';
import { ArrowUpRight, Award, Crown, X, Languages, Puzzle, Download } from 'lucide-react';
import { GradientField } from '../ui';
import { go, TOOLS } from '../routes';
import type { Lang, T } from '../i18n';

export function Home({
  lang,
  setLang,
  t,
}: {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: T;
}) {
  const [open, setOpen] = useState(false);

  const links: [string, string][] = [
    [t('nav_tools'), '/app'],
    [t('t_builder'), '/builder'],
    [t('nav_gallery'), '/gallery'],
    [t('nav_pricing'), '/billing'],
  ];

  return (
    <main className="relative h-[100svh] min-h-[680px] overflow-hidden bg-ink text-white">
      <video
        className="absolute inset-0 h-full w-full object-cover opacity-45"
        src="/static/video/hero.mp4"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        aria-hidden="true"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,7,11,.96)_0%,rgba(5,7,11,.68)_48%,rgba(5,7,11,.34)_100%)]" />
      <GradientField intense />

      {/* ---------------- navbar ---------------- */}
      <nav className="relative z-20 flex items-center px-6 py-5 sm:px-10 lg:px-16 lg:py-7">
        <button
          onClick={() => go('/')}
          className="font-podium text-2xl font-bold uppercase tracking-wider sm:text-3xl"
        >
          {t('brand')}
        </button>

        <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-8 md:flex">
          {links.map(([name, path]) => (
            <button
              key={path}
              onClick={() => go(path)}
              className="font-inter text-sm uppercase tracking-widest text-white/80 transition hover:text-white"
            >
              {name}
            </button>
          ))}
        </div>

        <div className="ml-auto hidden items-center gap-3 md:flex">
          <button
            onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}
            className="p-3 text-white/70 transition hover:text-white"
            aria-label="Language"
          >
            <Languages size={18} />
          </button>
          <button
            onClick={() => go('/app')}
            className="group flex items-center gap-2 border border-white/30 px-6 py-3 text-xs uppercase tracking-widest transition hover:border-white/60 hover:bg-white/10"
          >
            {t('open_tools')}
            <ArrowUpRight size={15} className="transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </button>
        </div>

        <button
          onClick={() => setOpen(true)}
          className="ml-auto space-y-1.5 md:hidden"
          aria-label="Menu"
        >
          <span className="block h-0.5 w-6 bg-white" />
          <span className="block h-0.5 w-6 bg-white" />
          <span className="block h-0.5 w-4 bg-white" />
        </button>
      </nav>

      {/* ---------------- mobile overlay ---------------- */}
      <div
        className={`fixed inset-0 z-50 bg-black/95 backdrop-blur-sm transition-all duration-500 md:hidden ${
          open ? 'visible opacity-100' : 'invisible opacity-0'
        }`}
      >
        <div className="flex items-center justify-between px-6 py-5">
          <b className="font-podium text-2xl uppercase tracking-wider">{t('brand')}</b>
          <button onClick={() => setOpen(false)} aria-label="Close">
            <X />
          </button>
        </div>
        <div className="flex h-[calc(100%-80px)] flex-col items-center justify-center gap-5">
          {links.map(([name, path], i) => (
            <button
              key={path}
              onClick={() => {
                setOpen(false);
                go(path);
              }}
              style={{ transitionDelay: `${i * 80 + 100}ms` }}
              className={`font-podium text-4xl uppercase transition-all duration-500 sm:text-5xl ${
                open ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'
              }`}
            >
              {name}
            </button>
          ))}
          <button
            onClick={() => {
              setOpen(false);
              go('/app');
            }}
            style={{ transitionDelay: `${links.length * 80 + 100}ms` }}
            className={`mt-5 border border-white/30 px-7 py-3 text-xs uppercase tracking-widest transition-all duration-500 ${
              open ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'
            }`}
          >
            {t('open_tools')}
          </button>
          <button
            onClick={() => setLang(lang === 'ru' ? 'en' : 'ru')}
            className="mt-2 text-xs uppercase tracking-widest text-white/50"
          >
            {lang === 'ru' ? 'ENGLISH' : 'РУССКИЙ'}
          </button>
        </div>
      </div>

      {/* ---------------- hero ---------------- */}
      <section className="relative z-10 flex h-[calc(100%-90px)] items-center px-6 pb-16 sm:px-10 lg:px-16">
        <div>
          <div className="animate-fade-up mb-6 flex items-center gap-3 font-inter text-xs uppercase tracking-[0.3em] text-white/70 sm:text-sm lg:mb-8">
            <Crown className="h-4 w-4 shrink-0" />
            {t('hero_tag')}
          </div>

          <h1 className="animate-fade-up-delay-1 font-podium uppercase leading-[0.92] tracking-tight">
            {[t('hero_1'), t('hero_2'), t('hero_3')].map((line) => (
              <span key={line} className="block text-[clamp(2.8rem,8vw,7rem)]">
                {line}
              </span>
            ))}
          </h1>

          <p className="animate-fade-up-delay-2 mt-6 max-w-md font-inter text-sm leading-relaxed text-white/70 sm:text-base lg:mt-8">
            {t('hero_sub_a')}
            <br />
            {t('hero_sub_b')} <b className="text-white">{t('hero_sub_c')}</b>
          </p>

          <div className="animate-fade-up-delay-3 mt-8 flex flex-wrap items-center gap-4 sm:gap-6 lg:mt-10">
            <button
              onClick={() => go('/builder')}
              className="group flex items-center gap-2 bg-black px-5 py-3 text-[11px] uppercase tracking-widest transition hover:bg-neutral-900 sm:px-7 sm:py-4 sm:text-xs"
            >
              {t('hero_cta')}
              <ArrowUpRight
                size={15}
                className="transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              />
            </button>
            <div className="hidden items-center gap-3 sm:flex">
              <Award className="h-8 w-8 text-white/50" />
              <span className="text-xs uppercase tracking-wider text-white/60">
                {t('hero_badge_a')}
                <br />
                {t('hero_badge_b')}
              </span>
            </div>
          </div>

          <div className="animate-fade-up-delay-4 mt-8 flex flex-wrap gap-6 sm:mt-10 sm:gap-12 lg:mt-14 lg:gap-16">
            {[
              [t('stat_1v'), t('stat_1l')],
              [t('stat_2v'), t('stat_2l')],
              [t('stat_3v'), t('stat_3l')],
            ].map(([v, l]) => (
              <div key={l}>
                <b className="font-inter text-2xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
                  {v}
                </b>
                <div className="mt-1 text-[9px] uppercase tracking-widest text-white/50 sm:text-xs">
                  {l}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <aside className="glass absolute right-[5vw] top-1/2 z-10 hidden w-[360px] -translate-y-1/2 rounded-[28px] p-6 xl:block">
        <div className="mb-5 flex items-center gap-4">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-white text-black"><Puzzle size={26} /></div>
          <div><div className="text-[10px] uppercase tracking-[.25em] text-cyan">Browser extension</div><h2 className="mt-1 text-xl font-semibold">Showcase Helper</h2></div>
        </div>
        <p className="text-sm leading-relaxed text-white/55">{lang === 'ru' ? 'Инструменты витрин всегда под рукой: подготовка файлов, предпросмотр и быстрая загрузка в Steam.' : 'Showcase tools are always one click away: prepare files, preview and upload to Steam faster.'}</p>
        <a href="/static/downloads/SteamShowcase-Helper-v0.9.zip" download className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-white px-5 py-3 text-xs font-semibold uppercase tracking-widest text-black transition hover:bg-cyan">
          <Download size={14} />{lang === 'ru' ? 'Скачать расширение' : 'Download extension'}
        </a>
        <p className="mt-3 text-center text-[10px] text-white/30">Chrome · Chromium · v0.9</p>
      </aside>

      {/* Quick tool strip along the bottom on large screens. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 hidden justify-center pb-6 lg:flex">
        <div className="pointer-events-auto flex gap-2 rounded-full border border-white/10 bg-black/50 p-2 backdrop-blur-xl">
          {TOOLS.filter((x) => x.hub)
            .slice(0, 6)
            .map((x) => (
              <button
                key={x.slug}
                onClick={() => go('/' + x.slug)}
                className="rounded-full px-4 py-2 text-[11px] uppercase tracking-widest text-white/55 transition hover:bg-white/10 hover:text-white"
              >
                {t(x.key)}
              </button>
            ))}
        </div>
      </div>
    </main>
  );
}
