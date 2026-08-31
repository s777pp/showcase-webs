/** Route table + tiny history-based navigation (no router dependency). */

export type Tool = {
  slug: string;
  key: string; // i18n key for the display name
  desc: string; // i18n key for the hub card description
  nav: boolean; // show in the header navigation
  hub: boolean; // show as a card on the tools hub
};

export const TOOLS: Tool[] = [
  { slug: 'app', key: 'nav_tools', desc: 'd_process', nav: true, hub: false },
  { slug: 'builder', key: 't_builder', desc: 'd_builder', nav: true, hub: true },
  { slug: 'process', key: 't_process', desc: 'd_process', nav: true, hub: true },
  { slug: 'mockup', key: 't_mockup', desc: 'd_mockup', nav: true, hub: true },
  { slug: 'backgrounds', key: 't_backgrounds', desc: 'd_backgrounds', nav: true, hub: true },
  { slug: 'optimizer', key: 't_optimizer', desc: 'd_optimizer', nav: true, hub: true },
  { slug: 'achievements', key: 't_achievements', desc: 'd_achievements', nav: true, hub: true },
  { slug: 'converter', key: 't_converter', desc: 'd_converter', nav: false, hub: true },
  { slug: 'upscale', key: 't_upscale', desc: 'd_upscale', nav: false, hub: true },
  { slug: 'hex', key: 't_hex', desc: 'd_hex', nav: false, hub: true },
  { slug: 'download', key: 't_download', desc: 'd_download', nav: false, hub: true },
  { slug: 'steam', key: 't_steam', desc: 'd_steam', nav: false, hub: true },
  { slug: 'deviantart', key: 't_da', desc: 'd_da', nav: false, hub: true },
  { slug: 'gallery', key: 'nav_gallery', desc: 'd_process', nav: true, hub: false },
  { slug: 'profile', key: 'nav_profile', desc: 'd_process', nav: false, hub: false },
  { slug: 'billing', key: 'nav_pricing', desc: 'd_process', nav: false, hub: false },
  { slug: 'faq', key: 'nav_faq', desc: 'd_process', nav: false, hub: false },
  { slug: 'legal', key: 'nav_faq', desc: 'd_process', nav: false, hub: false },
];

/** Client-side navigation: push the URL and let App re-render on popstate. */
export function go(path: string) {
  if (location.pathname === path) return;
  history.pushState({}, '', path);
  dispatchEvent(new PopStateEvent('popstate'));
  window.scrollTo({ top: 0 });
}
