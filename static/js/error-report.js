/* Error popup for every page with the site shell (owner, 2026-10-05).

   Watches the site's own /api requests (fetch + XHR) and its own scripts:
   - a job status that ended with error_kind "user" (the file or settings: too big for 5 MB,
     broken file, unsupported format...) -> a short explanation and what to do, no report;
   - error_kind "server", an unexplained 5xx or a crash in our scripts -> "Something went wrong"
     with "Tell the developer": contact (e-mail or Telegram, optional when signed in), a comment,
     and the technical details attached automatically. It goes to POST /api/support/tickets,
     so it lands in the admin "Обращения" and in the owner bot like any support request.
   Errors a tool already explains itself (Steam profile import, rate limits, sign-in) are left
   to that tool. Server side: job_diagnostics.public_error() fills error_kind / error_code. */
(function () {
  'use strict';
  if (window.SMErrorReport) return;

  var COPY = {
    en: { serverTitle: 'Something went wrong on our side', serverText: 'This is not your fault. You can try again; if it repeats, tell us and we will fix it.', pageTitle: 'Something on this page broke', pageText: 'A part of the page stopped working. Reloading the page usually helps; if it does not, tell us.', userTitle: 'The file could not be prepared', fix: 'What to do', report: 'Tell the developer', send: 'Send', close: 'Close', contact: 'E-mail or Telegram (@username)', contactHintUser: 'Optional: we will answer to your account e-mail.', contactHintGuest: 'So we can answer you.', comment: 'What were you doing? (optional)', details: 'Technical details', sent: 'Thank you! The report has been sent; the answer will come to you.', failed: 'Could not send. Write to support instead.', limit: 'Too many reports today. Please try again tomorrow.', needContact: 'Enter an e-mail or a Telegram username.',
      steam_limit: ['The animation does not fit Steam’s 5 MB limit even at the lowest quality.', 'Take a shorter fragment (4–6 s), a lower FPS or a calmer part of the video.'], upload_limit: ['The file is larger than the upload limit.', 'Compress or trim the video, or make the picture smaller.'], format: ['This file format is not supported.', 'Save it as PNG, JPG, GIF, MP4 or WebM.'], animated_still: ['An animated picture came where a still one is expected.', 'Convert the animation to GIF or MP4.'], broken_file: ['The file could not be read: it is damaged or not what its extension says.', 'Re-save it in an editor or converter and upload it again.'], too_many_pixels: ['The picture is too large in pixels.', 'Make it 4K or smaller.'], no_frames: ['There were no frames in the selected fragment.', 'Move the start earlier or choose another fragment.'], duration: ['The animation length is outside the allowed range.', 'Choose a fragment of a suitable length.'], generic: ['The file could not be processed.', 'Check the file and the settings and try again.'] },
    ru: { serverTitle: 'Что-то пошло не так на нашей стороне', serverText: 'Это не твоя ошибка. Попробуй ещё раз; если повторится, сообщи нам, и мы починим.', pageTitle: 'На странице что-то сломалось', pageText: 'Часть страницы перестала работать. Обычно помогает обновить страницу; если нет, сообщи нам.', userTitle: 'Файл не получилось подготовить', fix: 'Что сделать', report: 'Сообщить разработчику', send: 'Отправить', close: 'Закрыть', contact: 'Почта или Telegram (@username)', contactHintUser: 'Необязательно: ответим на почту аккаунта.', contactHintGuest: 'Чтобы мы могли тебе ответить.', comment: 'Что ты делал? (необязательно)', details: 'Технические подробности', sent: 'Спасибо! Отчёт отправлен, ответ придёт тебе.', failed: 'Не удалось отправить. Напиши в поддержку.', limit: 'Сегодня отправлено слишком много отчётов. Попробуй завтра.', needContact: 'Укажи почту или Telegram.',
      steam_limit: ['Анимация не влезает в лимит Steam 5 МБ даже на минимальном качестве.', 'Возьми фрагмент покороче (4–6 с), меньший FPS или более спокойную часть видео.'], upload_limit: ['Файл больше допустимого размера загрузки.', 'Сожми или обрежь видео, уменьши картинку.'], format: ['Этот формат файла не поддерживается.', 'Сохрани как PNG, JPG, GIF, MP4 или WebM.'], animated_still: ['Пришла анимированная картинка там, где нужна обычная.', 'Сконвертируй анимацию в GIF или MP4.'], broken_file: ['Файл не читается: он повреждён или это не тот формат, что в расширении.', 'Пересохрани его в редакторе или конвертере и загрузи снова.'], too_many_pixels: ['У картинки слишком большое разрешение.', 'Уменьши её до 4K или меньше.'], no_frames: ['В выбранном отрезке нет кадров.', 'Поставь начало раньше или выбери другой фрагмент.'], duration: ['Длина анимации вне допустимого диапазона.', 'Выбери фрагмент подходящей длины.'], generic: ['Файл не получилось обработать.', 'Проверь файл и настройки и попробуй ещё раз.'] },
    de: { serverTitle: 'Bei uns ist etwas schiefgelaufen', serverText: 'Das ist nicht dein Fehler. Versuch es noch einmal; wenn es wieder passiert, sag uns Bescheid.', pageTitle: 'Auf dieser Seite ist etwas kaputtgegangen', pageText: 'Ein Teil der Seite funktioniert nicht mehr. Neu laden hilft meistens; sonst sag uns Bescheid.', userTitle: 'Die Datei konnte nicht vorbereitet werden', fix: 'Was tun', report: 'Dem Entwickler melden', send: 'Senden', close: 'Schließen', contact: 'E-Mail oder Telegram (@username)', contactHintUser: 'Optional: Wir antworten an die E-Mail deines Kontos.', contactHintGuest: 'Damit wir dir antworten können.', comment: 'Was hast du gemacht? (optional)', details: 'Technische Details', sent: 'Danke! Der Bericht ist gesendet, die Antwort kommt zu dir.', failed: 'Senden fehlgeschlagen. Schreib bitte dem Support.', limit: 'Heute wurden zu viele Berichte gesendet. Versuch es morgen.', needContact: 'Gib eine E-Mail oder einen Telegram-Namen an.',
      steam_limit: ['Die Animation passt selbst in niedrigster Qualität nicht in Steams 5-MB-Grenze.', 'Nimm einen kürzeren Ausschnitt (4–6 s), weniger FPS oder einen ruhigeren Teil.'], upload_limit: ['Die Datei ist größer als das Upload-Limit.', 'Komprimiere oder kürze das Video, verkleinere das Bild.'], format: ['Dieses Dateiformat wird nicht unterstützt.', 'Speichere als PNG, JPG, GIF, MP4 oder WebM.'], animated_still: ['Ein animiertes Bild kam dort an, wo ein Standbild erwartet wird.', 'Wandle die Animation in GIF oder MP4 um.'], broken_file: ['Die Datei ist nicht lesbar: beschädigt oder nicht das, was die Endung sagt.', 'Speichere sie neu und lade sie erneut hoch.'], too_many_pixels: ['Das Bild hat zu viele Pixel.', 'Verkleinere es auf 4K oder weniger.'], no_frames: ['Im gewählten Ausschnitt gibt es keine Bilder.', 'Setze den Start früher oder wähle einen anderen Ausschnitt.'], duration: ['Die Länge der Animation liegt außerhalb des erlaubten Bereichs.', 'Wähle einen passend langen Ausschnitt.'], generic: ['Die Datei konnte nicht verarbeitet werden.', 'Prüfe Datei und Einstellungen und versuch es erneut.'] },
    tr: { serverTitle: 'Bizim tarafta bir şeyler ters gitti', serverText: 'Senin hatan değil. Tekrar dene; yine olursa bize bildir, düzeltelim.', pageTitle: 'Bu sayfada bir şey bozuldu', pageText: 'Sayfanın bir kısmı çalışmayı bıraktı. Genellikle sayfayı yenilemek yardımcı olur; olmazsa bize bildir.', userTitle: 'Dosya hazırlanamadı', fix: 'Ne yapmalı', report: 'Geliştiriciye bildir', send: 'Gönder', close: 'Kapat', contact: 'E-posta veya Telegram (@kullanıcıadı)', contactHintUser: 'İsteğe bağlı: hesabının e-postasına yanıt veririz.', contactHintGuest: 'Sana yanıt verebilmemiz için.', comment: 'Ne yapıyordun? (isteğe bağlı)', details: 'Teknik ayrıntılar', sent: 'Teşekkürler! Rapor gönderildi, yanıt sana gelecek.', failed: 'Gönderilemedi. Lütfen desteğe yaz.', limit: 'Bugün çok fazla rapor gönderildi. Yarın tekrar dene.', needContact: 'Bir e-posta veya Telegram kullanıcı adı gir.',
      steam_limit: ['Animasyon en düşük kalitede bile Steam’in 5 MB sınırına sığmıyor.', 'Daha kısa bir bölüm (4–6 sn), daha düşük FPS ya da daha sakin bir kısım seç.'], upload_limit: ['Dosya yükleme sınırından büyük.', 'Videoyu sıkıştır veya kırp, resmi küçült.'], format: ['Bu dosya biçimi desteklenmiyor.', 'PNG, JPG, GIF, MP4 veya WebM olarak kaydet.'], animated_still: ['Durağan resim beklenen yere animasyonlu bir resim geldi.', 'Animasyonu GIF veya MP4’e dönüştür.'], broken_file: ['Dosya okunamadı: bozuk ya da uzantısının söylediği biçimde değil.', 'Bir düzenleyicide yeniden kaydedip tekrar yükle.'], too_many_pixels: ['Resmin piksel sayısı çok büyük.', '4K veya daha küçüğe indir.'], no_frames: ['Seçilen bölümde kare yok.', 'Başlangıcı öne al ya da başka bir bölüm seç.'], duration: ['Animasyon uzunluğu izin verilen aralığın dışında.', 'Uygun uzunlukta bir bölüm seç.'], generic: ['Dosya işlenemedi.', 'Dosyayı ve ayarları kontrol edip tekrar dene.'] },
    fr: { serverTitle: 'Un problème est survenu de notre côté', serverText: 'Ce n’est pas votre faute. Réessayez ; si cela se répète, signalez-le et nous corrigerons.', pageTitle: 'Quelque chose s’est cassé sur cette page', pageText: 'Une partie de la page ne fonctionne plus. Recharger la page aide souvent ; sinon, signalez-le.', userTitle: 'Le fichier n’a pas pu être préparé', fix: 'Que faire', report: 'Signaler au développeur', send: 'Envoyer', close: 'Fermer', contact: 'E-mail ou Telegram (@pseudo)', contactHintUser: 'Facultatif : nous répondrons à l’e-mail du compte.', contactHintGuest: 'Pour que nous puissions vous répondre.', comment: 'Que faisiez-vous ? (facultatif)', details: 'Détails techniques', sent: 'Merci ! Le rapport est envoyé, la réponse vous parviendra.', failed: 'Envoi impossible. Écrivez au support.', limit: 'Trop de rapports aujourd’hui. Réessayez demain.', needContact: 'Indiquez un e-mail ou un pseudo Telegram.',
      steam_limit: ['L’animation ne tient pas dans la limite de 5 Mo de Steam, même en qualité minimale.', 'Prenez un extrait plus court (4–6 s), moins d’images/s ou un passage plus calme.'], upload_limit: ['Le fichier dépasse la taille d’envoi autorisée.', 'Compressez ou coupez la vidéo, réduisez l’image.'], format: ['Ce format de fichier n’est pas pris en charge.', 'Enregistrez-le en PNG, JPG, GIF, MP4 ou WebM.'], animated_still: ['Une image animée est arrivée là où une image fixe est attendue.', 'Convertissez l’animation en GIF ou MP4.'], broken_file: ['Le fichier est illisible : endommagé ou d’un autre format que son extension.', 'Réenregistrez-le dans un éditeur et envoyez-le à nouveau.'], too_many_pixels: ['L’image a trop de pixels.', 'Réduisez-la à 4K ou moins.'], no_frames: ['Aucune image dans l’extrait choisi.', 'Avancez le début ou choisissez un autre extrait.'], duration: ['La durée de l’animation est hors de la plage autorisée.', 'Choisissez un extrait de durée adaptée.'], generic: ['Le fichier n’a pas pu être traité.', 'Vérifiez le fichier et les réglages, puis réessayez.'] },
    uk: { serverTitle: 'Щось пішло не так на нашому боці', serverText: 'Це не твоя помилка. Спробуй ще раз; якщо повториться, повідом нам, і ми полагодимо.', pageTitle: 'На сторінці щось зламалося', pageText: 'Частина сторінки перестала працювати. Зазвичай допомагає оновити сторінку; якщо ні, повідом нам.', userTitle: 'Файл не вдалося підготувати', fix: 'Що зробити', report: 'Повідомити розробнику', send: 'Надіслати', close: 'Закрити', contact: 'Пошта або Telegram (@username)', contactHintUser: 'Необов’язково: відповімо на пошту акаунта.', contactHintGuest: 'Щоб ми могли тобі відповісти.', comment: 'Що ти робив? (необов’язково)', details: 'Технічні подробиці', sent: 'Дякуємо! Звіт надіслано, відповідь прийде тобі.', failed: 'Не вдалося надіслати. Напиши в підтримку.', limit: 'Сьогодні надіслано забагато звітів. Спробуй завтра.', needContact: 'Вкажи пошту або Telegram.',
      steam_limit: ['Анімація не влазить у ліміт Steam 5 МБ навіть на мінімальній якості.', 'Візьми коротший фрагмент (4–6 с), менший FPS або спокійнішу частину відео.'], upload_limit: ['Файл більший за дозволений розмір завантаження.', 'Стисни або обріж відео, зменш картинку.'], format: ['Цей формат файлу не підтримується.', 'Збережи як PNG, JPG, GIF, MP4 або WebM.'], animated_still: ['Прийшла анімована картинка там, де потрібна звичайна.', 'Сконвертуй анімацію в GIF або MP4.'], broken_file: ['Файл не читається: пошкоджений або не того формату, що в розширенні.', 'Перезбережи його в редакторі й завантаж знову.'], too_many_pixels: ['У картинки завелика роздільність.', 'Зменш її до 4K або менше.'], no_frames: ['У вибраному відрізку немає кадрів.', 'Постав початок раніше або вибери інший фрагмент.'], duration: ['Довжина анімації поза дозволеним діапазоном.', 'Вибери фрагмент відповідної довжини.'], generic: ['Файл не вдалося обробити.', 'Перевір файл і налаштування та спробуй ще раз.'] },
    es: { serverTitle: 'Algo salió mal de nuestro lado', serverText: 'No es culpa tuya. Vuelve a intentarlo; si se repite, avísanos y lo arreglaremos.', pageTitle: 'Algo se rompió en esta página', pageText: 'Una parte de la página dejó de funcionar. Recargarla suele ayudar; si no, avísanos.', userTitle: 'No se pudo preparar el archivo', fix: 'Qué hacer', report: 'Avisar al desarrollador', send: 'Enviar', close: 'Cerrar', contact: 'Correo o Telegram (@usuario)', contactHintUser: 'Opcional: responderemos al correo de tu cuenta.', contactHintGuest: 'Para poder responderte.', comment: '¿Qué estabas haciendo? (opcional)', details: 'Detalles técnicos', sent: '¡Gracias! El informe se envió, la respuesta te llegará.', failed: 'No se pudo enviar. Escribe al soporte.', limit: 'Hoy se enviaron demasiados informes. Inténtalo mañana.', needContact: 'Indica un correo o un usuario de Telegram.',
      steam_limit: ['La animación no cabe en el límite de 5 MB de Steam ni con la calidad mínima.', 'Elige un fragmento más corto (4–6 s), menos FPS o una parte más tranquila.'], upload_limit: ['El archivo supera el límite de subida.', 'Comprime o recorta el vídeo, reduce la imagen.'], format: ['Este formato de archivo no es compatible.', 'Guárdalo como PNG, JPG, GIF, MP4 o WebM.'], animated_still: ['Llegó una imagen animada donde se espera una fija.', 'Convierte la animación a GIF o MP4.'], broken_file: ['El archivo no se puede leer: está dañado o no es el formato que indica su extensión.', 'Vuelve a guardarlo en un editor y súbelo otra vez.'], too_many_pixels: ['La imagen tiene demasiados píxeles.', 'Redúcela a 4K o menos.'], no_frames: ['El fragmento elegido no tiene fotogramas.', 'Pon el inicio antes o elige otro fragmento.'], duration: ['La duración de la animación está fuera del rango permitido.', 'Elige un fragmento de duración adecuada.'], generic: ['No se pudo procesar el archivo.', 'Revisa el archivo y los ajustes y vuelve a intentarlo.'] },
    pt: { serverTitle: 'Algo deu errado do nosso lado', serverText: 'Não é culpa sua. Tente de novo; se repetir, avise-nos e vamos corrigir.', pageTitle: 'Algo quebrou nesta página', pageText: 'Uma parte da página parou de funcionar. Recarregar costuma ajudar; se não, avise-nos.', userTitle: 'Não foi possível preparar o arquivo', fix: 'O que fazer', report: 'Avisar o desenvolvedor', send: 'Enviar', close: 'Fechar', contact: 'E-mail ou Telegram (@usuario)', contactHintUser: 'Opcional: responderemos no e-mail da conta.', contactHintGuest: 'Para podermos responder.', comment: 'O que você estava fazendo? (opcional)', details: 'Detalhes técnicos', sent: 'Obrigado! O relatório foi enviado, a resposta chegará a você.', failed: 'Não foi possível enviar. Escreva ao suporte.', limit: 'Relatórios demais hoje. Tente amanhã.', needContact: 'Informe um e-mail ou usuário do Telegram.',
      steam_limit: ['A animação não cabe no limite de 5 MB da Steam nem na qualidade mínima.', 'Escolha um trecho mais curto (4–6 s), menos FPS ou uma parte mais calma.'], upload_limit: ['O arquivo é maior que o limite de envio.', 'Comprima ou corte o vídeo, diminua a imagem.'], format: ['Este formato de arquivo não é suportado.', 'Salve como PNG, JPG, GIF, MP4 ou WebM.'], animated_still: ['Chegou uma imagem animada onde se espera uma imagem parada.', 'Converta a animação para GIF ou MP4.'], broken_file: ['O arquivo não pode ser lido: está danificado ou não é o formato da extensão.', 'Salve de novo em um editor e envie outra vez.'], too_many_pixels: ['A imagem tem pixels demais.', 'Reduza para 4K ou menos.'], no_frames: ['Não há quadros no trecho escolhido.', 'Coloque o início antes ou escolha outro trecho.'], duration: ['A duração da animação está fora do intervalo permitido.', 'Escolha um trecho de duração adequada.'], generic: ['Não foi possível processar o arquivo.', 'Verifique o arquivo e as configurações e tente de novo.'] }
  };
  /* Requests whose failures are background noise or already explained by their tool. */
  var QUIET = /^\/api\/(notifications|presence|analytics|news\/seen|health|ready|quota|auth\/me|bootstrap|support|announcements|profile\/steam-import|profile\/extension-import|gif-optimizer|events|jobs\/stream)/;
  var TOOL_BY_PATH = { process: 'process', 'workshop-studio': 'workshop_studio', compose: 'compose', loop: 'loop', upscale: 'upscale', builder: 'builder' };

  function language() { var l = window.SMLang && SMLang.get ? SMLang.get() : (document.documentElement.lang || 'en'); return COPY[l] ? l : 'en'; }
  function t(key) { var c = COPY[language()] || COPY.en; return c[key] != null ? c[key] : COPY.en[key]; }
  function node(tag, cls, text) { var el = document.createElement(tag); if (cls) el.className = cls; if (text != null) el.textContent = text; return el; }
  function apiPath(url) {
    try { var u = new URL(url, location.href); return u.origin === location.origin && u.pathname.indexOf('/api/') === 0 ? u.pathname : ''; } catch (e) { return ''; }
  }
  function toolOf(path) {
    var m = /^\/api\/([a-z-]+)/.exec(path || ''); if (m && TOOL_BY_PATH[m[1]]) return TOOL_BY_PATH[m[1]];
    var active = document.querySelector('#nav .active[data-tab]'); return active ? active.dataset.tab : location.pathname.replace(/^\/[a-z]{2}(?=\/|$)/, '') || '/';
  }

  var shownJobs = {}, lastShown = 0, seenSignatures = {}, card = null;
  function show(report) {
    var now = Date.now();
    if (card || now - lastShown < 15000) return;
    var signature = [report.kind, report.code, report.path].join('|');
    if (seenSignatures[signature]) return;
    seenSignatures[signature] = 1; lastShown = now;
    render(report);
  }

  function render(report) {
    injectStyle();
    var user = report.kind === 'user', info = user ? (t(report.code) || t('generic')) : null;
    card = node('aside', 'sm-err sm-err--' + (user ? 'user' : 'server'));
    card.setAttribute('role', 'alert');
    var head = node('div', 'sm-err__head'), icon = node('span', 'sm-err__icon', user ? 'i' : '!');
    var title = node('b', 'sm-err__title', user ? t('userTitle') : (report.kind === 'page' ? t('pageTitle') : t('serverTitle')));
    var closeBtn = node('button', 'sm-err__close', '×'); closeBtn.type = 'button'; closeBtn.setAttribute('aria-label', t('close'));
    head.append(icon, title, closeBtn); card.append(head);
    card.append(node('p', 'sm-err__text', user ? info[0] : (report.kind === 'page' ? t('pageText') : t('serverText'))));
    if (user) {
      var fix = node('p', 'sm-err__fix'); fix.append(node('b', null, t('fix') + ': '), document.createTextNode(info[1])); card.append(fix);
    } else {
      var details = node('details', 'sm-err__details'); details.append(node('summary', null, t('details')));
      details.append(node('pre', null, technical(report))); card.append(details);
      var actions = node('div', 'sm-err__actions'), reportBtn = node('button', 'sm-err__btn', t('report')); reportBtn.type = 'button';
      actions.append(reportBtn); card.append(actions);
      reportBtn.addEventListener('click', function () { actions.remove(); openForm(report); });
    }
    closeBtn.addEventListener('click', dismiss);
    document.body.append(card);
    if (user) setTimeout(function () { if (card && !card.querySelector('form')) dismiss(); }, 20000);
  }
  function dismiss() { if (card) { card.remove(); card = null; } }
  function technical(report) {
    return ['tool: ' + report.tool, report.code ? 'code: ' + report.code : '', report.status ? 'http: ' + report.status : '',
      report.requestId ? 'request: ' + report.requestId : '', report.jobId ? 'job: ' + report.jobId : '',
      report.error ? 'error: ' + report.error : '', 'page: ' + location.pathname].filter(Boolean).join('\n');
  }
  function openForm(report) {
    var form = node('form', 'sm-err__form');
    var contact = node('input'); contact.type = 'text'; contact.maxLength = 254; contact.placeholder = t('contact'); contact.autocomplete = 'email';
    var hint = node('small', 'sm-err__hint', t('contactHintGuest'));
    var comment = node('textarea'); comment.rows = 3; comment.maxLength = 1500; comment.placeholder = t('comment');
    var send = node('button', 'sm-err__btn', t('send')); send.type = 'submit';
    var status = node('p', 'sm-err__status'); status.setAttribute('role', 'status');
    form.append(contact, hint, comment, send, status); card.append(form);
    var signedIn = false;
    fetch('/api/auth/me', { credentials: 'same-origin', cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (me) {
      signedIn = !!(me && (me.logged_in || me.email)); if (signedIn) hint.textContent = t('contactHintUser');
    }).catch(function () {});
    contact.focus();
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var value = contact.value.trim();
      if (!value && !signedIn) { status.textContent = t('needContact'); contact.focus(); return; }
      send.disabled = true;
      var message = '[Отчёт об ошибке] ' + report.tool + ': ' + (report.code || report.error || ('HTTP ' + report.status)) +
        (comment.value.trim() ? '\n\n' + comment.value.trim() : '\n\n(без комментария)');
      fetch('/api/support/tickets', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contact: value, message: message.slice(0, 2000), page: location.pathname,
          context: { kind: 'error_report', tool: report.tool, error: String(report.error || '').slice(0, 300), error_code: report.code || '',
            request_id: report.requestId || '', job_id: report.jobId || '', language: language(),
            viewport: innerWidth + 'x' + innerHeight, browser: navigator.userAgent.slice(0, 120) } })
      }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (body) { return { ok: r.ok, status: r.status, body: body }; }); })
        .then(function (res) {
          if (res.ok) { form.replaceWith(node('p', 'sm-err__done', t('sent'))); setTimeout(dismiss, 6000); return; }
          send.disabled = false;
          status.textContent = res.status === 429 ? t('limit') : (res.body && res.body.code === 'contact' ? t('needContact') : t('failed'));
        }).catch(function () { send.disabled = false; status.textContent = t('failed'); });
    });
  }

  /* --------------------------------------------------------------- watching */
  function inspect(path, status, body) {
    if (!path || QUIET.test(path)) return;
    var jobMatch = /\/status\/([^/?#]+)/.exec(path), jobId = jobMatch ? jobMatch[1] : '';
    if (body && body.status === 'error' && body.error_kind && jobId) {
      if (shownJobs[jobId]) return; shownJobs[jobId] = 1;
      show({ kind: body.error_kind === 'user' ? 'user' : 'server', code: body.error_code || '', error: body.error || '', jobId: jobId, path: path, tool: toolOf(path) });
      return;
    }
    if (status >= 500) {
      // 503 with a code (busy, maintenance, youtube_blocked...) is a known state the tool explains.
      if (status === 503 && body && (body.code || body.reason)) return;
      show({ kind: 'server', code: body && body.code || '', error: body && body.msg || '', status: status,
        requestId: body && body.request_id || '', path: path, tool: toolOf(path) });
    }
  }
  var nativeFetch = window.fetch;
  if (nativeFetch) {
    window.fetch = function (input, init) {
      var promise = nativeFetch.apply(this, arguments);
      var path = apiPath(typeof input === 'string' ? input : (input && input.url) || '');
      if (!path || QUIET.test(path)) return promise;
      promise.then(function (response) {
        var type = response.headers.get('content-type') || '';
        if (response.status >= 500 || (/\/status\//.test(path) && type.indexOf('json') >= 0)) {
          response.clone().json().then(function (body) { inspect(path, response.status, body); }, function () { inspect(path, response.status, null); });
        }
      }, function () {});
      return promise;
    };
  }
  var open = XMLHttpRequest.prototype.open, sendXhr = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (method, url) { this.__smPath = apiPath(url); return open.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    var xhr = this;
    if (xhr.__smPath && !QUIET.test(xhr.__smPath)) {
      xhr.addEventListener('loadend', function () {
        if (!xhr.status || (xhr.status < 500 && !/\/status\//.test(xhr.__smPath))) return;
        var body = null;
        try { body = xhr.responseType === 'json' ? xhr.response : JSON.parse(xhr.responseText || 'null'); } catch (e) { body = null; }
        inspect(xhr.__smPath, xhr.status, body);
      });
    }
    return sendXhr.apply(this, arguments);
  };
  /* Crashes in our own scripts (not extensions, not cross-origin noise). */
  function ownScript(file) { return !!file && file.indexOf(location.origin + '/static/') === 0; }
  var IGNORE_ERROR = /ResizeObserver loop|Script error|AbortError|The play\(\) request|NotAllowedError|Load failed|NetworkError|Failed to fetch/i;
  window.addEventListener('error', function (event) {
    if (!event || !ownScript(event.filename) || IGNORE_ERROR.test(String(event.message || ''))) return;
    show({ kind: 'page', code: 'script', error: String(event.message || '').slice(0, 200) + ' @ ' + String(event.filename || '').split('/').pop() + ':' + event.lineno,
      path: event.filename, tool: toolOf('') });
  });
  window.addEventListener('unhandledrejection', function (event) {
    var reason = event && event.reason, stack = reason && reason.stack ? String(reason.stack) : '';
    if (!stack || stack.indexOf(location.origin + '/static/') < 0 || IGNORE_ERROR.test(String(reason.message || reason))) return;
    show({ kind: 'page', code: 'promise', error: String(reason.message || reason).slice(0, 200), path: 'promise', tool: toolOf('') });
  });

  var styled = false;
  function injectStyle() {
    if (styled) return; styled = true;
    var css = '.sm-err{position:fixed;left:16px;bottom:16px;z-index:2147482000;width:min(380px,calc(100vw - 32px));max-height:calc(100dvh - 32px);overflow:auto;padding:14px 16px;border:1px solid rgba(110,170,255,.28);border-radius:14px;background:linear-gradient(165deg,#0e1a3c,#050a1c);color:#e9f3ff;font:13px/1.45 Montserrat,system-ui,sans-serif;box-shadow:0 20px 60px rgba(0,0,0,.55)}' +
      '.sm-err::before{content:"";position:absolute;inset:0 0 auto;height:2px;border-radius:14px 14px 0 0;background:linear-gradient(90deg,#ffb347,#8a7dff)}.sm-err--user::before{background:linear-gradient(90deg,#1fc9f1,#8a7dff)}' +
      '.sm-err__head{display:flex;align-items:center;gap:10px}.sm-err__icon{flex:none;display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:rgba(255,179,71,.18);color:#ffc77a;font-weight:800}.sm-err--user .sm-err__icon{background:rgba(31,201,241,.18);color:#6fe3ff}' +
      '.sm-err__title{flex:1;font-size:14px}.sm-err__close{flex:none;width:28px;height:28px;border:1px solid rgba(110,170,255,.26);border-radius:8px;background:rgba(3,8,24,.7);color:#e9f3ff;font-size:17px;cursor:pointer}' +
      '.sm-err__text,.sm-err__fix,.sm-err__done{margin:8px 0 0;color:rgba(214,229,250,.8)}.sm-err__fix b{color:#e9f3ff}.sm-err__details{margin-top:8px;color:rgba(200,214,238,.6)}.sm-err__details summary{cursor:pointer;font-size:12px}' +
      '.sm-err__details pre{margin:6px 0 0;padding:8px;border-radius:8px;background:rgba(3,8,24,.7);white-space:pre-wrap;word-break:break-word;font:11px/1.4 Consolas,monospace}' +
      '.sm-err__actions{margin-top:10px}.sm-err__btn{padding:8px 14px;border:0;border-radius:9px;background:linear-gradient(135deg,#6fe3ff,#1fc9f1);color:#021018;font:700 13px Montserrat,system-ui,sans-serif;cursor:pointer}.sm-err__btn:disabled{opacity:.6}' +
      '.sm-err__form{display:grid;gap:6px;margin-top:10px}.sm-err__form input,.sm-err__form textarea{width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid rgba(110,170,255,.3);border-radius:8px;background:rgba(3,8,24,.75);color:#e9f3ff;font:13px Montserrat,system-ui,sans-serif}' +
      '.sm-err__hint{color:rgba(200,214,238,.55);font-size:11.5px}.sm-err__status{margin:0;color:#ffc77a;font-size:12px}.sm-err__done{color:#7ee2a8}' +
      'body.studio-support-open .sm-err{display:none}';
    var style = node('style'); style.textContent = css; document.head.append(style);
  }

  window.SMErrorReport = { show: show, inspect: inspect, dismiss: dismiss };
})();
