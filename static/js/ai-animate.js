/* AI animation tab (#tab-aianim, beta for Pro; server: smweb/ai_animate.py + routers/ai_animate.py).
   Layout: a hero with the two looks, then settings in four numbered steps (picture, motion style, what moves,
   background) beside a sticky result panel (empty -> progress by stage with elapsed time and Cancel ->
   the GIF with Download GIF / MP4, Cut for Steam (hands the MP4 to Process) and Another take).
   Locks: guest -> sign in, free -> Pro (beta), no FAL_KEY on the server -> unavailable.
   The running job id survives a reload (sessionStorage). Copy: the keyed COPY dictionary below, 8 languages (scripts/check_i18n.js).
   Debug hook: window.SMAiAnimate. */
(function () {
  'use strict';
  var COPY = {
    en: { eyebrow: 'Beta · Pro', heroTitle: 'Bring your art to life', heroLead: 'AI gently animates a still picture: hair, breathing, a glance. The background stays your own and the loop is seamless, ready for a Steam showcase.',
      fact1: '1–3 minutes', fact2: 'Your original background', fact3: 'Seamless loop', fact4: 'GIF up to 5 MB + MP4',
      s1: 'Picture', s1Hint: 'One character works best. PNG, JPG, WebP, GIF (first frame), up to 40 MB.', drop: 'Drop a picture here', dropOr: 'Choose a file', sample: 'Try with an example', replace: 'Replace',
      s2: 'Motion style', calm: 'Calm', calmHint: 'Soft idle motion: the face stays the same, the hair sways a little.', lively: 'Lively', livelyHint: 'More motion: the hair flows, the character moves in place. The face may change a little.',
      s3: 'What should move', s3Hint: 'Optional: pick hints or describe it in your own words.', m_hair: 'Hair', m_breath: 'Breathing', m_blink: 'Blinking', m_gaze: 'Glance', m_wind: 'Wind', m_glow: 'Light',
      wishPh: 'Your wish, e.g. “the ribbon flutters, the stars twinkle”', s4: 'Background',
      keepBg: 'Keep the original background', keepBgHint: 'Only what really moves comes from the animation; the rest is your picture, pixel for pixel.',
      go: 'Bring to life', left: 'Left: {n} of {max}', unlimited: 'No daily limit for your account', refund: 'If the AI refuses or something fails, the try comes back.',
      resultTitle: 'Result', resultEmpty: 'Your animation will appear here.', yourPicture: 'Your picture',
      st_queued: 'Waiting in the queue…', st_prepare: 'Preparing the picture…', st_wish: 'Reading your wish…', st_sending: 'Sending to the AI…', st_queued_ai: 'Waiting for the AI service…', st_animating: 'The AI is animating, usually 1–3 minutes…', st_assembling: 'Building a seamless loop…', st_saving: 'Saving…', st_cancelling: 'Cancelling…',
      elapsed: '{s} s', cancel: 'Cancel', cancelled: 'Cancelled. The try came back.',
      dlGif: 'Download GIF', dlMp4: 'Download MP4', toProcess: 'Cut for Steam', again: 'Another take', gifInfo: 'GIF {w}×{h} · {fps} fps · {mb} MB', saved: 'Also kept in My results for 30 days.', handing: 'Opening Process…',
      err_ai_moderated: 'The AI refused this picture under its content rules (usually nudity). Your try came back.', err_ai_site_busy: 'The beta’s daily budget for the whole site is used up. Try again tomorrow.',
      err_unavailable: 'AI animation is temporarily unavailable.', err_bad_image: 'Could not read this picture. Try PNG or JPG.', err_too_small: 'The picture is too small: at least 128 px on each side.', err_too_large: 'The picture is too large: over 40 megapixels.', err_too_big: 'The file is larger than 40 MB.', err_busy: 'Too many active jobs. Wait for one to finish.', err_generic: 'Something went wrong. Your try came back, please try again.', pickFirst: 'Add a picture first.',
      lockLogin: 'Sign in to use AI animation', lockLoginBtn: 'Sign in', lockPro: 'AI animation is in beta and comes with Pro', lockProText: 'Every animation runs on a paid AI model, so during the beta it is part of Pro.', lockProBtn: 'Get Pro', lockOff: 'AI animation is temporarily unavailable. Please check back later.',
      tipsTitle: 'For the best result', tip1: 'One character with the face clearly visible.', tip2: 'Calm keeps the face; Lively gives more motion.', tip3: 'Hair and loose clothes move best; hands stay where they are.', tip4: '“Cut for Steam” sends the result straight to Process.',
      introTitle: 'AI animation beta test', introLead: 'We are testing a new tool: AI brings your art to life (hair, breathing, a glance) and the site turns it into a seamless loop for a Steam showcase.', introPro: 'Pro only', introProText: 'During the beta the tool works with Pro.', introOne: 'One animation per account', introOneText: 'For now every Pro account gets one animation for the whole beta. Failed or refused attempts come back automatically.', introMore: 'Need more?', introMoreText: 'Write to support and we will add more animations to your account.', introGo: 'Got it, let’s try', introSupport: 'Write to support', introBefore: 'Before', introAfter: 'After', err_ai_beta_used: 'Your beta animation is used. Write to support and we will add more.', support: 'Write to support' },
    ru: { eyebrow: 'Бета · Pro', heroTitle: 'Оживи свой арт', heroLead: 'ИИ мягко оживляет статичную картинку: волосы, дыхание, взгляд. Фон остаётся твоим, петля бесшовная — сразу для витрины Steam.',
      fact1: '1–3 минуты', fact2: 'Оригинальный фон', fact3: 'Бесшовная петля', fact4: 'GIF до 5 МБ + MP4',
      s1: 'Картинка', s1Hint: 'Лучше всего — один персонаж. PNG, JPG, WebP, GIF (первый кадр), до 40 МБ.', drop: 'Перетащи картинку сюда', dropOr: 'Выбрать файл', sample: 'Попробовать на примере', replace: 'Заменить',
      s2: 'Характер движения', calm: 'Спокойное', calmHint: 'Мягкое движение: лицо не меняется, волосы чуть покачиваются.', lively: 'Живое', livelyHint: 'Больше движения: волосы развеваются, персонаж двигается на месте. Лицо может немного меняться.',
      s3: 'Что двигается', s3Hint: 'Необязательно: выбери подсказки или опиши своими словами.', m_hair: 'Волосы', m_breath: 'Дыхание', m_blink: 'Моргание', m_gaze: 'Взгляд', m_wind: 'Ветер', m_glow: 'Свет',
      wishPh: 'Своё пожелание, например «развевается лента, мерцают звёзды»', s4: 'Фон',
      keepBg: 'Оставить оригинальный фон', keepBgHint: 'Из анимации берётся только то, что реально двигается, остальное — твоя картинка пиксель в пиксель.',
      go: 'Оживить', left: 'Осталось: {n} из {max}', unlimited: 'Для твоего аккаунта дневного лимита нет', refund: 'Если ИИ откажет или что-то сломается, попытка вернётся.',
      resultTitle: 'Результат', resultEmpty: 'Здесь появится твоя анимация.', yourPicture: 'Твоя картинка',
      st_queued: 'Ждём очередь…', st_prepare: 'Готовим картинку…', st_wish: 'Читаем пожелание…', st_sending: 'Отправляем ИИ…', st_queued_ai: 'Ждём ИИ-сервис…', st_animating: 'ИИ оживляет картинку, обычно 1–3 минуты…', st_assembling: 'Собираем бесшовную петлю…', st_saving: 'Сохраняем…', st_cancelling: 'Отменяем…',
      elapsed: '{s} с', cancel: 'Отменить', cancelled: 'Отменено. Попытка вернулась.',
      dlGif: 'Скачать GIF', dlMp4: 'Скачать MP4', toProcess: 'Нарезать для Steam', again: 'Ещё вариант', gifInfo: 'GIF {w}×{h} · {fps} к/с · {mb} МБ', saved: 'Ещё 30 дней лежит в «Моих результатах».', handing: 'Открываем «Обработку»…',
      err_ai_moderated: 'ИИ отказался анимировать картинку по своим правилам (обычно из-за обнажёнки). Попытка вернулась.', err_ai_site_busy: 'Дневной бюджет беты на весь сайт закончился. Попробуй завтра.',
      err_unavailable: 'ИИ-анимация временно недоступна.', err_bad_image: 'Не получилось прочитать картинку. Попробуй PNG или JPG.', err_too_small: 'Картинка слишком маленькая: нужно от 128 px по каждой стороне.', err_too_large: 'Картинка слишком большая: больше 40 мегапикселей.', err_too_big: 'Файл больше 40 МБ.', err_busy: 'Слишком много активных задач. Дождись окончания одной из них.', err_generic: 'Что-то пошло не так. Попытка вернулась, попробуй ещё раз.', pickFirst: 'Сначала добавь картинку.',
      lockLogin: 'Войди, чтобы пользоваться ИИ-анимацией', lockLoginBtn: 'Войти', lockPro: 'ИИ-анимация в бете и входит в Pro', lockProText: 'Каждая анимация считается на платной ИИ-модели, поэтому на время беты она входит в Pro.', lockProBtn: 'Получить Pro', lockOff: 'ИИ-анимация временно недоступна. Загляни чуть позже.',
      tipsTitle: 'Как получить лучший результат', tip1: 'Один персонаж, лицо хорошо видно.', tip2: '«Спокойное» сохраняет лицо, «Живое» даёт больше движения.', tip3: 'Лучше всего двигаются волосы и свободная одежда, руки остаются на месте.', tip4: '«Нарезать для Steam» сразу отправляет результат в «Обработку».',
      introTitle: 'Бета-тест ИИ-⁠анимации', introLead: 'Мы тестируем новый инструмент: ИИ оживляет твой арт (волосы, дыхание, взгляд), а сайт превращает результат в бесшовную петлю для витрины Steam.', introPro: 'Только для Pro', introProText: 'На время беты инструмент работает с Pro.', introOne: 'Одна анимация на аккаунт', introOneText: 'Пока каждому Pro-аккаунту даётся одна анимация на всю бету. Неудачные и отклонённые попытки возвращаются сами.', introMore: 'Нужно больше?', introMoreText: 'Напиши в поддержку, и мы добавим анимации на твой аккаунт.', introGo: 'Понятно, попробовать', introSupport: 'Написать в поддержку', introBefore: 'Было', introAfter: 'Стало', err_ai_beta_used: 'Твоя бета-анимация уже использована. Напиши в поддержку, и мы добавим ещё.', support: 'Написать в поддержку' },
    de: { eyebrow: 'Beta · Pro', heroTitle: 'Erwecke dein Bild zum Leben', heroLead: 'KI animiert ein Standbild sanft: Haare, Atmung, ein Blick. Der Hintergrund bleibt dein eigener und die Schleife ist nahtlos, bereit für eine Steam-Präsentation.',
      fact1: '1–3 Minuten', fact2: 'Dein Originalhintergrund', fact3: 'Nahtlose Schleife', fact4: 'GIF bis 5 MB + MP4',
      s1: 'Bild', s1Hint: 'Am besten eine Figur. PNG, JPG, WebP, GIF (erstes Bild), bis 40 MB.', drop: 'Bild hierher ziehen', dropOr: 'Datei wählen', sample: 'Mit einem Beispiel ausprobieren', replace: 'Ersetzen',
      s2: 'Bewegungsstil', calm: 'Ruhig', calmHint: 'Sanfte Bewegung: das Gesicht bleibt gleich, die Haare wiegen sich leicht.', lively: 'Lebendig', livelyHint: 'Mehr Bewegung: die Haare wehen, die Figur bewegt sich auf der Stelle. Das Gesicht kann sich etwas ändern.',
      s3: 'Was sich bewegen soll', s3Hint: 'Optional: Hinweise wählen oder mit eigenen Worten beschreiben.', m_hair: 'Haare', m_breath: 'Atmung', m_blink: 'Blinzeln', m_gaze: 'Blick', m_wind: 'Wind', m_glow: 'Licht',
      wishPh: 'Dein Wunsch, z. B. „das Band flattert, die Sterne funkeln“', s4: 'Hintergrund',
      keepBg: 'Originalhintergrund behalten', keepBgHint: 'Nur was sich wirklich bewegt, kommt aus der Animation; der Rest ist dein Bild, Pixel für Pixel.',
      go: 'Zum Leben erwecken', left: 'Übrig: {n} von {max}', unlimited: 'Für dein Konto gibt es kein Tageslimit', refund: 'Lehnt die KI ab oder geht etwas schief, bekommst du den Versuch zurück.',
      resultTitle: 'Ergebnis', resultEmpty: 'Hier erscheint deine Animation.', yourPicture: 'Dein Bild',
      st_queued: 'Wartet in der Warteschlange…', st_prepare: 'Bild wird vorbereitet…', st_wish: 'Wunsch wird gelesen…', st_sending: 'Wird an die KI gesendet…', st_queued_ai: 'Wartet auf den KI-Dienst…', st_animating: 'Die KI animiert, meist 1–3 Minuten…', st_assembling: 'Nahtlose Schleife wird gebaut…', st_saving: 'Wird gespeichert…', st_cancelling: 'Wird abgebrochen…',
      elapsed: '{s} s', cancel: 'Abbrechen', cancelled: 'Abgebrochen. Der Versuch ist zurück.',
      dlGif: 'GIF herunterladen', dlMp4: 'MP4 herunterladen', toProcess: 'Für Steam zuschneiden', again: 'Noch eine Variante', gifInfo: 'GIF {w}×{h} · {fps} fps · {mb} MB', saved: 'Bleibt 30 Tage in „Meine Ergebnisse“.', handing: 'Verarbeitung wird geöffnet…',
      err_ai_moderated: 'Die KI hat dieses Bild nach ihren Inhaltsregeln abgelehnt (meist Nacktheit). Der Versuch ist zurück.', err_ai_site_busy: 'Das Tagesbudget der Beta für die ganze Seite ist aufgebraucht. Versuch es morgen wieder.',
      err_unavailable: 'Die KI-Animation ist vorübergehend nicht verfügbar.', err_bad_image: 'Dieses Bild konnte nicht gelesen werden. Versuch PNG oder JPG.', err_too_small: 'Das Bild ist zu klein: mindestens 128 px pro Seite.', err_too_large: 'Das Bild ist zu groß: über 40 Megapixel.', err_too_big: 'Die Datei ist größer als 40 MB.', err_busy: 'Zu viele aktive Aufgaben. Warte, bis eine fertig ist.', err_generic: 'Etwas ist schiefgelaufen. Der Versuch ist zurück, versuch es noch einmal.', pickFirst: 'Füge zuerst ein Bild hinzu.',
      lockLogin: 'Melde dich an, um die KI-Animation zu nutzen', lockLoginBtn: 'Anmelden', lockPro: 'Die KI-Animation ist in der Beta und gehört zu Pro', lockProText: 'Jede Animation läuft auf einem kostenpflichtigen KI-Modell, deshalb gehört sie während der Beta zu Pro.', lockProBtn: 'Pro holen', lockOff: 'Die KI-Animation ist vorübergehend nicht verfügbar. Schau später wieder vorbei.',
      tipsTitle: 'Für das beste Ergebnis', tip1: 'Eine Figur, das Gesicht gut sichtbar.', tip2: 'Ruhig behält das Gesicht, Lebendig bringt mehr Bewegung.', tip3: 'Haare und lockere Kleidung bewegen sich am besten, Hände bleiben, wo sie sind.', tip4: '„Für Steam zuschneiden“ schickt das Ergebnis direkt in die Verarbeitung.',
      introTitle: 'Beta-Test der KI-Animation', introLead: 'Wir testen ein neues Werkzeug: KI erweckt dein Bild zum Leben (Haare, Atmung, ein Blick), und die Seite macht daraus eine nahtlose Schleife für eine Steam-Präsentation.', introPro: 'Nur mit Pro', introProText: 'Während der Beta funktioniert das Werkzeug mit Pro.', introOne: 'Eine Animation pro Konto', introOneText: 'Vorerst bekommt jedes Pro-Konto eine Animation für die ganze Beta. Fehlgeschlagene oder abgelehnte Versuche kommen automatisch zurück.', introMore: 'Du brauchst mehr?', introMoreText: 'Schreib dem Support, dann fügen wir deinem Konto weitere Animationen hinzu.', introGo: 'Verstanden, ausprobieren', introSupport: 'Support kontaktieren', introBefore: 'Vorher', introAfter: 'Nachher', err_ai_beta_used: 'Deine Beta-Animation ist aufgebraucht. Schreib dem Support, dann fügen wir mehr hinzu.', support: 'Support kontaktieren' },
    tr: { eyebrow: 'Beta · Pro', heroTitle: 'Çizimine hayat ver', heroLead: 'Yapay zekâ durağan bir resmi yumuşakça canlandırır: saçlar, nefes, bir bakış. Arka plan senin kalır ve döngü kesintisizdir; Steam vitrini için hazır.',
      fact1: '1–3 dakika', fact2: 'Orijinal arka planın', fact3: 'Kesintisiz döngü', fact4: '5 MB’a kadar GIF + MP4',
      s1: 'Resim', s1Hint: 'En iyisi tek karakter. PNG, JPG, WebP, GIF (ilk kare), 40 MB’a kadar.', drop: 'Resmi buraya bırak', dropOr: 'Dosya seç', sample: 'Örnekle dene', replace: 'Değiştir',
      s2: 'Hareket tarzı', calm: 'Sakin', calmHint: 'Yumuşak hareket: yüz aynı kalır, saçlar hafifçe sallanır.', lively: 'Canlı', livelyHint: 'Daha fazla hareket: saçlar dalgalanır, karakter yerinde hareket eder. Yüz biraz değişebilir.',
      s3: 'Ne hareket etsin', s3Hint: 'İsteğe bağlı: ipuçlarını seç ya da kendi sözlerinle anlat.', m_hair: 'Saçlar', m_breath: 'Nefes', m_blink: 'Göz kırpma', m_gaze: 'Bakış', m_wind: 'Rüzgâr', m_glow: 'Işık',
      wishPh: 'Kendi isteğin, ör. “kurdele dalgalanıyor, yıldızlar parlıyor”', s4: 'Arka plan',
      keepBg: 'Orijinal arka planı koru', keepBgHint: 'Animasyondan yalnızca gerçekten hareket eden alınır; gerisi piksel piksel senin resmin.',
      go: 'Hayat ver', left: 'Kalan: {n} / {max}', unlimited: 'Hesabın için günlük sınır yok', refund: 'Yapay zekâ reddederse ya da bir şey bozulursa hakkın geri gelir.',
      resultTitle: 'Sonuç', resultEmpty: 'Animasyonun burada görünecek.', yourPicture: 'Resmin',
      st_queued: 'Sırada bekliyor…', st_prepare: 'Resim hazırlanıyor…', st_wish: 'İsteğin okunuyor…', st_sending: 'Yapay zekâya gönderiliyor…', st_queued_ai: 'Yapay zekâ servisi bekleniyor…', st_animating: 'Yapay zekâ canlandırıyor, genelde 1–3 dakika…', st_assembling: 'Kesintisiz döngü kuruluyor…', st_saving: 'Kaydediliyor…', st_cancelling: 'İptal ediliyor…',
      elapsed: '{s} sn', cancel: 'İptal', cancelled: 'İptal edildi. Hakkın geri geldi.',
      dlGif: 'GIF indir', dlMp4: 'MP4 indir', toProcess: 'Steam için kes', again: 'Bir varyant daha', gifInfo: 'GIF {w}×{h} · {fps} fps · {mb} MB', saved: 'Sonuçlarım’da 30 gün daha durur.', handing: 'İşleme açılıyor…',
      err_ai_moderated: 'Yapay zekâ bu resmi içerik kuralları nedeniyle reddetti (genelde çıplaklık). Hakkın geri geldi.', err_ai_site_busy: 'Betanın tüm site için günlük bütçesi bitti. Yarın tekrar dene.',
      err_unavailable: 'Yapay zekâ animasyonu geçici olarak kullanılamıyor.', err_bad_image: 'Bu resim okunamadı. PNG ya da JPG dene.', err_too_small: 'Resim çok küçük: her kenarda en az 128 px.', err_too_large: 'Resim çok büyük: 40 megapikselden fazla.', err_too_big: 'Dosya 40 MB’tan büyük.', err_busy: 'Çok fazla etkin iş var. Birinin bitmesini bekle.', err_generic: 'Bir şeyler ters gitti. Hakkın geri geldi, tekrar dene.', pickFirst: 'Önce bir resim ekle.',
      lockLogin: 'Yapay zekâ animasyonunu kullanmak için giriş yap', lockLoginBtn: 'Giriş yap', lockPro: 'Yapay zekâ animasyonu beta aşamasında ve Pro’ya dahil', lockProText: 'Her animasyon ücretli bir yapay zekâ modelinde çalışır, bu yüzden beta süresince Pro’ya dahildir.', lockProBtn: 'Pro al', lockOff: 'Yapay zekâ animasyonu geçici olarak kullanılamıyor. Biraz sonra tekrar bak.',
      tipsTitle: 'En iyi sonuç için', tip1: 'Tek karakter, yüzü net görünsün.', tip2: 'Sakin yüzü korur, Canlı daha çok hareket verir.', tip3: 'En iyi saçlar ve bol giysiler hareket eder; eller yerinde kalır.', tip4: '“Steam için kes” sonucu doğrudan İşleme’ye gönderir.',
      introTitle: 'Yapay zekâ animasyonu beta testi', introLead: 'Yeni bir aracı test ediyoruz: yapay zekâ çizimine hayat verir (saçlar, nefes, bir bakış), site de bunu Steam vitrini için kesintisiz bir döngüye çevirir.', introPro: 'Yalnızca Pro', introProText: 'Beta süresince araç Pro ile çalışır.', introOne: 'Hesap başına bir animasyon', introOneText: 'Şimdilik her Pro hesabı tüm beta için bir animasyon alır. Başarısız ya da reddedilen denemeler otomatik geri gelir.', introMore: 'Daha fazlası mı lazım?', introMoreText: 'Desteğe yaz, hesabına daha fazla animasyon ekleyelim.', introGo: 'Anladım, deneyelim', introSupport: 'Desteğe yaz', introBefore: 'Önce', introAfter: 'Sonra', err_ai_beta_used: 'Beta animasyonun kullanıldı. Desteğe yaz, daha fazlasını ekleyelim.', support: 'Desteğe yaz' },
    fr: { eyebrow: 'Bêta · Pro', heroTitle: 'Donne vie à ton dessin', heroLead: 'L’IA anime doucement une image fixe : cheveux, respiration, un regard. Le fond reste le tien et la boucle est parfaite, prête pour une vitrine Steam.',
      fact1: '1–3 minutes', fact2: 'Ton fond d’origine', fact3: 'Boucle parfaite', fact4: 'GIF jusqu’à 5 Mo + MP4',
      s1: 'Image', s1Hint: 'Un seul personnage donne le meilleur résultat. PNG, JPG, WebP, GIF (première image), jusqu’à 40 Mo.', drop: 'Dépose une image ici', dropOr: 'Choisir un fichier', sample: 'Essayer avec un exemple', replace: 'Remplacer',
      s2: 'Style de mouvement', calm: 'Calme', calmHint: 'Mouvement doux : le visage ne change pas, les cheveux bougent un peu.', lively: 'Vivant', livelyHint: 'Plus de mouvement : les cheveux flottent, le personnage bouge sur place. Le visage peut un peu changer.',
      s3: 'Ce qui doit bouger', s3Hint: 'Facultatif : choisis des indices ou décris-le avec tes mots.', m_hair: 'Cheveux', m_breath: 'Respiration', m_blink: 'Clignement', m_gaze: 'Regard', m_wind: 'Vent', m_glow: 'Lumière',
      wishPh: 'Ton souhait, par ex. « le ruban flotte, les étoiles scintillent »', s4: 'Fond',
      keepBg: 'Garder le fond d’origine', keepBgHint: 'Seul ce qui bouge vraiment vient de l’animation ; le reste est ton image, pixel pour pixel.',
      go: 'Donner vie', left: 'Restant : {n} sur {max}', unlimited: 'Pas de limite quotidienne pour ton compte', refund: 'Si l’IA refuse ou si quelque chose échoue, l’essai est rendu.',
      resultTitle: 'Résultat', resultEmpty: 'Ton animation apparaîtra ici.', yourPicture: 'Ton image',
      st_queued: 'En file d’attente…', st_prepare: 'Préparation de l’image…', st_wish: 'Lecture de ton souhait…', st_sending: 'Envoi à l’IA…', st_queued_ai: 'En attente du service d’IA…', st_animating: 'L’IA anime l’image, en général 1–3 minutes…', st_assembling: 'Création d’une boucle parfaite…', st_saving: 'Enregistrement…', st_cancelling: 'Annulation…',
      elapsed: '{s} s', cancel: 'Annuler', cancelled: 'Annulé. L’essai est rendu.',
      dlGif: 'Télécharger le GIF', dlMp4: 'Télécharger le MP4', toProcess: 'Découper pour Steam', again: 'Une autre version', gifInfo: 'GIF {w}×{h} · {fps} i/s · {mb} Mo', saved: 'Gardé aussi 30 jours dans Mes résultats.', handing: 'Ouverture de Traitement…',
      err_ai_moderated: 'L’IA a refusé cette image selon ses règles de contenu (en général la nudité). L’essai est rendu.', err_ai_site_busy: 'Le budget quotidien de la bêta pour tout le site est épuisé. Réessaie demain.',
      err_unavailable: 'L’animation IA est temporairement indisponible.', err_bad_image: 'Impossible de lire cette image. Essaie PNG ou JPG.', err_too_small: 'L’image est trop petite : au moins 128 px de chaque côté.', err_too_large: 'L’image est trop grande : plus de 40 mégapixels.', err_too_big: 'Le fichier dépasse 40 Mo.', err_busy: 'Trop de tâches actives. Attends qu’une se termine.', err_generic: 'Un problème est survenu. L’essai est rendu, réessaie.', pickFirst: 'Ajoute d’abord une image.',
      lockLogin: 'Connecte-toi pour utiliser l’animation IA', lockLoginBtn: 'Se connecter', lockPro: 'L’animation IA est en bêta et fait partie de Pro', lockProText: 'Chaque animation tourne sur un modèle d’IA payant, c’est pourquoi pendant la bêta elle fait partie de Pro.', lockProBtn: 'Obtenir Pro', lockOff: 'L’animation IA est temporairement indisponible. Repasse un peu plus tard.',
      tipsTitle: 'Pour le meilleur résultat', tip1: 'Un seul personnage, le visage bien visible.', tip2: 'Calme garde le visage, Vivant donne plus de mouvement.', tip3: 'Les cheveux et les vêtements amples bougent le mieux ; les mains restent en place.', tip4: '« Découper pour Steam » envoie le résultat directement dans Traitement.',
      introTitle: 'Bêta-test de l’animation IA', introLead: 'Nous testons un nouvel outil : l’IA donne vie à ton dessin (cheveux, respiration, un regard) et le site en fait une boucle parfaite pour une vitrine Steam.', introPro: 'Réservé à Pro', introProText: 'Pendant la bêta, l’outil fonctionne avec Pro.', introOne: 'Une animation par compte', introOneText: 'Pour l’instant, chaque compte Pro reçoit une animation pour toute la bêta. Les essais échoués ou refusés sont rendus automatiquement.', introMore: 'Besoin de plus ?', introMoreText: 'Écris au support et nous ajouterons des animations à ton compte.', introGo: 'Compris, essayer', introSupport: 'Écrire au support', introBefore: 'Avant', introAfter: 'Après', err_ai_beta_used: 'Ton animation de la bêta est utilisée. Écris au support et nous en ajouterons.', support: 'Écrire au support' },
    uk: { eyebrow: 'Бета · Pro', heroTitle: 'Оживи свій арт', heroLead: 'ШІ м’яко оживлює статичну картинку: волосся, дихання, погляд. Фон лишається твоїм, петля безшовна — одразу для вітрини Steam.',
      fact1: '1–3 хвилини', fact2: 'Оригінальний фон', fact3: 'Безшовна петля', fact4: 'GIF до 5 МБ + MP4',
      s1: 'Картинка', s1Hint: 'Найкраще — один персонаж. PNG, JPG, WebP, GIF (перший кадр), до 40 МБ.', drop: 'Перетягни картинку сюди', dropOr: 'Вибрати файл', sample: 'Спробувати на прикладі', replace: 'Замінити',
      s2: 'Характер руху', calm: 'Спокійний', calmHint: 'М’який рух: обличчя не змінюється, волосся трохи погойдується.', lively: 'Живий', livelyHint: 'Більше руху: волосся розвівається, персонаж рухається на місці. Обличчя може трохи змінюватися.',
      s3: 'Що рухається', s3Hint: 'Необов’язково: вибери підказки або опиши своїми словами.', m_hair: 'Волосся', m_breath: 'Дихання', m_blink: 'Кліпання', m_gaze: 'Погляд', m_wind: 'Вітер', m_glow: 'Світло',
      wishPh: 'Своє побажання, наприклад «розвівається стрічка, мерехтять зорі»', s4: 'Фон',
      keepBg: 'Залишити оригінальний фон', keepBgHint: 'З анімації береться лише те, що справді рухається, решта — твоя картинка піксель у піксель.',
      go: 'Оживити', left: 'Залишилось: {n} з {max}', unlimited: 'Для твого акаунта денного ліміту немає', refund: 'Якщо ШІ відмовить або щось зламається, спроба повернеться.',
      resultTitle: 'Результат', resultEmpty: 'Тут з’явиться твоя анімація.', yourPicture: 'Твоя картинка',
      st_queued: 'Чекаємо чергу…', st_prepare: 'Готуємо картинку…', st_wish: 'Читаємо побажання…', st_sending: 'Надсилаємо ШІ…', st_queued_ai: 'Чекаємо ШІ-сервіс…', st_animating: 'ШІ оживлює картинку, зазвичай 1–3 хвилини…', st_assembling: 'Збираємо безшовну петлю…', st_saving: 'Зберігаємо…', st_cancelling: 'Скасовуємо…',
      elapsed: '{s} с', cancel: 'Скасувати', cancelled: 'Скасовано. Спроба повернулася.',
      dlGif: 'Завантажити GIF', dlMp4: 'Завантажити MP4', toProcess: 'Нарізати для Steam', again: 'Ще варіант', gifInfo: 'GIF {w}×{h} · {fps} к/с · {mb} МБ', saved: 'Ще 30 днів лежить у «Моїх результатах».', handing: 'Відкриваємо «Обробку»…',
      err_ai_moderated: 'ШІ відмовився анімувати картинку за своїми правилами (зазвичай через оголеність). Спроба повернулася.', err_ai_site_busy: 'Денний бюджет бети на весь сайт закінчився. Спробуй завтра.',
      err_unavailable: 'ШІ-анімація тимчасово недоступна.', err_bad_image: 'Не вдалося прочитати картинку. Спробуй PNG або JPG.', err_too_small: 'Картинка замала: потрібно від 128 px з кожного боку.', err_too_large: 'Картинка завелика: понад 40 мегапікселів.', err_too_big: 'Файл більший за 40 МБ.', err_busy: 'Забагато активних задач. Дочекайся завершення однієї з них.', err_generic: 'Щось пішло не так. Спроба повернулася, спробуй ще раз.', pickFirst: 'Спершу додай картинку.',
      lockLogin: 'Увійди, щоб користуватися ШІ-анімацією', lockLoginBtn: 'Увійти', lockPro: 'ШІ-анімація в беті та входить у Pro', lockProText: 'Кожна анімація рахується на платній ШІ-моделі, тож на час бети вона входить у Pro.', lockProBtn: 'Отримати Pro', lockOff: 'ШІ-анімація тимчасово недоступна. Зазирни трохи пізніше.',
      tipsTitle: 'Як отримати найкращий результат', tip1: 'Один персонаж, обличчя добре видно.', tip2: '«Спокійний» зберігає обличчя, «Живий» дає більше руху.', tip3: 'Найкраще рухаються волосся й вільний одяг, руки лишаються на місці.', tip4: '«Нарізати для Steam» одразу надсилає результат в «Обробку».',
      introTitle: 'Бета-тест ШІ-⁠анімації', introLead: 'Ми тестуємо новий інструмент: ШІ оживлює твій арт (волосся, дихання, погляд), а сайт перетворює результат на безшовну петлю для вітрини Steam.', introPro: 'Лише для Pro', introProText: 'На час бети інструмент працює з Pro.', introOne: 'Одна анімація на акаунт', introOneText: 'Поки що кожен Pro-акаунт отримує одну анімацію на всю бету. Невдалі й відхилені спроби повертаються самі.', introMore: 'Потрібно більше?', introMoreText: 'Напиши в підтримку, і ми додамо анімації на твій акаунт.', introGo: 'Зрозуміло, спробувати', introSupport: 'Написати в підтримку', introBefore: 'Було', introAfter: 'Стало', err_ai_beta_used: 'Твою бета-анімацію вже використано. Напиши в підтримку, і ми додамо ще.', support: 'Написати в підтримку' },
    es: { eyebrow: 'Beta · Pro', heroTitle: 'Dale vida a tu ilustración', heroLead: 'La IA anima con suavidad una imagen fija: el pelo, la respiración, una mirada. El fondo sigue siendo el tuyo y el bucle no tiene cortes, listo para un escaparate de Steam.',
      fact1: '1–3 minutos', fact2: 'Tu fondo original', fact3: 'Bucle sin cortes', fact4: 'GIF de hasta 5 MB + MP4',
      s1: 'Imagen', s1Hint: 'Funciona mejor con un solo personaje. PNG, JPG, WebP, GIF (primer fotograma), hasta 40 MB.', drop: 'Suelta una imagen aquí', dropOr: 'Elegir archivo', sample: 'Probar con un ejemplo', replace: 'Cambiar',
      s2: 'Estilo de movimiento', calm: 'Tranquilo', calmHint: 'Movimiento suave: la cara no cambia, el pelo se mece un poco.', lively: 'Vivo', livelyHint: 'Más movimiento: el pelo ondea, el personaje se mueve en su sitio. La cara puede cambiar un poco.',
      s3: 'Qué debe moverse', s3Hint: 'Opcional: elige pistas o descríbelo con tus palabras.', m_hair: 'Pelo', m_breath: 'Respiración', m_blink: 'Parpadeo', m_gaze: 'Mirada', m_wind: 'Viento', m_glow: 'Luz',
      wishPh: 'Tu deseo, p. ej. «la cinta ondea, las estrellas brillan»', s4: 'Fondo',
      keepBg: 'Mantener el fondo original', keepBgHint: 'De la animación solo se toma lo que realmente se mueve; el resto es tu imagen, píxel a píxel.',
      go: 'Dar vida', left: 'Quedan: {n} de {max}', unlimited: 'Tu cuenta no tiene límite diario', refund: 'Si la IA lo rechaza o algo falla, el intento se devuelve.',
      resultTitle: 'Resultado', resultEmpty: 'Tu animación aparecerá aquí.', yourPicture: 'Tu imagen',
      st_queued: 'Esperando en la cola…', st_prepare: 'Preparando la imagen…', st_wish: 'Leyendo tu deseo…', st_sending: 'Enviando a la IA…', st_queued_ai: 'Esperando al servicio de IA…', st_animating: 'La IA está animando, normalmente 1–3 minutos…', st_assembling: 'Montando un bucle sin cortes…', st_saving: 'Guardando…', st_cancelling: 'Cancelando…',
      elapsed: '{s} s', cancel: 'Cancelar', cancelled: 'Cancelado. El intento se devolvió.',
      dlGif: 'Descargar GIF', dlMp4: 'Descargar MP4', toProcess: 'Recortar para Steam', again: 'Otra versión', gifInfo: 'GIF {w}×{h} · {fps} fps · {mb} MB', saved: 'También se guarda 30 días en Mis resultados.', handing: 'Abriendo Procesar…',
      err_ai_moderated: 'La IA rechazó esta imagen por sus normas de contenido (normalmente desnudez). El intento se devolvió.', err_ai_site_busy: 'El presupuesto diario de la beta para todo el sitio se agotó. Inténtalo mañana.',
      err_unavailable: 'La animación con IA no está disponible por ahora.', err_bad_image: 'No se pudo leer esta imagen. Prueba PNG o JPG.', err_too_small: 'La imagen es demasiado pequeña: al menos 128 px por lado.', err_too_large: 'La imagen es demasiado grande: más de 40 megapíxeles.', err_too_big: 'El archivo supera los 40 MB.', err_busy: 'Demasiadas tareas activas. Espera a que termine una.', err_generic: 'Algo salió mal. El intento se devolvió, inténtalo otra vez.', pickFirst: 'Primero añade una imagen.',
      lockLogin: 'Inicia sesión para usar la animación con IA', lockLoginBtn: 'Iniciar sesión', lockPro: 'La animación con IA está en beta y forma parte de Pro', lockProText: 'Cada animación se calcula en un modelo de IA de pago, por eso durante la beta forma parte de Pro.', lockProBtn: 'Obtener Pro', lockOff: 'La animación con IA no está disponible por ahora. Vuelve más tarde.',
      tipsTitle: 'Para el mejor resultado', tip1: 'Un solo personaje, con la cara bien visible.', tip2: 'Tranquilo conserva la cara; Vivo da más movimiento.', tip3: 'El pelo y la ropa suelta son lo que mejor se mueve; las manos se quedan donde están.', tip4: '«Recortar para Steam» envía el resultado directamente a Procesar.',
      introTitle: 'Prueba beta de la animación con IA', introLead: 'Estamos probando una herramienta nueva: la IA da vida a tu ilustración (el pelo, la respiración, una mirada) y el sitio la convierte en un bucle sin cortes para un escaparate de Steam.', introPro: 'Solo para Pro', introProText: 'Durante la beta la herramienta funciona con Pro.', introOne: 'Una animación por cuenta', introOneText: 'Por ahora cada cuenta Pro recibe una animación para toda la beta. Los intentos fallidos o rechazados se devuelven solos.', introMore: '¿Necesitas más?', introMoreText: 'Escribe al soporte y añadiremos más animaciones a tu cuenta.', introGo: 'Entendido, probar', introSupport: 'Escribir al soporte', introBefore: 'Antes', introAfter: 'Después', err_ai_beta_used: 'Tu animación de la beta ya se usó. Escribe al soporte y añadiremos más.', support: 'Escribir al soporte' },
    pt: { eyebrow: 'Beta · Pro', heroTitle: 'Dê vida à sua arte', heroLead: 'A IA anima com suavidade uma imagem parada: cabelo, respiração, um olhar. O fundo continua sendo o seu e o loop não tem emenda, pronto para uma vitrine da Steam.',
      fact1: '1–3 minutos', fact2: 'Seu fundo original', fact3: 'Loop sem emenda', fact4: 'GIF de até 5 MB + MP4',
      s1: 'Imagem', s1Hint: 'Funciona melhor com um personagem. PNG, JPG, WebP, GIF (primeiro quadro), até 40 MB.', drop: 'Solte uma imagem aqui', dropOr: 'Escolher arquivo', sample: 'Experimentar com um exemplo', replace: 'Trocar',
      s2: 'Estilo de movimento', calm: 'Calmo', calmHint: 'Movimento suave: o rosto não muda, o cabelo balança um pouco.', lively: 'Vivo', livelyHint: 'Mais movimento: o cabelo esvoaça, o personagem se mexe no lugar. O rosto pode mudar um pouco.',
      s3: 'O que deve se mexer', s3Hint: 'Opcional: escolha dicas ou descreva com suas palavras.', m_hair: 'Cabelo', m_breath: 'Respiração', m_blink: 'Piscar', m_gaze: 'Olhar', m_wind: 'Vento', m_glow: 'Luz',
      wishPh: 'Seu desejo, por ex. «a fita esvoaça, as estrelas cintilam»', s4: 'Fundo',
      keepBg: 'Manter o fundo original', keepBgHint: 'Da animação só vem o que realmente se mexe; o resto é a sua imagem, pixel por pixel.',
      go: 'Dar vida', left: 'Restam: {n} de {max}', unlimited: 'Sua conta não tem limite diário', refund: 'Se a IA recusar ou algo falhar, a tentativa volta.',
      resultTitle: 'Resultado', resultEmpty: 'Sua animação vai aparecer aqui.', yourPicture: 'Sua imagem',
      st_queued: 'Aguardando na fila…', st_prepare: 'Preparando a imagem…', st_wish: 'Lendo seu desejo…', st_sending: 'Enviando para a IA…', st_queued_ai: 'Aguardando o serviço de IA…', st_animating: 'A IA está animando, normalmente 1–3 minutos…', st_assembling: 'Montando um loop sem emenda…', st_saving: 'Salvando…', st_cancelling: 'Cancelando…',
      elapsed: '{s} s', cancel: 'Cancelar', cancelled: 'Cancelado. A tentativa voltou.',
      dlGif: 'Baixar GIF', dlMp4: 'Baixar MP4', toProcess: 'Cortar para a Steam', again: 'Outra versão', gifInfo: 'GIF {w}×{h} · {fps} qps · {mb} MB', saved: 'Também fica 30 dias em Meus resultados.', handing: 'Abrindo Processar…',
      err_ai_moderated: 'A IA recusou esta imagem pelas regras de conteúdo (normalmente nudez). A tentativa voltou.', err_ai_site_busy: 'O orçamento diário da beta para o site inteiro acabou. Tente amanhã.',
      err_unavailable: 'A animação com IA está temporariamente indisponível.', err_bad_image: 'Não foi possível ler esta imagem. Tente PNG ou JPG.', err_too_small: 'A imagem é pequena demais: pelo menos 128 px de cada lado.', err_too_large: 'A imagem é grande demais: mais de 40 megapixels.', err_too_big: 'O arquivo tem mais de 40 MB.', err_busy: 'Tarefas ativas demais. Espere uma terminar.', err_generic: 'Algo deu errado. A tentativa voltou, tente de novo.', pickFirst: 'Adicione uma imagem primeiro.',
      lockLogin: 'Entre para usar a animação com IA', lockLoginBtn: 'Entrar', lockPro: 'A animação com IA está em beta e faz parte do Pro', lockProText: 'Cada animação roda em um modelo de IA pago, por isso durante a beta ela faz parte do Pro.', lockProBtn: 'Obter o Pro', lockOff: 'A animação com IA está temporariamente indisponível. Volte daqui a pouco.',
      tipsTitle: 'Para o melhor resultado', tip1: 'Um personagem, com o rosto bem visível.', tip2: 'Calmo mantém o rosto; Vivo dá mais movimento.', tip3: 'Cabelo e roupas soltas se mexem melhor; as mãos ficam no lugar.', tip4: '«Cortar para a Steam» manda o resultado direto para Processar.',
      introTitle: 'Teste beta da animação com IA', introLead: 'Estamos testando uma ferramenta nova: a IA dá vida à sua arte (cabelo, respiração, um olhar) e o site transforma isso em um loop sem emenda para uma vitrine da Steam.', introPro: 'Só para o Pro', introProText: 'Durante a beta a ferramenta funciona com o Pro.', introOne: 'Uma animação por conta', introOneText: 'Por enquanto cada conta Pro recebe uma animação para toda a beta. Tentativas que falharem ou forem recusadas voltam sozinhas.', introMore: 'Precisa de mais?', introMoreText: 'Escreva para o suporte e adicionaremos mais animações à sua conta.', introGo: 'Entendi, experimentar', introSupport: 'Falar com o suporte', introBefore: 'Antes', introAfter: 'Depois', err_ai_beta_used: 'Sua animação da beta já foi usada. Escreva para o suporte e adicionaremos mais.', support: 'Falar com o suporte' }
  };
  var MOTIONS = ['hair', 'breath', 'blink', 'gaze', 'wind', 'glow'];
  var STORE = 'sm_aianim_settings', JOB_KEY = 'sm_aianim_job';
  var DEMO = { calm: '/static/img/ai-animate/demo-calm.mp4?v=1', lively: '/static/img/ai-animate/demo-lively.mp4?v=1' };
  var POSTER = { calm: '/static/img/ai-animate/demo-calm.webp?v=1', lively: '/static/img/ai-animate/demo-lively.webp?v=1' };

  var host = document.getElementById('aiAnimate');
  if (!host) return;

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key, vars) {
    var text = (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.split('{' + k + '}').join(vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function button(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }
  function svg(paths, cls) { var s = el('span', cls || 'aia-ico'); s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + paths + '</svg>'; return s; }
  var ICON = {
    hair: '<path d="M7 20c0-6 1-11 5-14 4 3 5 8 5 14M9.5 20c0-4 .8-7 2.5-9M14.5 20c0-4-.8-7-2.5-9"/>',
    breath: '<path d="M4 12h4l2-5 4 10 2-5h4"/>',
    blink: '<path d="M3 12c3-4 6-6 9-6s6 2 9 6c-3 4-6 6-9 6s-6-2-9-6z"/><path d="M3 12h18"/>',
    gaze: '<circle cx="12" cy="12" r="7"/><circle cx="14" cy="11" r="2.5"/>',
    wind: '<path d="M3 9h11a3 3 0 1 0-3-3M3 15h15a3 3 0 1 1-3 3M3 12h8"/>',
    glow: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/><circle cx="12" cy="12" r="3"/>',
    upload: '<path d="M12 16V5m0 0-4 4m4-4 4 4M5 15v3a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/>',
    spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>'
  };

  var state = { file: null, url: '', mode: 'calm', motions: ['hair', 'breath'], wish: '', keepBg: true,
    info: null, job: null, jobId: '', started: 0, result: null, error: '', busy: false };
  try {
    var saved = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (saved) {
      if (saved.mode === 'lively' || saved.mode === 'calm') state.mode = saved.mode;
      if (Array.isArray(saved.motions)) state.motions = saved.motions.filter(function (m) { return MOTIONS.indexOf(m) >= 0; });
      if (typeof saved.keepBg === 'boolean') state.keepBg = saved.keepBg;
    }
  } catch (_) {}
  function save() { try { localStorage.setItem(STORE, JSON.stringify({ mode: state.mode, motions: state.motions, keepBg: state.keepBg })); } catch (_) {} }
  var refs = {};

  // ---------------------------------------------------------------- markup
  function step(n, title, hint) {
    var head = el('div', 'aia-step');
    var text = el('div', 'aia-step__text');
    text.append(el('h3', 'aia-h', title));
    if (hint) text.append(el('p', 'aia-muted', hint));
    head.append(el('span', 'aia-step__n', String(n)), text);
    return head;
  }
  function demo(mode, cls) {
    var video = el('video', cls);
    video.muted = true; video.loop = true; video.autoplay = true; video.playsInline = true; video.setAttribute('playsinline', '');
    video.preload = 'metadata'; video.poster = POSTER[mode]; video.src = DEMO[mode];
    video.setAttribute('aria-label', t(mode));
    return video;
  }
  // A one-off welcome in place of the hero (owner 2026-10-10): beta, Pro only, one animation per account, more
  // through support. Remembered per browser (localStorage); without storage it simply shows every time.
  var INTRO_KEY = 'sm_aianim_intro_v1';
  function introSeen() { try { return localStorage.getItem(INTRO_KEY) === '1'; } catch (_) { return false; } }
  function intro() {
    var box = el('section', 'aia-intro');
    var copy = el('div', 'aia-intro__copy');
    copy.append(el('span', 'aia-eyebrow', t('eyebrow')), el('h2', 'aia-intro__title', t('introTitle')), el('p', 'aia-intro__lead', t('introLead')));
    var points = el('ul', 'aia-intro__points');
    [['introPro', 'introProText', ICON.spark], ['introOne', 'introOneText', ICON.breath], ['introMore', 'introMoreText', ICON.gaze]].forEach(function (row) {
      var li = el('li');
      var text = el('div');
      text.append(el('b', '', t(row[0])), el('span', '', t(row[1])));
      li.append(svg(row[2], 'aia-intro__icon'), text);
      points.append(li);
    });
    var actions = el('div', 'aia-intro__actions');
    var go = button('aia-go', t('introGo'), function () {
      try { localStorage.setItem(INTRO_KEY, '1'); } catch (_) {}
      box.replaceWith(hero());
    });
    var help = button('aia-btn aia-intro__support', t('introSupport'));
    help.setAttribute('data-support-choice', '');
    actions.append(go, help);
    copy.append(points, actions);
    var show = el('div', 'aia-intro__show');
    var before = el('figure', 'aia-intro__card');
    var img = el('img'); img.src = POSTER.calm; img.alt = ''; img.loading = 'lazy';
    before.append(img, el('figcaption', '', t('introBefore')));
    var after = el('figure', 'aia-intro__card aia-intro__card--live');
    after.append(demo('lively', ''), el('figcaption', '', '✨ ' + t('introAfter')));
    show.append(before, after);
    box.append(copy, show);
    return box;
  }
  function hero() {
    var hero = el('section', 'aia-hero');
    var copy = el('div', 'aia-hero__copy');
    copy.append(el('span', 'aia-eyebrow', t('eyebrow')), el('h2', 'aia-hero__title', t('heroTitle')), el('p', 'aia-hero__lead', t('heroLead')));
    var facts = el('ul', 'aia-facts');
    ['fact1', 'fact2', 'fact3', 'fact4'].forEach(function (k) { facts.append(el('li', '', t(k))); });
    copy.append(facts);
    var show = el('div', 'aia-hero__show');
    var still = el('figure', 'aia-hero__card');
    var stillImg = el('img'); stillImg.src = POSTER.calm; stillImg.alt = ''; stillImg.loading = 'lazy';
    still.append(stillImg, el('figcaption', '', t('yourPicture')));
    var live = el('figure', 'aia-hero__card aia-hero__card--live');
    live.append(demo('lively', ''), el('figcaption', '', '✨ ' + t('lively')));
    show.append(still, svg('<path d="M5 12h14m-5-5 5 5-5 5"/>', 'aia-hero__arrow'), live);
    hero.append(copy, show);
    return hero;
  }
  function build() {
    host.replaceChildren();
    var root = el('div', 'aia');

    // Settings
    var form = el('section', 'aia-panel aia-form');
    // 1 picture
    var input = el('input'); input.type = 'file'; input.accept = 'image/*'; input.hidden = true;
    input.dataset.smEnhanced = '1';
    input.addEventListener('change', function () { if (input.files[0]) pick(input.files[0]); input.value = ''; });
    refs.input = input;
    var drop = el('div', 'aia-drop');
    refs.drop = drop;
    ['dragenter', 'dragover'].forEach(function (e) { drop.addEventListener(e, function (ev) { ev.preventDefault(); drop.classList.add('is-over'); }); });
    ['dragleave', 'drop'].forEach(function (e) { drop.addEventListener(e, function (ev) { ev.preventDefault(); if (e === 'drop' || !drop.contains(ev.relatedTarget)) drop.classList.remove('is-over'); }); });
    drop.addEventListener('drop', function (ev) { var f = ev.dataTransfer && ev.dataTransfer.files[0]; if (f) pick(f); });
    var s1 = el('div', 'aia-block');
    s1.append(step(1, t('s1'), t('s1Hint')), drop, input);
    // 2 mode
    var s2 = el('div', 'aia-block');
    var modes = el('div', 'aia-modes');
    refs.modes = {};
    ['calm', 'lively'].forEach(function (mode) {
      var card = button('aia-mode', null, function () { state.mode = mode; save(); paint(); });
      var media = el('div', 'aia-mode__media');
      media.append(demo(mode, ''));
      var text = el('span', 'aia-mode__text');
      text.append(el('b', '', t(mode)), el('small', '', t(mode + 'Hint')));
      card.append(media, text);
      refs.modes[mode] = card;
      modes.append(card);
    });
    s2.append(step(2, t('s2')), modes);
    // 3 motions + wish
    var s3 = el('div', 'aia-block');
    var chips = el('div', 'aia-chips');
    refs.chips = {};
    MOTIONS.forEach(function (m) {
      var chip = button('aia-chip', null, function () {
        var at = state.motions.indexOf(m);
        if (at >= 0) state.motions.splice(at, 1); else state.motions.push(m);
        save(); paint();
      });
      chip.append(svg(ICON[m]), el('span', '', t('m_' + m)));
      refs.chips[m] = chip;
      chips.append(chip);
    });
    var wishWrap = el('label', 'aia-wish');
    var wish = el('textarea'); wish.rows = 2; wish.maxLength = 200; wish.placeholder = t('wishPh'); wish.value = state.wish;
    var count = el('small', 'aia-wish__count');
    wish.addEventListener('input', function () { state.wish = wish.value; count.textContent = wish.value.length + '/200'; });
    count.textContent = state.wish.length + '/200';
    wishWrap.append(wish, count);
    s3.append(step(3, t('s3'), t('s3Hint')), chips, wishWrap);
    // 4 background (the model returns a 5 s clip that comes back to its first frame; short loops come later)
    var s4 = el('div', 'aia-block');
    var keep = el('label', 'aia-switch');
    var box = el('input'); box.type = 'checkbox'; box.checked = state.keepBg;
    box.addEventListener('change', function () { state.keepBg = box.checked; save(); });
    var keepText = el('span', 'aia-switch__text');
    keepText.append(el('b', '', t('keepBg')), el('small', '', t('keepBgHint')));
    keep.append(box, el('i', 'aia-switch__ui'), keepText);
    s4.append(step(4, t('s4')), keep);
    // action
    var action = el('div', 'aia-action');
    var go = button('aia-go', null, function () { run(); });
    go.append(svg(ICON.spark), el('span', '', t('go')));
    refs.go = go;
    refs.left = el('p', 'aia-left');
    action.append(go, refs.left, el('p', 'aia-muted aia-refund', t('refund')));
    form.append(s1, s2, s3, s4, action);

    // Result
    var result = el('aside', 'aia-panel aia-result');
    result.append(el('h3', 'aia-h', t('resultTitle')));
    refs.stage = el('div', 'aia-stage');
    refs.actions = el('div', 'aia-actions');
    refs.message = el('p', 'aia-message'); refs.message.setAttribute('role', 'status');
    result.append(refs.stage, refs.message, refs.actions);

    var grid = el('div', 'aia-grid');
    grid.append(form, result);
    // Tips
    var tips = el('section', 'aia-panel aia-tips');
    tips.append(el('h3', 'aia-h', t('tipsTitle')));
    var list = el('ol', 'aia-tips__list');
    ['tip1', 'tip2', 'tip3', 'tip4'].forEach(function (k) { list.append(el('li', '', t(k))); });
    tips.append(list);
    refs.lock = el('div', 'aia-lock');
    root.append(introSeen() ? hero() : intro(), refs.lock, grid, tips);
    host.append(root);
    paint();
  }

  // ---------------------------------------------------------------- paint
  function paintDrop() {
    var drop = refs.drop;
    drop.replaceChildren();
    if (state.url) {
      drop.classList.add('has-file');
      var img = el('img', 'aia-drop__img'); img.src = state.url; img.alt = state.file ? state.file.name : '';
      var bar = el('div', 'aia-drop__bar');
      bar.append(el('span', 'aia-drop__name', state.file ? state.file.name : ''), button('aia-btn aia-btn--small', t('replace'), function () { refs.input.click(); }));
      drop.append(img, bar);
    } else {
      drop.classList.remove('has-file');
      var inner = button('aia-drop__empty', null, function () { refs.input.click(); });
      inner.append(svg(ICON.upload, 'aia-drop__icon'), el('b', '', t('drop')), el('span', 'aia-drop__btn', t('dropOr')));
      drop.append(inner, button('aia-link', t('sample'), sample));
    }
  }
  function paintLock() {
    var info = state.info, lock = refs.lock;
    lock.replaceChildren();
    var kind = !info ? '' : !info.available ? 'off' : !info.signed_in ? 'login' : !info.pro ? 'pro' : '';
    lock.hidden = !kind;
    host.querySelector('.aia').classList.toggle('is-locked', !!kind);
    if (!kind) return;
    var card = el('div', 'aia-lock__card');
    card.append(svg(ICON.spark, 'aia-lock__icon'));
    if (kind === 'off') card.append(el('b', '', t('lockOff')));
    if (kind === 'login') {
      card.append(el('b', '', t('lockLogin')),
        button('aia-go aia-go--small', t('lockLoginBtn'), function () { if (window.SSShell && SSShell.openAuth) SSShell.openAuth('login'); }));
    }
    if (kind === 'pro') {
      card.append(el('b', '', t('lockPro')), el('p', 'aia-muted', t('lockProText')),
        button('aia-go aia-go--small', t('lockProBtn'), function () { if (window.SSShell && SSShell.openActivation) SSShell.openActivation(); }));
    }
    lock.append(card);
  }
  function paintResult() {
    var stage = refs.stage, actions = refs.actions, job = state.job;
    stage.replaceChildren(); actions.replaceChildren();
    refs.message.textContent = state.error || '';
    refs.message.classList.toggle('is-bad', !!state.error);
    if (state.errorCode === 'ai_beta_used') {
      var help = button('aia-btn aia-btn--small aia-message__support', t('support'));
      help.setAttribute('data-support-choice', '');
      refs.message.append(' ', help);
    }
    if (state.result) {
      var img = el('img', 'aia-stage__media'); img.src = state.result.gif_url; img.alt = t('resultTitle');
      stage.append(img);
      var r = state.result;
      var info = el('p', 'aia-muted aia-result__info', t('gifInfo', { w: r.out_width, h: r.out_height, fps: r.out_fps, mb: (r.gif_bytes / 1048576).toFixed(2) }));
      var a1 = el('a', 'aia-go aia-go--small'); a1.href = r.gif_download; a1.append(svg(ICON.upload, 'aia-ico aia-ico--down'), el('span', '', t('dlGif')));
      var a2 = el('a', 'aia-btn'); a2.href = r.mp4_download; a2.textContent = t('dlMp4');
      actions.append(a1, a2, button('aia-btn', t('toProcess'), toProcess), button('aia-btn', t('again'), function () { run(); }), info);
      if (r.saved_id) actions.append(el('p', 'aia-muted', t('saved')));
      return;
    }
    if (job) {
      var wrap = el('div', 'aia-progress');
      var base = el('div', 'aia-progress__picture');
      if (state.url) { var pic = el('img'); pic.src = state.url; pic.alt = ''; base.append(pic); }
      base.append(el('span', 'aia-progress__shine'));
      var label = el('b', 'aia-progress__label', t('st_' + (job.stage || 'queued')) || t('st_queued'));
      var bar = el('span', 'aia-progress__bar'); var fill = el('i'); fill.style.width = Math.max(4, job.pct || 0) + '%'; bar.append(fill);
      var elapsed = el('small', 'aia-muted', t('elapsed', { s: Math.round((Date.now() - state.started) / 1000) }));
      refs.elapsed = elapsed;
      wrap.append(base, label, bar, elapsed);
      stage.append(wrap);
      actions.append(button('aia-btn', t('cancel'), cancel));
      return;
    }
    var empty = el('div', 'aia-stage__empty');
    if (state.url) { var p = el('img', 'aia-stage__media aia-stage__media--still'); p.src = state.url; p.alt = ''; empty.append(p); }
    else empty.append(svg(ICON.spark, 'aia-stage__icon'));
    empty.append(el('span', '', t('resultEmpty')));
    stage.append(empty);
  }
  function paint() {
    if (!refs.drop) return;
    paintDrop();
    Object.keys(refs.modes).forEach(function (m) { refs.modes[m].classList.toggle('is-on', state.mode === m); refs.modes[m].setAttribute('aria-pressed', String(state.mode === m)); });
    MOTIONS.forEach(function (m) { var on = state.motions.indexOf(m) >= 0; refs.chips[m].classList.toggle('is-on', on); refs.chips[m].setAttribute('aria-pressed', String(on)); });
    var quota = state.info && state.info.quota;
    refs.left.textContent = !quota ? '' : quota.left == null ? t('unlimited') : t('left', { n: quota.left, max: quota.total });
    refs.go.disabled = state.busy || !!state.job;
    paintLock();
    paintResult();
  }

  // ---------------------------------------------------------------- actions
  function pick(file) {
    if (!/^image\//.test(file.type) && !/\.(png|jpe?g|webp|gif|bmp|avif|heic|heif|tiff?)$/i.test(file.name || '')) { fail('err_bad_image'); return; }
    if (state.url) URL.revokeObjectURL(state.url);
    state.file = file; state.url = URL.createObjectURL(file); state.result = null; state.error = '';
    paint();
  }
  function sample() {
    fetch('/static/img/samples/sample-art.webp?v=2', { cache: 'force-cache' }).then(function (r) { return r.blob(); })
      .then(function (blob) { pick(new File([blob], 'sample-art.webp', { type: 'image/webp' })); })
      .catch(function () { fail('err_generic'); });
  }
  function fail(key) { state.error = t(key); state.errorCode = key.replace(/^err_/, ''); state.busy = false; paint(); }
  function loadInfo() {
    return fetch('/api/ai-animate/info', { credentials: 'same-origin' }).then(function (r) { return r.json(); })
      .then(function (info) { state.info = info; paint(); }).catch(function () {});
  }
  function run() {
    if (state.busy || state.job) return;
    if (!state.file) { fail('pickFirst'); return; }
    state.busy = true; state.error = ''; state.errorCode = ''; state.result = null; paint();
    var fd = new FormData();
    fd.append('file', state.file, state.file.name || 'picture.png');
    fd.append('mode', state.mode);
    fd.append('motions', state.motions.join(','));
    fd.append('wish', state.wish || '');
    fd.append('keep_background', state.keepBg ? 'true' : 'false');
    fetch('/api/ai-animate/start', { method: 'POST', body: fd, credentials: 'same-origin' })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { r: r, j: j }; }); })
      .then(function (x) {
        state.busy = false;
        if (!x.r.ok || !x.j.ok) {
          if (x.j && x.j.limit && x.j.limit.kind) { state.error = ''; paint(); return; }   // free-limits.js shows its dialog
          fail('err_' + ((x.j && x.j.code) || 'generic')); return;
        }
        track(x.j.job_id, Date.now());
        loadInfo();
      })
      .catch(function () { fail('err_generic'); });
  }
  function track(id, started) {
    state.jobId = id; state.started = started; state.job = { stage: 'queued', pct: 2 };
    try { sessionStorage.setItem(JOB_KEY, JSON.stringify({ id: id, started: started })); } catch (_) {}
    paint(); poll();
  }
  function finish() { state.job = null; state.jobId = ''; try { sessionStorage.removeItem(JOB_KEY); } catch (_) {} }
  var pollTimer = 0;
  function poll() {
    clearTimeout(pollTimer);
    if (!state.jobId) return;
    fetch('/api/ai-animate/status/' + state.jobId, { credentials: 'same-origin' }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) { finish(); fail('err_generic'); return; }
        if (j.status === 'done') { state.result = j; finish(); state.error = ''; paint(); loadInfo(); return; }
        if (j.status === 'error') { finish(); fail(COPY.en['err_' + j.error_code] ? 'err_' + j.error_code : 'err_generic'); loadInfo(); return; }
        if (j.status === 'cancelled') { finish(); state.error = t('cancelled'); paint(); loadInfo(); return; }
        state.job = j; paint();
        pollTimer = setTimeout(poll, 2500);
      })
      .catch(function () { pollTimer = setTimeout(poll, 5000); });
  }
  function cancel() {
    if (!state.jobId) return;
    state.job = Object.assign({}, state.job, { stage: 'cancelling' }); paint();
    fetch('/api/ai-animate/cancel/' + state.jobId, { method: 'POST', credentials: 'same-origin' }).catch(function () {});
  }
  function toProcess() {
    var r = state.result;
    if (!r) return;
    refs.message.textContent = t('handing');
    fetch(r.mp4_download, { credentials: 'same-origin' }).then(function (res) { return res.blob(); }).then(function (blob) {
      var file = new File([blob], 'ai-animation.mp4', { type: 'video/mp4' });
      var nav = document.querySelector('#nav button[data-tab="process"]');
      if (nav) nav.click();
      setTimeout(function () { document.dispatchEvent(new CustomEvent('sm:assets-selected', { detail: { target: 'process', files: [file] } })); }, 150);
    }).catch(function () { fail('err_generic'); });
  }
  setInterval(function () { if (state.job && refs.elapsed) refs.elapsed.textContent = t('elapsed', { s: Math.round((Date.now() - state.started) / 1000) }); }, 1000);

  // ---------------------------------------------------------------- start
  var loaded = false;
  function open() {
    if (!loaded) { loaded = true; build(); }
    loadInfo();
    try {
      var running = JSON.parse(sessionStorage.getItem(JOB_KEY) || 'null');
      if (running && running.id && !state.jobId) track(running.id, running.started || Date.now());
    } catch (_) {}
  }
  function tabOpen() { var tab = document.getElementById('tab-aianim'); return tab && tab.classList.contains('active'); }
  document.addEventListener('click', function (event) {
    var b = event.target.closest && event.target.closest('[data-tab="aianim"]');
    if (b) setTimeout(open, 0);
  });
  if (tabOpen() || /#aianim\b/.test(location.hash)) open();
  window.addEventListener('sm:langchange', function () { if (loaded) build(); });
  document.addEventListener('paste', function (event) {
    if (!tabOpen() || !event.clipboardData) return;
    var item = Array.prototype.find.call(event.clipboardData.files || [], function (f) { return /^image\//.test(f.type); });
    if (item) pick(item);
  });
  window.SMAiAnimate = { state: state, open: open, pick: pick, run: run, paint: paint };
})();
