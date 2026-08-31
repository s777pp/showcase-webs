/**
 * Thin wrappers over the FastAPI backend in main.py.
 * Every path here exists as a route in main.py — nothing is invented.
 */

export type Me = {
  logged_in?: boolean;
  id?: number;
  email?: string;
  username?: string;
  display_name?: string;
  avatar_url?: string;
  is_pro?: boolean;
  bio?: string;
};

export type Quota = {
  used: number;
  limit: number;
  left: number;
  pro: boolean;
  label?: string;
  remaining_sec?: number | null;
  is_trial?: boolean;
};

async function j<T>(r: Response): Promise<T> {
  const text = await r.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!r.ok) {
    const msg = (data && (data.msg || data.detail || data.error)) || `HTTP ${r.status}`;
    const err = new Error(String(msg)) as Error & { code?: string; status?: number };
    err.code = data?.code;
    err.status = r.status;
    throw err;
  }
  return data as T;
}

export const api = {
  // ---------- auth ----------
  me: () => fetch('/api/auth/me').then((r) => j<Me>(r)),
  quota: () => fetch('/api/quota').then((r) => j<Quota>(r)),
  meta: () => fetch('/api/meta').then((r) => j<any>(r)),
  register: (email: string, password: string) =>
    fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }).then((r) => j<any>(r)),
  login: (email: string, password: string) =>
    fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    }).then((r) => j<any>(r)),
  logout: () => fetch('/api/auth/logout', { method: 'POST' }).then((r) => j<any>(r)),
  saveProfile: (fd: FormData) =>
    fetch('/api/auth/profile', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  unlock: (code: string) =>
    fetch('/api/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    }).then((r) => j<any>(r)),
  telegramConfig: () => fetch('/api/auth/telegram/config').then((r) => j<any>(r)),

  // ---------- showcase pipeline ----------
  processStart: (fd: FormData) =>
    fetch('/api/process/start', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  processStatus: (id: string) =>
    fetch(`/api/process/status/${encodeURIComponent(id)}`).then((r) => j<any>(r)),
  processDownloadUrl: (id: string) => `/api/process/download/${encodeURIComponent(id)}`,
  jobFileUrl: (id: string, name: string) =>
    `/api/job-file/${encodeURIComponent(id)}/${encodeURIComponent(name)}`,

  previewWm: (fd: FormData) => fetch('/api/preview_wm', { method: 'POST', body: fd }),
  previewSlots: (mode: string) =>
    fetch(`/api/preview-slots?mode=${encodeURIComponent(mode)}`).then((r) => j<any>(r)),
  previewBuild: (fd: FormData) =>
    fetch('/api/preview-build', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  previewTemplateUrl: (mode: string) => `/api/preview-template/${encodeURIComponent(mode)}`,

  // ---------- media tools ----------
  convert: (fd: FormData) => fetch('/api/convert', { method: 'POST', body: fd }),
  hex21: (fd: FormData) => fetch('/api/hex21', { method: 'POST', body: fd }),
  compose: (fd: FormData) => fetch('/api/compose', { method: 'POST', body: fd }),
  upscale: (fd: FormData) => fetch('/api/upscale', { method: 'POST', body: fd }),
  upscaleModels: () => fetch('/api/upscale/models').then((r) => j<any>(r)),
  downloadUrl: (url: string, quality = 'best') =>
    fetch('/api/download-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, quality }),
    }).then((r) => j<any>(r)),

  // ---------- new tools (added to main.py alongside the originals) ----------
  optimize: (fd: FormData) => fetch('/api/optimizer', { method: 'POST', body: fd }),
  builderRender: (fd: FormData) => fetch('/api/builder/render', { method: 'POST', body: fd }),
  backgrounds: (q: string, page = 0, kind = 'all', count = 24, asset = 'background') =>
    fetch(
      `/api/steam/backgrounds?q=${encodeURIComponent(q)}&page=${page}&kind=${encodeURIComponent(
        kind,
      )}&count=${count}&asset=${encodeURIComponent(asset)}`,
    ).then((r) => j<any>(r)),
  achievements: (appid: string) =>
    fetch(`/api/steam/achievements/${encodeURIComponent(appid)}`).then((r) => j<any>(r)),
  steamApps: (q: string) =>
    fetch(`/api/steam/apps?q=${encodeURIComponent(q)}`).then((r) => j<any>(r)),
  steamProfile: (url: string) =>
    fetch(`/api/steam/profile?url=${encodeURIComponent(url)}`).then((r) => j<any>(r)),
  projects: () => fetch('/api/projects').then((r) => j<any>(r)),
  projectSave: (body: any) =>
    fetch('/api/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => j<any>(r)),
  projectDelete: (id: number) =>
    fetch(`/api/projects/${id}`, { method: 'DELETE' }).then((r) => j<any>(r)),

  // ---------- gallery ----------
  galleryList: (status = 'approved', limit = 40, offset = 0) =>
    fetch(`/api/gallery/list?status=${status}&limit=${limit}&offset=${offset}`).then((r) =>
      j<any>(r),
    ),
  galleryPublish: (fd: FormData) =>
    fetch('/api/gallery/publish', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  galleryLike: (id: number) =>
    fetch(`/api/gallery/${id}/like`, { method: 'POST' }).then((r) => j<any>(r)),
  galleryComments: (id: number) =>
    fetch(`/api/gallery/${id}/comments`).then((r) => j<any>(r)),
  galleryComment: (id: number, text: string) =>
    fetch(`/api/gallery/${id}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }).then((r) => j<any>(r)),
  galleryDelete: (id: number) =>
    fetch(`/api/gallery/delete/${id}`, { method: 'POST' }).then((r) => j<any>(r)),
  galleryMod: (id: number, action: string) =>
    fetch(`/api/gallery/mod/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    }).then((r) => j<any>(r)),
  galleryAmAdmin: () => fetch('/api/gallery/am_admin').then((r) => j<any>(r)),
  galleryImageUrl: (id: number) => `/api/gallery/image/${id}`,

  // ---------- profile ----------
  profileMe: () => fetch('/api/profile/me').then((r) => j<any>(r)),
  profileOf: (username: string) =>
    fetch(`/api/profile/${encodeURIComponent(username)}`).then((r) => j<any>(r)),
  profileShowcases: (username: string) =>
    fetch(`/api/profile/${encodeURIComponent(username)}/showcases`).then((r) => j<any>(r)),
  profileLibrary: () => fetch('/api/profile/my-library').then((r) => j<any>(r)),
  profileUpdate: (body: any) =>
    fetch('/api/profile/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => j<any>(r)),
  showcaseAdd: (fd: FormData) =>
    fetch('/api/profile/showcase/add', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  showcaseDelete: (id: number) =>
    fetch('/api/profile/showcase/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then((r) => j<any>(r)),

  // ---------- notifications ----------
  notifications: () => fetch('/api/notifications').then((r) => j<any>(r)),
  notificationsUnread: () => fetch('/api/notifications/unread').then((r) => j<any>(r)),
  notificationsRead: () => fetch('/api/notifications/read', { method: 'POST' }).then((r) => j<any>(r)),

  // ---------- deviantart ----------
  daStatus: () => fetch('/api/da/status').then((r) => j<any>(r)),
  daUpload: (fd: FormData) => fetch('/api/da/upload', { method: 'POST', body: fd }).then((r) => j<any>(r)),
  daLogout: () => fetch('/api/da/logout', { method: 'POST' }).then((r) => j<any>(r)),
  daKeys: (client_id: string, client_secret: string) =>
    fetch('/api/da/keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client_id, client_secret }),
    }).then((r) => j<any>(r)),

  // ---------- billing ----------
  checkout: () => fetch('/api/billing/checkout', { method: 'POST' }).then((r) => j<any>(r)),
};

/** Trigger a browser download for a fetched blob response. */
export async function saveBlob(res: Response, filename: string) {
  if (!res.ok) {
    const t = await res.text();
    let msg = `HTTP ${res.status}`;
    try {
      msg = JSON.parse(t).msg || msg;
    } catch {
      /* not json */
    }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 8000);
}
