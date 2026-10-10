/* Notification bell (2026-10-01). Loaded by ss-shell.js for signed-in users only.
   The server stores kind + parameters; the text is written here in the visitor's
   language. Errors explain in plain words what went wrong and what to do.
   Polls the unread count once a minute while the tab is visible.
   Owner messages (kind admin_message, smweb/admin_messages.py, 2026-10-07) open as a window over
   the page: the unread poll returns the newest one marked "popup", right after load and then every
   minute; closing it marks it read. Clicking such a message in the bell opens the same window. */
(function () {
  'use strict';
  if (window.SMBell) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  function lang() { var l = window.SSShell ? SSShell.lang() : 'en'; return LANGS.indexOf(l) >= 0 ? l : 'en'; }
  function L(values) { return values[LANGS.indexOf(lang())] || values[0]; }
  function fmt(text, vars) { return String(text).replace(/\{(\w+)\}/g, function (m, k) { return vars && vars[k] != null ? vars[k] : ''; }); }
  function esc(s) { return window.SSShell ? SSShell.esc(s) : String(s); }
  function svg(name) { return window.SSShell ? SSShell.svg(name) : ''; }
  function url(path) { return window.SSShell ? SSShell.siteUrl(path) : path; }

  // [en, ru, de, tr, fr, uk, es, pt]
  var UI = {
    title: ['Notifications', 'Уведомления', 'Benachrichtigungen', 'Bildirimler', 'Notifications', 'Сповіщення', 'Notificaciones', 'Notificações'],
    readAll: ['Mark all as read', 'Прочитать все', 'Alle als gelesen markieren', 'Tümünü okundu say', 'Tout marquer comme lu', 'Прочитати всі', 'Marcar todo como leído', 'Marcar tudo como lido'],
    empty: ['Nothing here yet. Replies, finished jobs and news will appear here.', 'Пока пусто. Здесь появятся ответы поддержки, готовые задачи и новости.', 'Noch leer. Antworten, fertige Aufträge und Neuigkeiten erscheinen hier.', 'Henüz boş. Yanıtlar, biten işler ve haberler burada görünecek.', 'Rien pour l’instant. Réponses, tâches terminées et actualités apparaîtront ici.', 'Поки порожньо. Тут з’являться відповіді підтримки, готові завдання й новини.', 'Aún no hay nada. Aquí aparecerán respuestas, tareas terminadas y noticias.', 'Ainda vazio. Respostas, tarefas concluídas e novidades aparecerão aqui.'],
    allNews: ['All news', 'Все новости', 'Alle Neuigkeiten', 'Tüm haberler', 'Toutes les actualités', 'Усі новини', 'Todas las noticias', 'Todas as novidades'],
    loading: ['Loading…', 'Загрузка…', 'Wird geladen…', 'Yükleniyor…', 'Chargement…', 'Завантаження…', 'Cargando…', 'Carregando…'],
    failed: ['Could not load notifications.', 'Не удалось загрузить уведомления.', 'Benachrichtigungen konnten nicht geladen werden.', 'Bildirimler yüklenemedi.', 'Impossible de charger les notifications.', 'Не вдалося завантажити сповіщення.', 'No se pudieron cargar las notificaciones.', 'Não foi possível carregar as notificações.'],
    now: ['just now', 'только что', 'gerade eben', 'şimdi', 'à l’instant', 'щойно', 'ahora', 'agora'],
    min: ['{n} min ago', '{n} мин назад', 'vor {n} Min.', '{n} dk önce', 'il y a {n} min', '{n} хв тому', 'hace {n} min', 'há {n} min'],
    hour: ['{n} h ago', '{n} ч назад', 'vor {n} Std.', '{n} sa önce', 'il y a {n} h', '{n} год тому', 'hace {n} h', 'há {n} h'],
    day: ['{n} d ago', '{n} дн назад', 'vor {n} T.', '{n} gün önce', 'il y a {n} j', '{n} дн тому', 'hace {n} d', 'há {n} d'],
    fromTeam: ['From the ShowcaseMaker team', 'От команды ShowcaseMaker', 'Vom ShowcaseMaker-Team', 'ShowcaseMaker ekibinden', 'De l’équipe ShowcaseMaker', 'Від команди ShowcaseMaker', 'Del equipo de ShowcaseMaker', 'Da equipe ShowcaseMaker'],
    gotIt: ['Got it', 'Понятно', 'Verstanden', 'Anladım', 'Compris', 'Зрозуміло', 'Entendido', 'Entendi'],
    open: ['Open', 'Открыть', 'Öffnen', 'Aç', 'Ouvrir', 'Відкрити', 'Abrir', 'Abrir'],
    close: ['Close', 'Закрыть', 'Schließen', 'Kapat', 'Fermer', 'Закрити', 'Cerrar', 'Fechar']
  };
  var CATEGORY = {
    news: ['News', 'Новости', 'Neuigkeiten', 'Haberler', 'Actualités', 'Новини', 'Noticias', 'Novidades'],
    update: ['Update', 'Обновление', 'Update', 'Güncelleme', 'Mise à jour', 'Оновлення', 'Actualización', 'Atualização'],
    feature: ['New feature', 'Новая функция', 'Neue Funktion', 'Yeni özellik', 'Nouvelle fonction', 'Нова функція', 'Nueva función', 'Novo recurso'],
    announcement: ['Announcement', 'Анонс', 'Ankündigung', 'Duyuru', 'Annonce', 'Анонс', 'Anuncio', 'Anúncio'],
    event: ['Event', 'Событие', 'Event', 'Etkinlik', 'Événement', 'Подія', 'Evento', 'Evento'],
    maintenance: ['Maintenance', 'Техработы', 'Wartung', 'Bakım', 'Maintenance', 'Техроботи', 'Mantenimiento', 'Manutenção'],
    promo: ['Promo', 'Промо', 'Aktion', 'Promosyon', 'Promo', 'Промо', 'Promoción', 'Promoção']
  };
  var TOOL = {
    process: ['Process', 'Обработка', 'Verarbeitung', 'İşleme', 'Traitement', 'Обробка', 'Procesamiento', 'Processamento'],
    workshop_studio: ['Rows and squares', 'Ряды и квадраты', 'Reihen und Quadrate', 'Satırlar ve kareler', 'Rangées et carrés', 'Ряди та квадрати', 'Filas y cuadrados', 'Linhas e quadrados'],
    compose: ['Character', 'Персонаж', 'Charakter', 'Karakter', 'Personnage', 'Персонаж', 'Personaje', 'Personagem'],
    upscale: ['Upscale', 'Апскейл', 'Hochskalieren', 'Büyütme', 'Agrandissement', 'Апскейл', 'Ampliación', 'Ampliação'],
    seamless_loop: ['Loop', 'Цикл', 'Schleife', 'Döngü', 'Boucle', 'Цикл', 'Bucle', 'Loop'],
    steam_profile_import: ['Steam profile import', 'Импорт профиля Steam', 'Steam-Profilimport', 'Steam profili içe aktarma', 'Import du profil Steam', 'Імпорт профілю Steam', 'Importación del perfil de Steam', 'Importação do perfil Steam'],
    profile_insight: ['Profile rating', 'Оценка профиля', 'Profilbewertung', 'Profil değerlendirmesi', 'Évaluation du profil', 'Оцінка профілю', 'Valoración del perfil', 'Avaliação do perfil'],
    steam_dna: ['Steam DNA', 'Steam DNA', 'Steam DNA', 'Steam DNA', 'Steam DNA', 'Steam DNA', 'Steam DNA', 'Steam DNA'],
    ai_animate: ['AI animation', 'ИИ-анимация', 'KI-Animation', 'Yapay zekâ animasyonu', 'Animation IA', 'ШІ-анімація', 'Animación con IA', 'Animação com IA'],
    builder_bg_remove: ['Background removal', 'Удаление фона', 'Hintergrundentfernung', 'Arka plan kaldırma', 'Suppression du fond', 'Видалення тла', 'Quitar el fondo', 'Remoção de fundo']
  };
  var TEXT = {
    jobDone: ['{tool}: ready', '{tool}: готово', '{tool}: fertig', '{tool}: hazır', '{tool} : terminé', '{tool}: готово', '{tool}: listo', '{tool}: pronto'],
    jobDoneBody: ['Open the tool to download the result.', 'Открой инструмент, чтобы скачать результат.', 'Öffne das Werkzeug, um das Ergebnis herunterzuladen.', 'Sonucu indirmek için aracı aç.', 'Ouvrez l’outil pour télécharger le résultat.', 'Відкрий інструмент, щоб завантажити результат.', 'Abre la herramienta para descargar el resultado.', 'Abra a ferramenta para baixar o resultado.'],
    jobError: ['{tool}: did not work', '{tool}: не получилось', '{tool}: fehlgeschlagen', '{tool}: başarısız', '{tool} : échec', '{tool}: не вдалося', '{tool}: no se pudo', '{tool}: não deu certo'],
    like: ['{actor} liked your work', '{actor} оценил(а) твою работу', '{actor} gefällt deine Arbeit', '{actor} eserini beğendi', '{actor} a aimé votre œuvre', '{actor} оцінив(ла) твою роботу', 'A {actor} le gustó tu obra', '{actor} curtiu sua obra'],
    comment: ['{actor} commented on your work', '{actor} прокомментировал(а) твою работу', '{actor} hat deine Arbeit kommentiert', '{actor} eserine yorum yaptı', '{actor} a commenté votre œuvre', '{actor} прокоментував(ла) твою роботу', '{actor} comentó tu obra', '{actor} comentou sua obra'],
    reply: ['{actor} replied to your comment', '{actor} ответил(а) на твой комментарий', '{actor} hat auf deinen Kommentar geantwortet', '{actor} yorumuna yanıt verdi', '{actor} a répondu à votre commentaire', '{actor} відповів(ла) на твій коментар', '{actor} respondió a tu comentario', '{actor} respondeu ao seu comentário'],
    downloads: ['Your work was downloaded', 'Твою работу скачали', 'Deine Arbeit wurde heruntergeladen', 'Eserin indirildi', 'Votre œuvre a été téléchargée', 'Твою роботу завантажили', 'Descargaron tu obra', 'Sua obra foi baixada'],
    downloadsBody: ['“{work}”: {count} downloads in the last hours', '«{work}»: скачиваний за последние часы — {count}', '„{work}“: {count} Downloads in den letzten Stunden', '“{work}”: son saatlerde {count} indirme', '« {work} » : {count} téléchargements ces dernières heures', '«{work}»: завантажень за останні години — {count}', '«{work}»: {count} descargas en las últimas horas', '“{work}”: {count} downloads nas últimas horas'],
    support: ['Support replied to your request', 'Поддержка ответила на твоё обращение', 'Der Support hat auf deine Anfrage geantwortet', 'Destek talebine yanıt verdi', 'Le support a répondu à votre demande', 'Підтримка відповіла на твоє звернення', 'Soporte respondió a tu solicitud', 'O suporte respondeu à sua solicitação'],
    pro3d: ['Pro ends in 3 days', 'Pro закончится через 3 дня', 'Pro endet in 3 Tagen', 'Pro 3 gün içinde bitiyor', 'Pro se termine dans 3 jours', 'Pro закінчиться через 3 дні', 'Pro termina en 3 días', 'O Pro termina em 3 dias'],
    pro1d: ['Pro ends tomorrow', 'Pro закончится завтра', 'Pro endet morgen', 'Pro yarın bitiyor', 'Pro se termine demain', 'Pro закінчиться завтра', 'Pro termina mañana', 'O Pro termina amanhã'],
    pro15m: ['Pro ends in 15 minutes', 'Pro закончится через 15 минут', 'Pro endet in 15 Minuten', 'Pro 15 dakika içinde bitiyor', 'Pro se termine dans 15 minutes', 'Pro закінчиться через 15 хвилин', 'Pro termina en 15 minutos', 'O Pro termina em 15 minutos'],
    proBody: ['Renew it to keep working without limits.', 'Продли, чтобы работать без лимитов.', 'Verlängere es, um ohne Limits weiterzuarbeiten.', 'Sınırsız çalışmaya devam etmek için yenile.', 'Renouvelez-le pour continuer sans limites.', 'Продовж, щоб працювати без лімітів.', 'Renuévalo para seguir sin límites.', 'Renove para continuar sem limites.'],
    proBought: ['Pro is active, thank you!', 'Pro активирован, спасибо!', 'Pro ist aktiv, danke!', 'Pro etkin, teşekkürler!', 'Pro est actif, merci !', 'Pro активовано, дякуємо!', 'Pro está activo, ¡gracias!', 'O Pro está ativo, obrigado!'],
    proBoughtBody: ['Your purchase is linked to this account. All Pro tools are open.', 'Покупка привязана к этому аккаунту. Все инструменты Pro открыты.', 'Dein Kauf ist mit diesem Konto verknüpft. Alle Pro-Werkzeuge sind frei.', 'Satın alman bu hesaba bağlandı. Tüm Pro araçları açık.', 'Votre achat est lié à ce compte. Tous les outils Pro sont ouverts.', 'Покупку прив’язано до цього акаунта. Усі інструменти Pro відкрито.', 'Tu compra está vinculada a esta cuenta. Todas las herramientas Pro están abiertas.', 'Sua compra está vinculada a esta conta. Todas as ferramentas Pro estão liberadas.'],
    proEnded: ['Pro has ended', 'Pro закончился', 'Pro ist abgelaufen', 'Pro sona erdi', 'Pro est terminé', 'Pro закінчився', 'Pro ha terminado', 'O Pro terminou'],
    proEndedBody: ['The free plan is active again. Enter a new code to get Pro back.', 'Снова действует бесплатный тариф. Введи новый код, чтобы вернуть Pro.', 'Der kostenlose Tarif gilt wieder. Gib einen neuen Code ein, um Pro zurückzubekommen.', 'Ücretsiz plan yeniden etkin. Pro’yu geri almak için yeni kod gir.', 'L’offre gratuite est de nouveau active. Saisissez un nouveau code pour retrouver Pro.', 'Знову діє безкоштовний тариф. Введи новий код, щоб повернути Pro.', 'Vuelve el plan gratuito. Introduce un código nuevo para recuperar Pro.', 'O plano gratuito voltou. Digite um novo código para ter o Pro de volta.']
  };
  // Plain-language reasons for failed jobs, with what to do.
  var REASON = {
    steam_private: ['Your Steam profile is private. Open Steam → Edit profile → Privacy settings, set “My profile” to Public, then try again.', 'Профиль Steam закрыт. Открой Steam → Редактировать профиль → Приватность, поставь «Мой профиль: открытый» и попробуй снова.', 'Dein Steam-Profil ist privat. Öffne Steam → Profil bearbeiten → Privatsphäre, stelle „Mein Profil“ auf Öffentlich und versuche es erneut.', 'Steam profilin gizli. Steam → Profili düzenle → Gizlilik ayarlarında “Profilim”i Herkese açık yap ve tekrar dene.', 'Votre profil Steam est privé. Steam → Modifier le profil → Confidentialité : réglez « Mon profil » sur Public, puis réessayez.', 'Профіль Steam закритий. Відкрий Steam → Редагувати профіль → Приватність, постав «Мій профіль: відкритий» і спробуй знову.', 'Tu perfil de Steam es privado. Abre Steam → Editar perfil → Privacidad, pon «Mi perfil» en Público y vuelve a intentarlo.', 'Seu perfil Steam é privado. Abra Steam → Editar perfil → Privacidade, deixe “Meu perfil” como Público e tente de novo.'],
    steam_busy: ['Steam is limiting requests right now. Wait a few minutes and try again.', 'Steam сейчас ограничивает запросы. Подожди несколько минут и попробуй снова.', 'Steam begrenzt gerade Anfragen. Warte ein paar Minuten und versuche es erneut.', 'Steam şu an istekleri sınırlıyor. Birkaç dakika bekleyip tekrar dene.', 'Steam limite les requêtes en ce moment. Patientez quelques minutes et réessayez.', 'Steam зараз обмежує запити. Зачекай кілька хвилин і спробуй знову.', 'Steam está limitando las solicitudes ahora. Espera unos minutos y vuelve a intentarlo.', 'A Steam está limitando pedidos agora. Espere alguns minutos e tente de novo.'],
    steam_not_found: ['This Steam profile was not found. Check the link: it should look like steamcommunity.com/id/name or /profiles/7656…', 'Такой профиль Steam не найден. Проверь ссылку: она должна быть вида steamcommunity.com/id/имя или /profiles/7656…', 'Dieses Steam-Profil wurde nicht gefunden. Prüfe den Link: steamcommunity.com/id/name oder /profiles/7656…', 'Bu Steam profili bulunamadı. Bağlantıyı kontrol et: steamcommunity.com/id/ad veya /profiles/7656… olmalı.', 'Ce profil Steam est introuvable. Vérifiez le lien : steamcommunity.com/id/nom ou /profiles/7656…', 'Такий профіль Steam не знайдено. Перевір посилання: steamcommunity.com/id/ім’я або /profiles/7656…', 'No se encontró este perfil de Steam. Revisa el enlace: steamcommunity.com/id/nombre o /profiles/7656…', 'Esse perfil Steam não foi encontrado. Confira o link: steamcommunity.com/id/nome ou /profiles/7656…'],
    steam_unavailable: ['Steam did not give out the profile. Check that it is public and try again in a few minutes.', 'Steam не отдал профиль. Проверь, что он открытый, и попробуй через несколько минут.', 'Steam hat das Profil nicht geliefert. Prüfe, ob es öffentlich ist, und versuche es in ein paar Minuten erneut.', 'Steam profili vermedi. Herkese açık olduğundan emin ol ve birkaç dakika sonra tekrar dene.', 'Steam n’a pas fourni le profil. Vérifiez qu’il est public et réessayez dans quelques minutes.', 'Steam не віддав профіль. Перевір, що він відкритий, і спробуй за кілька хвилин.', 'Steam no entregó el perfil. Comprueba que sea público y vuelve a intentarlo en unos minutos.', 'A Steam não entregou o perfil. Confira se ele é público e tente de novo em alguns minutos.'],
    steam_limit: ['The result does not fit Steam’s 5 MB limit even at the lowest quality. Use a shorter clip, a lower frame rate or a calmer animation.', 'Результат не влезает в лимит Steam 5 МБ даже на минимальном качестве. Возьми фрагмент короче, поставь меньше кадров в секунду или выбери более спокойную анимацию.', 'Das Ergebnis passt selbst bei niedrigster Qualität nicht in Steams 5-MB-Limit. Nimm einen kürzeren Clip, weniger Bilder pro Sekunde oder eine ruhigere Animation.', 'Sonuç en düşük kalitede bile Steam’in 5 MB sınırına sığmıyor. Daha kısa bir parça, daha düşük kare hızı ya da daha sakin bir animasyon kullan.', 'Le résultat dépasse la limite Steam de 5 Mo même en qualité minimale. Prenez un extrait plus court, moins d’images par seconde ou une animation plus calme.', 'Результат не вміщується в ліміт Steam 5 МБ навіть на мінімальній якості. Візьми коротший фрагмент, менше кадрів за секунду або спокійнішу анімацію.', 'El resultado no cabe en el límite de 5 MB de Steam ni con la calidad mínima. Usa un fragmento más corto, menos fotogramas por segundo o una animación más tranquila.', 'O resultado não cabe no limite de 5 MB da Steam nem na qualidade mínima. Use um trecho mais curto, menos quadros por segundo ou uma animação mais calma.'],
    upload_limit: ['The file is too large. Make it smaller (shorter clip or lower resolution) and upload it again.', 'Файл слишком большой. Уменьши его (короче фрагмент или меньше разрешение) и загрузи снова.', 'Die Datei ist zu groß. Verkleinere sie (kürzerer Clip oder geringere Auflösung) und lade sie erneut hoch.', 'Dosya çok büyük. Küçült (daha kısa parça ya da düşük çözünürlük) ve tekrar yükle.', 'Le fichier est trop lourd. Réduisez-le (extrait plus court ou résolution plus basse) et renvoyez-le.', 'Файл завеликий. Зменш його (коротший фрагмент або менша роздільність) і завантаж знову.', 'El archivo es demasiado grande. Hazlo más pequeño (fragmento más corto o menor resolución) y súbelo de nuevo.', 'O arquivo é grande demais. Diminua (trecho mais curto ou resolução menor) e envie de novo.'],
    format: ['This file format is not supported. Use PNG, JPG, WebP, GIF, MP4 or WebM.', 'Этот формат не поддерживается. Используй PNG, JPG, WebP, GIF, MP4 или WebM.', 'Dieses Dateiformat wird nicht unterstützt. Verwende PNG, JPG, WebP, GIF, MP4 oder WebM.', 'Bu dosya biçimi desteklenmiyor. PNG, JPG, WebP, GIF, MP4 veya WebM kullan.', 'Ce format n’est pas pris en charge. Utilisez PNG, JPG, WebP, GIF, MP4 ou WebM.', 'Цей формат не підтримується. Використай PNG, JPG, WebP, GIF, MP4 або WebM.', 'Este formato no es compatible. Usa PNG, JPG, WebP, GIF, MP4 o WebM.', 'Esse formato não é suportado. Use PNG, JPG, WebP, GIF, MP4 ou WebM.'],
    animated_still: ['This picture is animated. Save it as GIF or MP4 and upload it again.', 'Эта картинка анимированная. Сохрани её как GIF или MP4 и загрузи снова.', 'Dieses Bild ist animiert. Speichere es als GIF oder MP4 und lade es erneut hoch.', 'Bu resim animasyonlu. GIF ya da MP4 olarak kaydedip tekrar yükle.', 'Cette image est animée. Enregistrez-la en GIF ou MP4 et renvoyez-la.', 'Ця картинка анімована. Збережи її як GIF або MP4 і завантаж знову.', 'Esta imagen es animada. Guárdala como GIF o MP4 y súbela de nuevo.', 'Essa imagem é animada. Salve como GIF ou MP4 e envie de novo.'],
    broken_file: ['The file is damaged or not fully downloaded. Open it on your computer, save it again and upload the new copy.', 'Файл повреждён или скачан не до конца. Открой его у себя, пересохрани и загрузи новую копию.', 'Die Datei ist beschädigt oder unvollständig. Öffne sie, speichere sie neu und lade die neue Kopie hoch.', 'Dosya bozuk ya da tam inmemiş. Bilgisayarında açıp yeniden kaydet ve yeni kopyayı yükle.', 'Le fichier est endommagé ou incomplet. Ouvrez-le, réenregistrez-le et envoyez la nouvelle copie.', 'Файл пошкоджений або завантажений не повністю. Відкрий його, перезбережи й завантаж нову копію.', 'El archivo está dañado o incompleto. Ábrelo, guárdalo de nuevo y sube la copia nueva.', 'O arquivo está danificado ou incompleto. Abra, salve de novo e envie a nova cópia.'],
    too_many_pixels: ['The picture is too large in pixels. Reduce it to about 8000 px on the longer side.', 'Картинка слишком большая по пикселям. Уменьши её примерно до 8000 px по длинной стороне.', 'Das Bild hat zu viele Pixel. Verkleinere es auf etwa 8000 px an der langen Seite.', 'Resmin piksel boyutu çok büyük. Uzun kenarı yaklaşık 8000 px olacak şekilde küçült.', 'L’image a trop de pixels. Réduisez-la à environ 8000 px sur le grand côté.', 'Картинка завелика в пікселях. Зменш її приблизно до 8000 px по довшій стороні.', 'La imagen tiene demasiados píxeles. Redúcela a unos 8000 px en el lado largo.', 'A imagem tem pixels demais. Reduza para cerca de 8000 px no lado maior.'],
    no_frames: ['The selected fragment is empty or too short. Choose a longer part of the video.', 'Выбранный фрагмент пустой или слишком короткий. Выбери более длинный кусок видео.', 'Der gewählte Ausschnitt ist leer oder zu kurz. Wähle einen längeren Teil des Videos.', 'Seçilen parça boş ya da çok kısa. Videonun daha uzun bir kısmını seç.', 'Le fragment choisi est vide ou trop court. Choisissez une partie plus longue de la vidéo.', 'Обраний фрагмент порожній або закороткий. Обери довший шматок відео.', 'El fragmento elegido está vacío o es demasiado corto. Elige una parte más larga del vídeo.', 'O trecho escolhido está vazio ou é curto demais. Escolha uma parte maior do vídeo.'],
    duration: ['The chosen length is outside the allowed range. Pick a shorter or longer fragment.', 'Выбранная длина вне допустимых границ. Выбери фрагмент короче или длиннее.', 'Die gewählte Länge liegt außerhalb des erlaubten Bereichs. Wähle einen kürzeren oder längeren Ausschnitt.', 'Seçilen süre izin verilen aralığın dışında. Daha kısa ya da uzun bir parça seç.', 'La durée choisie sort des limites. Choisissez un fragment plus court ou plus long.', 'Обрана довжина поза допустимими межами. Обери коротший або довший фрагмент.', 'La duración elegida está fuera del rango permitido. Elige un fragmento más corto o más largo.', 'A duração escolhida está fora do permitido. Escolha um trecho mais curto ou mais longo.'],
    no_source: ['The source file is no longer on the server. Add it again and restart.', 'Исходного файла уже нет на сервере. Добавь его заново и запусти ещё раз.', 'Die Quelldatei ist nicht mehr auf dem Server. Füge sie erneut hinzu und starte neu.', 'Kaynak dosya artık sunucuda değil. Yeniden ekleyip tekrar başlat.', 'Le fichier source n’est plus sur le serveur. Ajoutez-le de nouveau et relancez.', 'Вихідного файлу вже немає на сервері. Додай його знову й запусти ще раз.', 'El archivo original ya no está en el servidor. Añádelo de nuevo y vuelve a empezar.', 'O arquivo original não está mais no servidor. Adicione de novo e reinicie.'],
    gpu: ['The upscale service is busy or unavailable. Try again in a few minutes.', 'Сервис апскейла сейчас занят или недоступен. Попробуй через несколько минут.', 'Der Hochskalierungsdienst ist ausgelastet oder nicht erreichbar. Versuche es in ein paar Minuten erneut.', 'Büyütme hizmeti meşgul ya da kullanılamıyor. Birkaç dakika sonra tekrar dene.', 'Le service d’agrandissement est occupé ou indisponible. Réessayez dans quelques minutes.', 'Сервіс апскейлу зайнятий або недоступний. Спробуй за кілька хвилин.', 'El servicio de ampliación está ocupado o no disponible. Inténtalo en unos minutos.', 'O serviço de ampliação está ocupado ou indisponível. Tente em alguns minutos.'],
    bg_removal: ['Background removal is unavailable right now. Try again later or remove the background in another app.', 'Удаление фона сейчас недоступно. Попробуй позже или убери фон в другой программе.', 'Die Hintergrundentfernung ist gerade nicht verfügbar. Versuche es später oder entferne den Hintergrund in einer anderen App.', 'Arka plan kaldırma şu an kullanılamıyor. Sonra dene ya da başka bir uygulamada kaldır.', 'La suppression du fond est indisponible pour le moment. Réessayez plus tard ou utilisez une autre appli.', 'Видалення тла зараз недоступне. Спробуй пізніше або прибери тло в іншій програмі.', 'Quitar el fondo no está disponible ahora. Inténtalo más tarde o hazlo en otra app.', 'A remoção de fundo está indisponível agora. Tente mais tarde ou use outro app.'],
    loop: ['A loop could not be built from this fragment. Try another start or a fragment of 2–4 seconds.', 'Из этого фрагмента не получилось собрать цикл. Попробуй другое начало или фрагмент 2–4 секунды.', 'Aus diesem Ausschnitt ließ sich keine Schleife bauen. Versuche einen anderen Start oder 2–4 Sekunden.', 'Bu parçadan döngü yapılamadı. Başka bir başlangıç ya da 2–4 saniyelik parça dene.', 'Impossible de faire une boucle avec ce fragment. Essayez un autre début ou 2 à 4 secondes.', 'З цього фрагмента не вдалося зібрати цикл. Спробуй інший початок або фрагмент 2–4 секунди.', 'No se pudo crear un bucle con este fragmento. Prueba otro inicio o un fragmento de 2–4 segundos.', 'Não deu para montar um loop com esse trecho. Tente outro início ou um trecho de 2–4 segundos.'],
    server: ['Something went wrong on our side. Try again; if it repeats, write to support and we will fix it.', 'Что-то пошло не так на нашей стороне. Попробуй ещё раз; если повторится — напиши в поддержку, исправим.', 'Auf unserer Seite ist etwas schiefgelaufen. Versuche es erneut; wenn es wieder passiert, schreib dem Support.', 'Bizim tarafta bir sorun oluştu. Tekrar dene; yinelenirse desteğe yaz, düzeltelim.', 'Un problème est survenu de notre côté. Réessayez ; si cela se répète, écrivez au support.', 'Щось пішло не так на нашому боці. Спробуй ще раз; якщо повториться — напиши в підтримку.', 'Algo falló de nuestro lado. Inténtalo de nuevo; si se repite, escribe a soporte.', 'Algo deu errado do nosso lado. Tente de novo; se repetir, fale com o suporte.'],
    unknown: ['The job stopped with an error. Try again; if it repeats, write to support.', 'Задача остановилась с ошибкой. Попробуй ещё раз; если повторится — напиши в поддержку.', 'Der Auftrag wurde mit einem Fehler beendet. Versuche es erneut; wenn es wieder passiert, schreib dem Support.', 'İş bir hatayla durdu. Tekrar dene; yinelenirse desteğe yaz.', 'La tâche s’est arrêtée sur une erreur. Réessayez ; si cela se répète, écrivez au support.', 'Завдання зупинилося з помилкою. Спробуй ще раз; якщо повториться — напиши в підтримку.', 'La tarea se detuvo con un error. Inténtalo de nuevo; si se repite, escribe a soporte.', 'A tarefa parou com um erro. Tente de novo; se repetir, fale com o suporte.']
  };
  var ICON = { news: '📰', update: '✨', feature: '✨', announcement: '📣', event: '📅', maintenance: '🛠', promo: '🎁',
               support_reply: '💬', job_done: '⚙️', job_error: '❌', pro_expiring: '💎', pro_expired: '💎', pro_purchased: '💎',
               like: '❤️', comment: '💬', reply: '💬', downloads: '⬇️', admin_message: '✉️' };

  // Owner messages are written in Russian with an optional English copy: ru/uk read Russian,
  // everyone else English when it exists.
  function messageText(item) {
    var meta = item.meta || {}, en = meta.en;
    if (en && en.title && ['ru', 'uk'].indexOf(lang()) < 0) return { title: en.title, body: en.body || '' };
    return { title: item.title || '', body: item.body || '' };
  }

  function present(item) {
    var meta = item.meta || {}, tool = TOOL[meta.tool] ? L(TOOL[meta.tool]) : L(TOOL.process), kind = item.kind;
    var out = { icon: ICON[kind] || '🔔', label: '', title: item.title || '', body: item.body || '' };
    if (kind === 'news') {
      var cat = meta.category || item.category || 'news';
      out.icon = ICON[cat] || ICON.news; out.label = L(CATEGORY[cat] || CATEGORY.news);
    } else if (kind === 'job_done') { out.title = fmt(L(TEXT.jobDone), { tool: tool }); out.body = L(TEXT.jobDoneBody); }
    else if (kind === 'job_error') { out.title = fmt(L(TEXT.jobError), { tool: tool }); out.body = L(REASON[meta.code] || REASON.unknown); }
    else if (kind === 'like' || kind === 'comment' || kind === 'reply') { out.title = fmt(L(TEXT[kind]), { actor: item.actor || '—' }); out.body = lang() === 'ru' ? item.body : ''; }
    else if (kind === 'downloads') { out.title = L(TEXT.downloads); out.body = fmt(L(TEXT.downloadsBody), { work: meta.work || '—', count: meta.count || 1 }); }
    else if (kind === 'support_reply') { out.title = L(TEXT.support); }
    else if (kind === 'pro_expiring') { out.title = L(TEXT['pro' + (meta.stage || '3d')] || TEXT.pro3d); out.body = L(TEXT.proBody); }
    else if (kind === 'pro_purchased') { out.title = L(TEXT.proBought); out.body = L(TEXT.proBoughtBody); }
    else if (kind === 'pro_expired') { out.title = L(TEXT.proEnded); out.body = L(TEXT.proEndedBody); }
    else if (kind === 'admin_message') { var m = messageText(item); out.label = L(UI.fromTeam); out.title = m.title; out.body = m.body; }
    return out;
  }
  function ago(ts) {
    var s = Math.max(0, Date.now() / 1000 - Number(ts || 0));
    if (s < 60) return L(UI.now);
    if (s < 3600) return fmt(L(UI.min), { n: Math.floor(s / 60) });
    if (s < 86400) return fmt(L(UI.hour), { n: Math.floor(s / 3600) });
    return fmt(L(UI.day), { n: Math.floor(s / 86400) });
  }

  var root = document.getElementById('ssBell'), btn = document.getElementById('ssBellBtn'), panel = document.getElementById('ssBellPanel');
  if (!root || !btn || !panel) return;
  var items = [], open = false;

  function counters(data) {
    var me = Object.assign({}, window.SS_ME || {}, { logged_in: true, unread: data.unread, news_dot: data.news_dot });
    window.SS_ME = me;
    if (window.SSShell && SSShell.paintCounters) SSShell.paintCounters(me);
  }
  function api(path, options) {
    return fetch(path, Object.assign({ credentials: 'same-origin', cache: 'no-store' }, options || {})).then(function (r) { return r.json(); });
  }
  function render(state) {
    var head = '<header class="ss-bell__head"><b>' + esc(L(UI.title)) + '</b>' +
      (items.some(function (i) { return !i.is_read; }) ? '<button type="button" class="ss-bell__all" data-bell-all>' + esc(L(UI.readAll)) + '</button>' : '') + '</header>';
    var list;
    if (state) list = '<p class="ss-bell__state">' + esc(state) + '</p>';
    else if (!items.length) list = '<p class="ss-bell__state">' + esc(L(UI.empty)) + '</p>';
    else list = '<ul class="ss-bell__list">' + items.map(function (item, index) {
      var view = present(item);
      return '<li><a class="ss-bell__item' + (item.is_read ? '' : ' is-unread') + '" href="' + esc(url(item.link || '/news')) + '" data-bell-item="' + index + '">' +
        '<span class="ss-bell__icon" aria-hidden="true">' + view.icon + '</span><span class="ss-bell__text">' +
        (view.label ? '<small class="ss-bell__label">' + esc(view.label) + '</small>' : '') +
        '<b>' + esc(view.title) + '</b>' + (view.body ? '<span>' + esc(view.body) + '</span>' : '') +
        '<time>' + esc(ago(item.created_at)) + '</time></span></a></li>';
    }).join('') + '</ul>';
    panel.innerHTML = head + list + '<footer class="ss-bell__foot"><a href="' + esc(url('/news')) + '">' + esc(L(UI.allNews)) + ' →</a></footer>';
  }
  function load() {
    render(L(UI.loading));
    return api('/api/notifications?limit=30&lang=' + encodeURIComponent(lang())).then(function (data) {
      if (!data || !data.ok) throw new Error('bell');
      items = data.items || []; counters(data); render();
    }).catch(function () { render(L(UI.failed)); });
  }
  function setOpen(value) {
    open = value; panel.hidden = !value; btn.setAttribute('aria-expanded', String(value)); root.classList.toggle('is-open', value);
    if (value) { document.dispatchEvent(new CustomEvent('ss:menu-open', { detail: 'bell' })); load(); }
  }
  function markRead(ids, all) {
    return api('/api/notifications/read', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(all ? { all: true } : { ids: ids }) }).then(function (data) { if (data && data.ok) counters(data); }).catch(function () {});
  }
  btn.addEventListener('click', function (event) { event.stopPropagation(); setOpen(!open); });
  document.addEventListener('click', function (event) { if (open && !root.contains(event.target)) setOpen(false); });
  document.addEventListener('keydown', function (event) { if (event.key === 'Escape' && open) { setOpen(false); btn.focus(); } });
  document.addEventListener('ss:menu-open', function (event) { if (event.detail !== 'bell' && open) setOpen(false); });
  panel.addEventListener('click', function (event) {
    var all = event.target.closest('[data-bell-all]');
    if (all) { event.preventDefault(); items.forEach(function (i) { i.is_read = true; }); render(); markRead(null, true); return; }
    var link = event.target.closest('[data-bell-item]');
    if (!link) return;
    var item = items[Number(link.dataset.bellItem)];
    if (item && item.kind === 'admin_message') { event.preventDefault(); setOpen(false); showMessage(item); return; }
    if (item && !item.is_read) {
      event.preventDefault(); item.is_read = true;
      markRead([item.id]).then(function () { location.href = link.href; });
    }
  });

  // Owner message window. Text is plain (line breaks kept); the only link is the message's own.
  var shown = {}, msgBox = null;
  function onMsgKey(event) { if (event.key === 'Escape') { event.preventDefault(); closeMessage(); } }
  function closeMessage() {
    if (!msgBox) return;
    msgBox.remove(); msgBox = null; document.removeEventListener('keydown', onMsgKey);
  }
  function showMessage(item) {
    if (!item || msgBox) return;
    shown[item.id] = true;
    var view = messageText(item), external = /^https:/i.test(item.link || '');
    var href = item.link ? (external ? item.link : url(item.link)) : '';
    msgBox = document.createElement('div');
    msgBox.className = 'sm-msg';
    msgBox.innerHTML = '<div class="sm-msg__backdrop" data-msg-close></div>' +
      '<section class="sm-msg__card" role="dialog" aria-modal="true" aria-labelledby="smMsgTitle">' +
      '<button type="button" class="sm-msg__x" data-msg-close aria-label="' + esc(L(UI.close)) + '">×</button>' +
      '<p class="sm-msg__from"><span aria-hidden="true">✉️</span>' + esc(L(UI.fromTeam)) + '</p>' +
      '<h2 id="smMsgTitle">' + esc(view.title) + '</h2>' + (view.body ? '<p class="sm-msg__body">' + esc(view.body) + '</p>' : '') +
      '<div class="sm-msg__actions">' +
      (href ? '<a class="sm-msg__go" data-msg-close href="' + esc(href) + '"' + (external ? ' target="_blank" rel="noopener"' : '') + '>' + esc(L(UI.open)) + '</a>' : '') +
      '<button type="button" class="sm-msg__ok" data-msg-close>' + esc(L(UI.gotIt)) + '</button></div></section>';
    document.body.appendChild(msgBox);
    msgBox.addEventListener('click', function (event) { if (event.target.closest('[data-msg-close]')) closeMessage(); });
    document.addEventListener('keydown', onMsgKey);
    var ok = msgBox.querySelector('.sm-msg__ok');
    if (ok) ok.focus({ preventScroll: true });
    if (!item.is_read) { item.is_read = true; markRead([item.id]); }
  }

  // Quiet poll of the counters while the tab is visible; it also brings owner messages.
  function poll() {
    if (document.hidden) return;
    api('/api/notifications/unread').then(function (data) {
      if (!data || !data.ok || !data.logged_in) return;
      counters(data);
      if (data.popup && !shown[data.popup.id]) showMessage(data.popup);
    }).catch(function () {});
  }
  setTimeout(poll, 1200);
  setInterval(poll, 60000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
  window.SMBell = { reload: load, poll: poll, present: present, showMessage: showMessage };
})();
