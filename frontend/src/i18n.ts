/**
 * RU/EN dictionary. Mirrors the data-i approach of the legacy static pages so the
 * two frontends read the same language choice from localStorage ("sm_lang").
 */
export type Lang = 'ru' | 'en';

export const LANG_KEY = 'sm_lang';

export function readLang(): Lang {
  try {
    const v = localStorage.getItem(LANG_KEY);
    if (v === 'ru' || v === 'en') return v;
  } catch {
    /* private mode */
  }
  return (navigator.language || '').toLowerCase().startsWith('ru') ? 'ru' : 'en';
}

export function writeLang(l: Lang) {
  try {
    localStorage.setItem(LANG_KEY, l);
  } catch {
    /* private mode */
  }
}

type Dict = Record<string, [string, string]>;

/** [ru, en] for every string in the app. */
const D: Dict = {
  // ---- brand / shell
  brand: ['SHOWCASE MAKER', 'SHOWCASE MAKER'],
  nav_tools: ['Инструменты', 'Tools'],
  nav_gallery: ['Галерея', 'Gallery'],
  nav_pricing: ['Тарифы', 'Pricing'],
  nav_faq: ['Помощь', 'Help'],
  nav_profile: ['Профиль', 'Profile'],
  open_tools: ['ОТКРЫТЬ ИНСТРУМЕНТЫ', 'OPEN TOOLS'],
  sign_in: ['ВОЙТИ', 'SIGN IN'],
  sign_out: ['Выйти', 'Sign out'],
  free: ['Free', 'Free'],
  pro: ['Pro', 'Pro'],

  // ---- landing
  hero_tag: ['СТУДИЯ ОФОРМЛЕНИЯ STEAM', 'STEAM PROFILE DESIGN STUDIO'],
  hero_1: ['Создавай.', 'Create.'],
  hero_2: ['Оживляй.', 'Animate.'],
  hero_3: ['Выделяйся.', 'Stand out.'],
  hero_sub_a: ['Собирай выразительные витрины Steam,', 'Build expressive Steam showcases'],
  hero_sub_b: ['которые не просто замечают —', 'that are not merely noticed —'],
  hero_sub_c: ['их запоминают.', 'they are remembered.'],
  hero_cta: ['НАЧАТЬ СОЗДАВАТЬ', 'START CREATING'],
  hero_badge_a: ['Все инструменты', 'Every tool'],
  hero_badge_b: ['В одном месте', 'In one place'],
  stat_1v: ['5+', '5+'],
  stat_1l: ['Форматов витрин', 'Showcase formats'],
  stat_2v: ['GIF', 'GIF'],
  stat_2l: ['Видео и анимация', 'Video and animation'],
  stat_3v: ['PRO', 'PRO'],
  stat_3l: ['Проекты в облаке', 'Cloud projects'],

  // ---- tool names
  t_process: ['Витрины', 'Showcases'],
  t_builder: ['Билдер', 'Builder'],
  t_mockup: ['Мокап Steam', 'Steam Mockup'],
  t_backgrounds: ['Каталог фонов', 'Background catalog'],
  t_optimizer: ['Оптимизатор GIF', 'GIF Optimizer'],
  t_achievements: ['Достижения', 'Achievements'],
  t_converter: ['Конвертер', 'Converter'],
  t_upscale: ['Апскейл', 'Upscale'],
  t_hex: ['HEX21', 'HEX21'],
  t_download: ['Загрузка по ссылке', 'Download by URL'],
  t_steam: ['Steam', 'Steam'],
  t_da: ['DeviantArt', 'DeviantArt'],
  t_gallery: ['Галерея', 'Gallery'],
  t_about: ['О сервисе', 'About'],

  // ---- tool descriptions (hub cards)
  d_process: [
    'Нарежь изображение, GIF или видео на части витрины Steam.',
    'Slice an image, GIF or video into Steam showcase parts.',
  ],
  d_builder: [
    'Собери фон, персонажа, текст, рамку и эффекты в одну работу.',
    'Combine background, character, text, frame and effects into one artwork.',
  ],
  d_mockup: [
    'Посмотри, как витрина выглядит в интерфейсе профиля Steam.',
    'Preview the showcase inside a Steam profile interface.',
  ],
  d_backgrounds: [
    'Найди статичный или анимированный фон профиля Steam.',
    'Find a static or animated Steam profile background.',
  ],
  d_optimizer: [
    'Сожми GIF под лимит Steam без потери анимации.',
    'Compress a GIF under the Steam limit without losing animation.',
  ],
  d_achievements: [
    'Собери текст из достижений для витрины достижений.',
    'Build text out of achievements for the achievement showcase.',
  ],
  d_converter: ['Переведи медиа между форматами.', 'Convert media between formats.'],
  d_upscale: ['Увеличь разрешение изображения нейросетью.', 'Upscale an image with a neural model.'],
  d_hex: ['Сделай изображение прозрачным трюком HEX21.', 'Make an image transparent with the HEX21 trick.'],
  d_download: ['Забери медиа по прямой ссылке.', 'Fetch media from a direct link.'],
  d_steam: ['Подтяни данные профиля и игр из Steam.', 'Pull profile and game data from Steam.'],
  d_da: ['Публикуй работы прямо в DeviantArt.', 'Publish artwork straight to DeviantArt.'],

  // ---- common UI
  upload: ['Загрузить файл', 'Upload file'],
  upload_hint: ['PNG, JPG, GIF, MP4 или WebM', 'PNG, JPG, GIF, MP4 or WebM'],
  drop_here: ['Перетащи файл сюда', 'Drop the file here'],
  start: ['НАЧАТЬ', 'START'],
  cancel: ['Отмена', 'Cancel'],
  download: ['СКАЧАТЬ', 'DOWNLOAD'],
  reset: ['Сбросить', 'Reset'],
  save: ['Сохранить', 'Save'],
  apply: ['Применить', 'Apply'],
  search: ['Найти', 'Search'],
  loading: ['Загрузка…', 'Loading…'],
  processing: ['Обработка…', 'Processing…'],
  done: ['Готово', 'Done'],
  error: ['Ошибка', 'Error'],
  empty: ['Пока пусто', 'Nothing here yet'],
  preview: ['Предпросмотр', 'Preview'],
  settings: ['Настройки', 'Settings'],
  result: ['Результат', 'Result'],
  choose_file: ['Выбери файл', 'Choose a file'],
  more: ['Ещё', 'More'],
  back: ['Назад', 'Back'],

  // ---- showcase modes
  mode: ['Формат витрины', 'Showcase format'],
  mode_workshop: ['Мастерская — 5 частей', 'Workshop — 5 parts'],
  mode_featured: ['Featured — 630 px', 'Featured — 630 px'],
  mode_split: ['Артворк — 506 + 100', 'Artwork — 506 + 100'],
  all_modes: ['Собрать все три формата', 'Build all three formats'],
  fps: ['Кадров в секунду', 'Frames per second'],
  size: ['Ширина', 'Width'],
  encoder: ['Кодировщик GIF', 'GIF encoder'],
  auto_contrast: ['Автоконтраст', 'Auto contrast'],

  // ---- watermark
  wm: ['Водяной знак', 'Watermark'],
  wm_on: ['Включить водяной знак', 'Enable watermark'],
  wm_text: ['Текст', 'Text'],
  wm_font: ['Шрифт', 'Font'],
  wm_opacity: ['Прозрачность', 'Opacity'],
  wm_color: ['Цвет', 'Color'],
  wm_corner: ['Угол', 'Corner'],
  wm_scale: ['Размер', 'Size'],
  wm_drag: ['Перетащи знак по превью', 'Drag the mark across the preview'],
  wm_locked: [
    'На бесплатном тарифе водяной знак сервиса обязателен. Pro снимает его.',
    'On the free plan the service watermark is mandatory. Pro removes it.',
  ],
  corner_tl: ['Слева сверху', 'Top left'],
  corner_tr: ['Справа сверху', 'Top right'],
  corner_bl: ['Слева снизу', 'Bottom left'],
  corner_br: ['Справа снизу', 'Bottom right'],

  // ---- builder
  layer_bg: ['Фон', 'Background'],
  layer_char: ['Персонаж', 'Character'],
  layer_text: ['Текст', 'Text'],
  layer_frame: ['Рамка', 'Frame'],
  layer_fx: ['Эффекты', 'Effects'],
  layers: ['Слои', 'Layers'],
  chroma: ['Хромакей', 'Chroma key'],
  chroma_auto: ['Автоматически', 'Automatic'],
  chroma_green: ['Зелёный', 'Green'],
  chroma_blue: ['Синий', 'Blue'],
  chroma_off: ['Не удалять', 'Keep as is'],
  chroma_tol: ['Допуск', 'Tolerance'],
  feather: ['Смягчение края', 'Edge feather'],
  scale: ['Масштаб', 'Scale'],
  pos_x: ['Позиция по X', 'Position X'],
  pos_y: ['Позиция по Y', 'Position Y'],
  rotate: ['Поворот', 'Rotation'],
  opacity: ['Непрозрачность', 'Opacity'],
  font_size: ['Кегль', 'Font size'],
  render: ['СОБРАТЬ РАБОТУ', 'RENDER ARTWORK'],
  send_to_process: ['Отправить в витрины', 'Send to showcases'],

  // ---- backgrounds
  bg_search: ['Название фона или игры', 'Background or game name'],
  bg_kind: ['Тип', 'Type'],
  bg_all: ['Все', 'All'],
  bg_static: ['Статичные', 'Static'],
  bg_animated: ['Анимированные', 'Animated'],
  bg_use: ['В билдер', 'To builder'],
  bg_open: ['Открыть в Steam', 'Open in Steam'],

  // ---- achievements
  ach_appid: ['AppID игры в Steam', 'Steam game AppID'],
  ach_filter: ['Фильтр по названию', 'Filter by name'],
  ach_load: ['ЗАГРУЗИТЬ', 'LOAD'],
  ach_picked: ['Выбрано', 'Selected'],
  ach_hint: [
    'Выбери достижения — из их названий сложится строка для витрины.',
    'Pick achievements — their names compose the showcase line.',
  ],

  // ---- optimizer
  opt_target: ['Целевой размер, МБ', 'Target size, MB'],
  opt_hint: [
    'Steam принимает GIF до 5 МБ в витринах артворка.',
    'Steam accepts GIFs up to 5 MB in artwork showcases.',
  ],

  // ---- gallery
  g_publish: ['Опубликовать', 'Publish'],
  g_pending: ['На модерации', 'Pending review'],
  g_likes: ['Лайки', 'Likes'],
  g_comments: ['Комментарии', 'Comments'],
  g_comment_ph: ['Написать комментарий…', 'Write a comment…'],
  g_send: ['Отправить', 'Send'],
  g_title: ['Название работы', 'Artwork title'],
  g_approve: ['Одобрить', 'Approve'],
  g_reject: ['Отклонить', 'Reject'],
  g_delete: ['Удалить', 'Delete'],

  // ---- auth / profile
  email: ['Почта', 'Email'],
  password: ['Пароль', 'Password'],
  login: ['Войти', 'Log in'],
  register: ['Регистрация', 'Sign up'],
  display_name: ['Отображаемое имя', 'Display name'],
  username: ['Никнейм', 'Username'],
  bio: ['О себе', 'About me'],
  avatar: ['Аватар', 'Avatar'],
  my_library: ['Мои работы', 'My library'],
  my_showcases: ['Мои витрины', 'My showcases'],
  projects: ['Проекты', 'Projects'],
  no_projects: ['Сохранённых проектов пока нет.', 'No saved projects yet.'],
  pro_only: ['Доступно в Pro', 'Pro only'],
  login_required: ['Нужно войти в аккаунт', 'You need to sign in'],
  quota_left: ['Осталось сегодня', 'Left today'],
  access_code: ['Код доступа', 'Access code'],
  unlock: ['Активировать', 'Activate'],

  // ---- billing
  price_free_t: ['Бесплатно', 'Free'],
  price_pro_t: ['Showcase Maker Pro', 'Showcase Maker Pro'],
  buy_pro: ['ОФОРМИТЬ PRO', 'GET PRO'],
  f_free_1: ['Основные инструменты', 'Core tools'],
  f_free_2: ['Ограниченный дневной экспорт', 'Limited daily export'],
  f_free_3: ['Водяной знак сервиса на работах', 'Service watermark on exports'],
  f_pro_1: ['Без водяного знака сервиса', 'No service watermark'],
  f_pro_2: ['Сохранение проектов билдера', 'Saved builder projects'],
  f_pro_3: ['Максимальное качество GIF и видео', 'Maximum GIF and video quality'],
  f_pro_4: ['Без дневного лимита', 'No daily limit'],
};

export function makeT(lang: Lang) {
  const i = lang === 'ru' ? 0 : 1;
  return (key: string): string => {
    const row = D[key];
    return row ? row[i] : key;
  };
}

export type T = ReturnType<typeof makeT>;
