/* "Upload to Steam automatically" in the gallery work window (owner, 2026-10-08).
   The server picks the Steam-ready parts of the work's ZIP for its showcase type (GET /api/gallery/works/{id}/steam,
   smweb/gallery_steam.py: order, names, HEX 21), this file reads them and hands them to SteamShowcase Helper with
   START_AUTO_UPLOAD - the same message the Steam Check report uses (steam-check.js). The extension uploads them on
   the visitor's own Steam session in a new tab; nothing here talks to Steam.
   The button follows #detailDownload (community-gallery.js shows it for free works with a ZIP), so the gallery code
   needs no changes. Copy: 8 languages, checked by scripts/check_i18n.js. */
(function () {
  'use strict';
  var EXTENSION_ID = 'nopmeakgeongafdhgmlpllalpcfpedej';
  var STORE_URL = 'https://chromewebstore.google.com/detail/steamshowcase-helper/nopmeakgeongafdhgmlpllalpcfpedej';
  var MIN_VERSION = '1.0.3';
  var COPY = {
    en: { button: 'Upload to Steam automatically', hint: 'SteamShowcase Helper uploads the files on your Steam account in a new tab.',
      checking: 'Looking for the extension…', preparing: 'Preparing the files…', sending: 'Handing the files to the extension…',
      started: 'Done: the extension opened an upload tab and is sending the files to Steam. When it finishes, it offers to put them into your showcase.',
      missing: 'Install SteamShowcase Helper (free) to upload in one click.', install: 'Install the extension', more: 'What it does',
      old: 'Update SteamShowcase Helper to the latest version, then try again.', login: 'Sign in to upload this work.',
      noSet: 'This work has no ready set of files for its showcase type. Download the ZIP and upload it by hand.',
      tooLarge: 'Some files of this work are over Steam’s 5 MB limit. Download the ZIP instead.',
      busy: 'The extension is already uploading another set. Wait until it finishes.',
      failed: 'Could not start the upload. Try again or download the ZIP.', choose: 'This work has several sets. Which one?', main: 'Main set' },
    ru: { button: 'Загрузить в Steam автоматически', hint: 'SteamShowcase Helper загрузит файлы в твой аккаунт Steam в новой вкладке.',
      checking: 'Ищем расширение…', preparing: 'Готовим файлы…', sending: 'Передаём файлы расширению…',
      started: 'Готово: расширение открыло вкладку загрузки и отправляет файлы в Steam. В конце оно предложит поставить их в витрину.',
      missing: 'Установи SteamShowcase Helper (бесплатно), чтобы загружать в один клик.', install: 'Установить расширение', more: 'Что оно умеет',
      old: 'Обнови SteamShowcase Helper до последней версии и попробуй ещё раз.', login: 'Войди в аккаунт, чтобы загрузить эту работу.',
      noSet: 'В этой работе нет готового набора файлов под её тип витрины. Скачай ZIP и загрузи вручную.',
      tooLarge: 'Часть файлов этой работы больше лимита Steam в 5 МБ. Скачай ZIP.',
      busy: 'Расширение уже загружает другой набор. Дождись, пока оно закончит.',
      failed: 'Не получилось начать загрузку. Попробуй ещё раз или скачай ZIP.', choose: 'В работе несколько наборов. Какой загрузить?', main: 'Основной набор' },
    de: { button: 'Automatisch zu Steam hochladen', hint: 'SteamShowcase Helper lädt die Dateien in einem neuen Tab in dein Steam-Konto hoch.',
      checking: 'Suche die Erweiterung…', preparing: 'Dateien werden vorbereitet…', sending: 'Dateien werden an die Erweiterung übergeben…',
      started: 'Fertig: Die Erweiterung hat einen Upload-Tab geöffnet und sendet die Dateien an Steam. Danach bietet sie an, sie in dein Showcase einzusetzen.',
      missing: 'Installiere SteamShowcase Helper (kostenlos), um mit einem Klick hochzuladen.', install: 'Erweiterung installieren', more: 'Was sie kann',
      old: 'Aktualisiere SteamShowcase Helper auf die neueste Version und versuche es erneut.', login: 'Melde dich an, um dieses Werk hochzuladen.',
      noSet: 'Dieses Werk hat keinen fertigen Dateisatz für seinen Showcase-Typ. Lade die ZIP herunter und lade sie von Hand hoch.',
      tooLarge: 'Einige Dateien dieses Werks sind größer als Steams Limit von 5 MB. Lade stattdessen die ZIP herunter.',
      busy: 'Die Erweiterung lädt schon einen anderen Satz hoch. Warte, bis sie fertig ist.',
      failed: 'Der Upload konnte nicht gestartet werden. Versuche es erneut oder lade die ZIP herunter.', choose: 'Dieses Werk hat mehrere Sätze. Welchen?', main: 'Hauptsatz' },
    tr: { button: 'Steam’e otomatik yükle', hint: 'SteamShowcase Helper dosyaları yeni bir sekmede Steam hesabına yükler.',
      checking: 'Eklenti aranıyor…', preparing: 'Dosyalar hazırlanıyor…', sending: 'Dosyalar eklentiye aktarılıyor…',
      started: 'Tamam: eklenti bir yükleme sekmesi açtı ve dosyaları Steam’e gönderiyor. Bitince onları vitrine yerleştirmeyi önerir.',
      missing: 'Tek tıkla yüklemek için SteamShowcase Helper’ı (ücretsiz) kur.', install: 'Eklentiyi kur', more: 'Neler yapar',
      old: 'SteamShowcase Helper’ı son sürüme güncelle ve tekrar dene.', login: 'Bu çalışmayı yüklemek için giriş yap.',
      noSet: 'Bu çalışmada vitrin türü için hazır bir dosya seti yok. ZIP’i indir ve elle yükle.',
      tooLarge: 'Bu çalışmanın bazı dosyaları Steam’in 5 MB sınırını aşıyor. Bunun yerine ZIP’i indir.',
      busy: 'Eklenti zaten başka bir seti yüklüyor. Bitmesini bekle.',
      failed: 'Yükleme başlatılamadı. Tekrar dene veya ZIP’i indir.', choose: 'Bu çalışmada birkaç set var. Hangisi?', main: 'Ana set' },
    fr: { button: 'Envoyer sur Steam automatiquement', hint: 'SteamShowcase Helper envoie les fichiers sur ton compte Steam dans un nouvel onglet.',
      checking: 'Recherche de l’extension…', preparing: 'Préparation des fichiers…', sending: 'Transmission des fichiers à l’extension…',
      started: 'C’est parti : l’extension a ouvert un onglet d’envoi et transmet les fichiers à Steam. À la fin, elle propose de les placer dans ta vitrine.',
      missing: 'Installe SteamShowcase Helper (gratuit) pour envoyer en un clic.', install: 'Installer l’extension', more: 'Ce qu’elle fait',
      old: 'Mets SteamShowcase Helper à jour vers la dernière version, puis réessaie.', login: 'Connecte-toi pour envoyer cette œuvre.',
      noSet: 'Cette œuvre n’a pas de jeu de fichiers prêt pour son type de vitrine. Télécharge le ZIP et envoie-le à la main.',
      tooLarge: 'Certains fichiers de cette œuvre dépassent la limite de 5 Mo de Steam. Télécharge plutôt le ZIP.',
      busy: 'L’extension envoie déjà un autre jeu. Attends qu’elle ait fini.',
      failed: 'Impossible de lancer l’envoi. Réessaie ou télécharge le ZIP.', choose: 'Cette œuvre a plusieurs jeux. Lequel ?', main: 'Jeu principal' },
    uk: { button: 'Завантажити в Steam автоматично', hint: 'SteamShowcase Helper завантажить файли у твій акаунт Steam у новій вкладці.',
      checking: 'Шукаємо розширення…', preparing: 'Готуємо файли…', sending: 'Передаємо файли розширенню…',
      started: 'Готово: розширення відкрило вкладку завантаження й надсилає файли в Steam. Наприкінці воно запропонує поставити їх у вітрину.',
      missing: 'Встанови SteamShowcase Helper (безкоштовно), щоб завантажувати в один клік.', install: 'Встановити розширення', more: 'Що воно вміє',
      old: 'Онови SteamShowcase Helper до останньої версії й спробуй ще раз.', login: 'Увійди в акаунт, щоб завантажити цю роботу.',
      noSet: 'У цій роботі немає готового набору файлів під її тип вітрини. Завантаж ZIP і додай вручну.',
      tooLarge: 'Частина файлів цієї роботи більша за ліміт Steam у 5 МБ. Завантаж ZIP.',
      busy: 'Розширення вже завантажує інший набір. Дочекайся, поки воно закінчить.',
      failed: 'Не вдалося почати завантаження. Спробуй ще раз або завантаж ZIP.', choose: 'У роботі кілька наборів. Який завантажити?', main: 'Основний набір' },
    es: { button: 'Subir a Steam automáticamente', hint: 'SteamShowcase Helper sube los archivos a tu cuenta de Steam en una pestaña nueva.',
      checking: 'Buscando la extensión…', preparing: 'Preparando los archivos…', sending: 'Pasando los archivos a la extensión…',
      started: 'Listo: la extensión abrió una pestaña de subida y está enviando los archivos a Steam. Al terminar, ofrece colocarlos en tu escaparate.',
      missing: 'Instala SteamShowcase Helper (gratis) para subir con un clic.', install: 'Instalar la extensión', more: 'Qué hace',
      old: 'Actualiza SteamShowcase Helper a la última versión e inténtalo de nuevo.', login: 'Inicia sesión para subir esta obra.',
      noSet: 'Esta obra no tiene un conjunto de archivos listo para su tipo de escaparate. Descarga el ZIP y súbelo a mano.',
      tooLarge: 'Algunos archivos de esta obra superan el límite de 5 MB de Steam. Descarga el ZIP.',
      busy: 'La extensión ya está subiendo otro conjunto. Espera a que termine.',
      failed: 'No se pudo iniciar la subida. Inténtalo de nuevo o descarga el ZIP.', choose: 'Esta obra tiene varios conjuntos. ¿Cuál?', main: 'Conjunto principal' },
    pt: { button: 'Enviar para a Steam automaticamente', hint: 'O SteamShowcase Helper envia os arquivos para a sua conta Steam em uma nova aba.',
      checking: 'Procurando a extensão…', preparing: 'Preparando os arquivos…', sending: 'Passando os arquivos para a extensão…',
      started: 'Pronto: a extensão abriu uma aba de envio e está mandando os arquivos para a Steam. No fim, ela oferece colocá-los na sua vitrine.',
      missing: 'Instale o SteamShowcase Helper (grátis) para enviar com um clique.', install: 'Instalar a extensão', more: 'O que ela faz',
      old: 'Atualize o SteamShowcase Helper para a versão mais recente e tente de novo.', login: 'Entre na conta para enviar esta obra.',
      noSet: 'Esta obra não tem um conjunto de arquivos pronto para o tipo de vitrine. Baixe o ZIP e envie manualmente.',
      tooLarge: 'Alguns arquivos desta obra passam do limite de 5 MB da Steam. Baixe o ZIP.',
      busy: 'A extensão já está enviando outro conjunto. Espere terminar.',
      failed: 'Não foi possível iniciar o envio. Tente de novo ou baixe o ZIP.', choose: 'Esta obra tem vários conjuntos. Qual?', main: 'Conjunto principal' }
  };

  function language() {
    var code = (window.SMLang && window.SMLang.get && window.SMLang.get()) || document.documentElement.lang || 'en';
    code = String(code).slice(0, 2).toLowerCase();
    return COPY[code] ? code : 'en';
  }
  function t(key) { return COPY[language()][key] || COPY.en[key]; }

  // ---------------------------------------------------------------- extension messages (same bridge as the tools)
  function bridgeMessage(message, wait) {
    return new Promise(function (resolve, reject) {
      var id = 'ssh-gallery-' + Date.now() + '-' + Math.random().toString(36).slice(2), done = false;
      function finish(ok, value) { if (done) return; done = true; clearTimeout(timer); window.removeEventListener('message', receive); (ok ? resolve : reject)(value); }
      function receive(event) {
        var data = event.data || {};
        if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && data.requestId === id) finish(true, data.reply || {});
      }
      window.addEventListener('message', receive);
      var timer = setTimeout(function () { finish(false, new Error('bridge-unavailable')); }, wait);
      window.postMessage({ source: 'SSH_SITE', type: 'REQUEST', requestId: id, payload: message }, location.origin);
    });
  }
  function directMessage(message) {
    return new Promise(function (resolve, reject) {
      if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) return reject(new Error('extension-missing'));
      try {
        chrome.runtime.sendMessage(EXTENSION_ID, message, function (reply) {
          if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message)); else resolve(reply || {});
        });
      } catch (error) { reject(error); }
    });
  }
  var bridgeAlive = false;
  function extensionMessage(message) {
    var ping = message.type === 'PING';
    return bridgeMessage(message, ping ? 1500 : 60000).then(function (reply) {
      if (ping && reply && reply.ok) bridgeAlive = true;
      return reply;
    }).catch(function (error) {
      // A bridge that answered PING is alive: never send the same upload a second time through another channel.
      if (bridgeAlive && !ping) throw error;
      return directMessage(message);
    });
  }
  function versionAtLeast(version, minimum) {
    var a = String(version || '0').split('.').map(Number), b = minimum.split('.').map(Number);
    for (var i = 0; i < 3; i++) { if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0); }
    return true;
  }
  function asDataUrl(blob, name) {
    var mime = /\.gif$/i.test(name) ? 'image/gif' : /\.jpe?g$/i.test(name) ? 'image/jpeg' : 'image/png';
    var typed = /^image\/(png|jpe?g|gif)$/i.test(blob.type || '') ? blob : blob.slice(0, blob.size, mime);
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result || '')); };
      reader.onerror = function () { reject(reader.error || new Error('read-failed')); };
      reader.readAsDataURL(typed);
    });
  }

  // ---------------------------------------------------------------- UI
  var download = document.getElementById('detailDownload');
  if (!download) return;
  var actions = download.parentNode;
  var button = document.createElement('button');
  button.type = 'button';
  button.id = 'detailSteam';
  button.className = 'community-secondary community-steam';
  button.hidden = true;
  var label = document.createElement('span');
  button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15V4m0 0-4 4m4-4 4 4M5 14v4a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/></svg>';
  button.appendChild(label);
  var note = document.createElement('div');
  note.className = 'community-steam__note';
  note.setAttribute('role', 'status');
  note.hidden = true;
  download.after(button);
  button.after(note);

  var current = 0, busy = false;
  function workId() {
    var match = /\/api\/gallery\/works\/(\d+)\/download/.exec(download.getAttribute('href') || '');
    return match ? Number(match[1]) : 0;
  }
  function sync() {
    label.textContent = t('button');
    button.title = t('hint');
    var id = download.hidden ? 0 : workId();
    button.hidden = !id;
    if (id !== current) { current = id; note.hidden = true; note.replaceChildren(); }
  }
  function say(text, links) {
    note.hidden = false;
    note.replaceChildren();
    var line = document.createElement('span');
    line.textContent = text;
    note.appendChild(line);
    (links || []).forEach(function (link) {
      var a = document.createElement('a');
      a.href = link[1];
      a.textContent = link[0];
      if (/^https:/.test(link[1])) { a.target = '_blank'; a.rel = 'noopener'; }
      note.appendChild(a);
    });
  }
  function choose(sets) {
    return new Promise(function (resolve) {
      say(t('choose'));
      var row = document.createElement('div');
      row.className = 'community-steam__sets';
      sets.forEach(function (set, index) {
        var chip = document.createElement('button');
        chip.type = 'button';
        chip.textContent = set.label || t('main');
        chip.addEventListener('click', function () { resolve(index); });
        row.appendChild(chip);
      });
      note.appendChild(row);
    });
  }
  function errorText(code) {
    return { login: t('login'), no_set: t('noSet'), too_large: t('tooLarge'), paid: t('noSet') }[code] || t('failed');
  }

  async function start() {
    var id = current;
    if (!id || busy) return;
    busy = true;
    button.disabled = true;
    try {
      say(t('checking'));
      var ping = await extensionMessage({ type: 'PING' }).catch(function () { return {}; });
      if (!ping || !ping.ok) { say(t('missing'), [[t('install'), STORE_URL], [t('more'), '/extension']]); return; }
      if (!versionAtLeast(ping.version, MIN_VERSION)) { say(t('old'), [[t('install'), STORE_URL]]); return; }
      say(t('preparing'));
      var response = await fetch('/api/gallery/works/' + id + '/steam', { credentials: 'include', cache: 'no-store' });
      var data = await response.json().catch(function () { return {}; });
      if (!response.ok || !data.ok || !data.sets || !data.sets.length) { say(errorText(data.code || (response.status === 401 ? 'login' : ''))); return; }
      var set = data.sets[data.sets.length > 1 ? await choose(data.sets) : 0];
      if (current !== id) return;
      say(t('preparing'));
      var items = [];
      for (var i = 0; i < set.files.length; i++) {
        var file = set.files[i];
        var url = new URL(file.url, location.origin);
        if (url.origin !== location.origin || url.pathname.indexOf('/api/gallery/works/' + id + '/steam/') !== 0) throw new Error('bad-url');
        var part = await fetch(url.href, { credentials: 'include', cache: 'no-store' });
        if (!part.ok) throw new Error('part-' + part.status);
        var blob = await part.blob();
        if (!blob.size || blob.size > 5 * 1024 * 1024) throw new Error('part-size');
        items.push({ fileName: file.name, fileSize: blob.size, fileBase64: await asDataUrl(blob, file.name) });
      }
      say(t('sending'));
      var reply = await extensionMessage({ type: 'START_AUTO_UPLOAD', mode: data.mode, lang: language() === 'ru' ? 'ru' : 'en', items: items });
      if (!reply || !reply.ok) {
        say(/already running/i.test(String(reply && reply.error || '')) ? t('busy') : t('failed'));
        return;
      }
      say(t('started'));
    } catch (_) {
      say(t('failed'));
    } finally {
      busy = false;
      button.disabled = false;
    }
  }

  button.addEventListener('click', start);
  new MutationObserver(sync).observe(download, { attributes: true, attributeFilter: ['href', 'hidden'] });
  window.addEventListener('sm:langchange', sync);
  sync();
})();
