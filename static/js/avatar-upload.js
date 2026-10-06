/* Change / remove the account avatar from any page (2026-10-06): account page hero and the public
   profile page dock. SMAvatar.pick(done) opens the file picker and uploads to /api/account/avatar;
   SMAvatar.remove(done) clears it. done({ok, avatar_url} | {ok:false, message}). After a change the
   shell header is refreshed (SSShell.loadMe) and every img[data-sm-avatar] on the page is updated. */
(function () {
  'use strict';
  if (window.SMAvatar) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { change: 'Change avatar', remove: 'Remove avatar', uploading: 'Uploading…', saved: 'Avatar updated', removed: 'Avatar removed', hint: 'PNG, JPG, WebP or GIF up to 6 MB · animated GIF / WebP up to 3 MB', confirm: 'Remove your avatar?', too_big: 'The file is larger than 6 MB.', animated_too_big: 'An animated avatar must be under 3 MB.', too_large: 'The picture is too large. Use one under 16 megapixels.', bad_image: 'This file is not a picture we can read. Use PNG, JPG, WebP or GIF.', login: 'Log in again to change the avatar.', failed: 'Could not save the avatar. Try again.' },
    ru: { change: 'Сменить аватар', remove: 'Удалить аватар', uploading: 'Загружаем…', saved: 'Аватар обновлён', removed: 'Аватар удалён', hint: 'PNG, JPG, WebP или GIF до 6 МБ · анимированные GIF / WebP до 3 МБ', confirm: 'Удалить аватар?', too_big: 'Файл больше 6 МБ.', animated_too_big: 'Анимированный аватар должен весить меньше 3 МБ.', too_large: 'Картинка слишком большая. Возьми до 16 мегапикселей.', bad_image: 'Не удалось прочитать картинку. Подойдут PNG, JPG, WebP или GIF.', login: 'Войди снова, чтобы сменить аватар.', failed: 'Не удалось сохранить аватар. Попробуй ещё раз.' },
    de: { change: 'Avatar ändern', remove: 'Avatar entfernen', uploading: 'Wird hochgeladen…', saved: 'Avatar aktualisiert', removed: 'Avatar entfernt', hint: 'PNG, JPG, WebP oder GIF bis 6 MB · animierte GIF / WebP bis 3 MB', confirm: 'Avatar entfernen?', too_big: 'Die Datei ist größer als 6 MB.', animated_too_big: 'Ein animierter Avatar muss kleiner als 3 MB sein.', too_large: 'Das Bild ist zu groß. Nimm eines unter 16 Megapixeln.', bad_image: 'Das Bild konnte nicht gelesen werden. Nutze PNG, JPG, WebP oder GIF.', login: 'Melde dich erneut an, um den Avatar zu ändern.', failed: 'Der Avatar konnte nicht gespeichert werden. Versuche es erneut.' },
    tr: { change: 'Avatarı değiştir', remove: 'Avatarı kaldır', uploading: 'Yükleniyor…', saved: 'Avatar güncellendi', removed: 'Avatar kaldırıldı', hint: '6 MB’a kadar PNG, JPG, WebP veya GIF · hareketli GIF / WebP 3 MB’a kadar', confirm: 'Avatar kaldırılsın mı?', too_big: 'Dosya 6 MB’tan büyük.', animated_too_big: 'Hareketli avatar 3 MB’tan küçük olmalı.', too_large: 'Resim çok büyük. 16 megapikselden küçük bir resim kullan.', bad_image: 'Resim okunamadı. PNG, JPG, WebP veya GIF kullan.', login: 'Avatarı değiştirmek için yeniden giriş yap.', failed: 'Avatar kaydedilemedi. Tekrar dene.' },
    fr: { change: 'Changer d’avatar', remove: 'Supprimer l’avatar', uploading: 'Envoi…', saved: 'Avatar mis à jour', removed: 'Avatar supprimé', hint: 'PNG, JPG, WebP ou GIF jusqu’à 6 Mo · GIF / WebP animés jusqu’à 3 Mo', confirm: 'Supprimer votre avatar ?', too_big: 'Le fichier dépasse 6 Mo.', animated_too_big: 'Un avatar animé doit faire moins de 3 Mo.', too_large: 'L’image est trop grande. Utilisez moins de 16 mégapixels.', bad_image: 'Image illisible. Utilisez PNG, JPG, WebP ou GIF.', login: 'Reconnectez-vous pour changer d’avatar.', failed: 'Impossible d’enregistrer l’avatar. Réessayez.' },
    uk: { change: 'Змінити аватар', remove: 'Видалити аватар', uploading: 'Завантажуємо…', saved: 'Аватар оновлено', removed: 'Аватар видалено', hint: 'PNG, JPG, WebP або GIF до 6 МБ · анімовані GIF / WebP до 3 МБ', confirm: 'Видалити аватар?', too_big: 'Файл більший за 6 МБ.', animated_too_big: 'Анімований аватар має важити менше 3 МБ.', too_large: 'Зображення завелике. Візьми до 16 мегапікселів.', bad_image: 'Не вдалося прочитати зображення. Підійдуть PNG, JPG, WebP або GIF.', login: 'Увійди знову, щоб змінити аватар.', failed: 'Не вдалося зберегти аватар. Спробуй ще раз.' },
    es: { change: 'Cambiar avatar', remove: 'Quitar avatar', uploading: 'Subiendo…', saved: 'Avatar actualizado', removed: 'Avatar eliminado', hint: 'PNG, JPG, WebP o GIF hasta 6 MB · GIF / WebP animados hasta 3 MB', confirm: '¿Quitar tu avatar?', too_big: 'El archivo supera los 6 MB.', animated_too_big: 'Un avatar animado debe pesar menos de 3 MB.', too_large: 'La imagen es demasiado grande. Usa una de menos de 16 megapíxeles.', bad_image: 'No se pudo leer la imagen. Usa PNG, JPG, WebP o GIF.', login: 'Vuelve a iniciar sesión para cambiar el avatar.', failed: 'No se pudo guardar el avatar. Inténtalo de nuevo.' },
    pt: { change: 'Trocar avatar', remove: 'Remover avatar', uploading: 'Enviando…', saved: 'Avatar atualizado', removed: 'Avatar removido', hint: 'PNG, JPG, WebP ou GIF até 6 MB · GIF / WebP animados até 3 MB', confirm: 'Remover seu avatar?', too_big: 'O arquivo tem mais de 6 MB.', animated_too_big: 'Um avatar animado precisa ter menos de 3 MB.', too_large: 'A imagem é grande demais. Use uma com menos de 16 megapixels.', bad_image: 'Não foi possível ler a imagem. Use PNG, JPG, WebP ou GIF.', login: 'Entre de novo para trocar o avatar.', failed: 'Não foi possível salvar o avatar. Tente de novo.' }
  };
  function lang() {
    var l = (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang || 'en').slice(0, 2);
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function t(key) { return COPY[lang()][key] || COPY.en[key] || key; }

  function refresh(url) {
    document.querySelectorAll('img[data-sm-avatar]').forEach(function (img) { if (url) img.src = url; });
    if (window.SSShell && SSShell.loadMe) SSShell.loadMe();
  }

  function upload(file, done) {
    var data = new FormData(); data.append('file', file);
    fetch('/api/account/avatar', { method: 'POST', credentials: 'same-origin', body: data })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (res) {
        if (res.ok && res.body.ok) { refresh(res.body.avatar_url); done({ ok: true, avatar_url: res.body.avatar_url, message: t('saved') }); }
        else done({ ok: false, message: t(res.body.code || 'failed') });
      })
      .catch(function () { done({ ok: false, message: t('failed') }); });
  }

  function pick(done) {
    var input = document.createElement('input');
    input.type = 'file'; input.accept = 'image/png,image/jpeg,image/webp,image/gif';
    input.dataset.smEnhanced = '1';
    input.style.display = 'none';
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      input.remove();
      if (!file) return;
      if (file.size > 6 * 1024 * 1024) { done({ ok: false, message: t('too_big') }); return; }
      done({ ok: null, message: t('uploading') });
      upload(file, done);
    });
    document.body.appendChild(input);
    input.click();
  }

  function remove(done) {
    if (!window.confirm(t('confirm'))) return;
    fetch('/api/account/avatar', { method: 'DELETE', credentials: 'same-origin' })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (res) {
        if (res.ok && res.body.ok) { refresh(''); done({ ok: true, avatar_url: '', message: t('removed') }); }
        else done({ ok: false, message: t(res.body.code || 'failed') });
      })
      .catch(function () { done({ ok: false, message: t('failed') }); });
  }

  window.SMAvatar = { pick: pick, remove: remove, t: t };
})();
