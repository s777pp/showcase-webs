/* /<lang>/account: the site account (2026-10-06, owner reference: steamprofile.io account screen).
   One request (/api/account/overview) feeds every card: plan + Pro time, today's files, Pro tools,
   sign-in methods, purchases, recent saved results, support, and the settings (nickname, password;
   export / delete come from account-controls.js, mounted into #accountContent).
   Buy / extend / key buttons open the shell's purchase dialog (pro-plans.js). */
(function () {
  'use strict';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { publicHint: 'The page with your showcases and works that everyone can see.', kicker: 'Account', navOverview: 'Overview', navSecurity: 'Sign-in and security', navData: 'Your data', daysLabel: 'days left', hoursLabel: 'hours left', foreverLabel: 'no end date', freePerDay: 'files a day', upgradeTitle: 'What Pro adds', choosePlan: 'Choose a plan', connected: 'Connected', dataText: 'Download a copy of everything we store about you, or delete the account for good.', resultsHint: 'Finished ZIPs from the tools stay here for 30 days.', purchasesHint: 'Plans bought with a card or PayPal and the keys you entered.', securityHint: 'How you sign in and the name others see.', statusHint: 'Your plan and today’s usage.', helpTitle: 'Need help?', statusTitle: 'Account status', planLabel: 'Current plan', free: 'Free', pro: 'Pro', forever: 'Pro forever', trial: 'Pro trial', until: 'until {date}', daysLeft: '{n} days left', lastDay: 'less than a day left', foreverNote: 'No end date', freeNote: 'Basic plan with a daily file limit', filesToday: 'Files today', unlimited: 'No limit', ofLimit: 'of {limit} · resets every day', results: 'Saved results', resultsNote: 'Finished ZIPs are kept for 30 days', proTools: 'Pro tools', tUpscale: 'Upscale', tLoop: 'Loop', tDesign: 'Design Selection', tCheck: 'Steam check', tMark: 'No watermark', buy: 'Buy Pro', extend: 'Extend Pro', haveKey: 'Enter a key', supportTitle: 'Support', supportText: 'Write to us and follow the replies in the support center.', supportBtn: 'Open the support center', purchasesTitle: 'Purchases', purchasesEmpty: 'No purchases yet.', srcGumroad: 'Card / PayPal', srcKey: 'Access key', srcTrial: 'Trial code', srcLicense: 'Gumroad license', stGranted: 'Active', stRefunded: 'Refunded', stPending: 'Not linked', loginTitle: 'Sign-in methods', emailLogin: 'Email', notLinked: 'not linked', settingsTitle: 'Account settings', nick: 'Nickname', saveNick: 'Save nickname', saving: 'Saving…', saved: 'Nickname saved', passTitle: 'Change password', curPass: 'Current password', newPass: 'New password', repeatPass: 'Repeat new password', changePass: 'Change password', fill: 'Fill in all password fields', match: 'New passwords do not match', short: 'Use at least 10 characters', changing: 'Changing password…', changed: 'Password changed', noPassword: 'You sign in without a password, so there is nothing to change here.', publicProfile: 'Public profile', logout: 'Log out', recentTitle: 'Recent results', recentEmpty: 'Your finished showcases will appear here.', openTools: 'Open the tools', download: 'Download', guestTitle: 'Your account', guestText: 'Log in to see your plan, purchases and settings.', login: 'Log in', register: 'Create an account', memberSince: 'With us since {date}', gallery: 'Gallery works', showcases: 'Profile showcases', error: 'Could not load the account. Try again.', retry: 'Retry', failed: 'Something went wrong', d1: '24 hours', d7: '7 days', d30: '30 days', d90: '90 days', life: 'Forever' },
    ru: { publicHint: 'Страница с твоими витринами и работами, которую видят все.', kicker: 'Аккаунт', navOverview: 'Обзор', navSecurity: 'Вход и безопасность', navData: 'Твои данные', daysLabel: 'дней осталось', hoursLabel: 'часов осталось', foreverLabel: 'без срока', freePerDay: 'файлов в день', upgradeTitle: 'Что даёт Pro', choosePlan: 'Выбрать тариф', connected: 'Подключено', dataText: 'Скачай копию всего, что мы храним о тебе, или удали аккаунт навсегда.', resultsHint: 'Готовые ZIP из инструментов хранятся здесь 30 дней.', purchasesHint: 'Тарифы, купленные картой или PayPal, и введённые ключи.', securityHint: 'Как ты входишь и какое имя видят другие.', statusHint: 'Твой тариф и сегодняшние лимиты.', helpTitle: 'Нужна помощь?', statusTitle: 'Статус аккаунта', planLabel: 'Текущий тариф', free: 'Free', pro: 'Pro', forever: 'Pro навсегда', trial: 'Пробный Pro', until: 'до {date}', daysLeft: 'осталось {n} дн.', lastDay: 'осталось меньше суток', foreverNote: 'Без срока окончания', freeNote: 'Базовый тариф с дневным лимитом файлов', filesToday: 'Файлы сегодня', unlimited: 'Без лимита', ofLimit: 'из {limit} · обновляется каждый день', results: 'Сохранённые результаты', resultsNote: 'Готовые ZIP хранятся 30 дней', proTools: 'Инструменты Pro', tUpscale: 'Апскейл', tLoop: 'Зациклить', tDesign: 'Подбор оформления', tCheck: 'Проверка Steam', tMark: 'Без водяного знака', buy: 'Купить Pro', extend: 'Продлить Pro', haveKey: 'Ввести ключ', supportTitle: 'Поддержка', supportText: 'Создавай обращения и следи за ответами в центре поддержки.', supportBtn: 'Перейти в центр поддержки', purchasesTitle: 'Покупки', purchasesEmpty: 'Покупок пока нет.', srcGumroad: 'Карта / PayPal', srcKey: 'Ключ доступа', srcTrial: 'Пробный код', srcLicense: 'Лицензия Gumroad', stGranted: 'Активна', stRefunded: 'Возврат', stPending: 'Не привязана', loginTitle: 'Способы входа', emailLogin: 'Почта', notLinked: 'не привязан', settingsTitle: 'Настройки аккаунта', nick: 'Ник', saveNick: 'Сохранить ник', saving: 'Сохраняем…', saved: 'Ник сохранён', passTitle: 'Смена пароля', curPass: 'Текущий пароль', newPass: 'Новый пароль', repeatPass: 'Повтори новый пароль', changePass: 'Изменить пароль', fill: 'Заполни все поля пароля', match: 'Новые пароли не совпадают', short: 'Минимум 10 символов', changing: 'Меняем пароль…', changed: 'Пароль изменён', noPassword: 'Ты входишь без пароля, поэтому менять здесь нечего.', publicProfile: 'Публичный профиль', logout: 'Выйти', recentTitle: 'Последние результаты', recentEmpty: 'Здесь появятся твои готовые витрины.', openTools: 'Открыть инструменты', download: 'Скачать', guestTitle: 'Твой аккаунт', guestText: 'Войди, чтобы увидеть тариф, покупки и настройки.', login: 'Войти', register: 'Создать аккаунт', memberSince: 'С нами с {date}', gallery: 'Работ в галерее', showcases: 'Витрин в профиле', error: 'Не удалось загрузить аккаунт. Попробуй ещё раз.', retry: 'Повторить', failed: 'Что-то пошло не так', d1: '24 часа', d7: '7 дней', d30: '30 дней', d90: '90 дней', life: 'Навсегда' },
    de: { publicHint: 'Die Seite mit deinen Vitrinen und Werken, die alle sehen können.', kicker: 'Konto', navOverview: 'Übersicht', navSecurity: 'Anmeldung und Sicherheit', navData: 'Deine Daten', daysLabel: 'Tage übrig', hoursLabel: 'Stunden übrig', foreverLabel: 'ohne Enddatum', freePerDay: 'Dateien pro Tag', upgradeTitle: 'Was Pro bietet', choosePlan: 'Tarif wählen', connected: 'Verbunden', dataText: 'Lade eine Kopie aller Daten herunter, die wir über dich speichern, oder lösche das Konto endgültig.', resultsHint: 'Fertige ZIPs aus den Werkzeugen bleiben hier 30 Tage.', purchasesHint: 'Mit Karte oder PayPal gekaufte Tarife und eingegebene Schlüssel.', securityHint: 'Wie du dich anmeldest und welchen Namen andere sehen.', statusHint: 'Dein Tarif und die heutige Nutzung.', helpTitle: 'Brauchst du Hilfe?', statusTitle: 'Kontostatus', planLabel: 'Aktueller Tarif', free: 'Free', pro: 'Pro', forever: 'Pro für immer', trial: 'Pro-Test', until: 'bis {date}', daysLeft: 'noch {n} Tage', lastDay: 'weniger als ein Tag übrig', foreverNote: 'Ohne Enddatum', freeNote: 'Basistarif mit täglichem Dateilimit', filesToday: 'Dateien heute', unlimited: 'Kein Limit', ofLimit: 'von {limit} · setzt sich täglich zurück', results: 'Gespeicherte Ergebnisse', resultsNote: 'Fertige ZIPs bleiben 30 Tage', proTools: 'Pro-Werkzeuge', tUpscale: 'Upscale', tLoop: 'Loop', tDesign: 'Designauswahl', tCheck: 'Steam-Prüfung', tMark: 'Kein Wasserzeichen', buy: 'Pro kaufen', extend: 'Pro verlängern', haveKey: 'Schlüssel eingeben', supportTitle: 'Support', supportText: 'Schreib uns und verfolge die Antworten im Support-Center.', supportBtn: 'Zum Support-Center', purchasesTitle: 'Käufe', purchasesEmpty: 'Noch keine Käufe.', srcGumroad: 'Karte / PayPal', srcKey: 'Zugangsschlüssel', srcTrial: 'Testcode', srcLicense: 'Gumroad-Lizenz', stGranted: 'Aktiv', stRefunded: 'Erstattet', stPending: 'Nicht verknüpft', loginTitle: 'Anmeldemethoden', emailLogin: 'E-Mail', notLinked: 'nicht verknüpft', settingsTitle: 'Kontoeinstellungen', nick: 'Nickname', saveNick: 'Nickname speichern', saving: 'Wird gespeichert…', saved: 'Nickname gespeichert', passTitle: 'Passwort ändern', curPass: 'Aktuelles Passwort', newPass: 'Neues Passwort', repeatPass: 'Neues Passwort wiederholen', changePass: 'Passwort ändern', fill: 'Fülle alle Passwortfelder aus', match: 'Die neuen Passwörter stimmen nicht überein', short: 'Mindestens 10 Zeichen', changing: 'Passwort wird geändert…', changed: 'Passwort geändert', noPassword: 'Du meldest dich ohne Passwort an, hier gibt es nichts zu ändern.', publicProfile: 'Öffentliches Profil', logout: 'Abmelden', recentTitle: 'Letzte Ergebnisse', recentEmpty: 'Hier erscheinen deine fertigen Vitrinen.', openTools: 'Werkzeuge öffnen', download: 'Herunterladen', guestTitle: 'Dein Konto', guestText: 'Melde dich an, um Tarif, Käufe und Einstellungen zu sehen.', login: 'Anmelden', register: 'Konto erstellen', memberSince: 'Dabei seit {date}', gallery: 'Galeriewerke', showcases: 'Profilvitrinen', error: 'Das Konto konnte nicht geladen werden. Versuche es erneut.', retry: 'Erneut versuchen', failed: 'Etwas ist schiefgelaufen', d1: '24 Stunden', d7: '7 Tage', d30: '30 Tage', d90: '90 Tage', life: 'Für immer' },
    tr: { publicHint: 'Herkesin görebildiği vitrinlerinin ve çalışmalarının sayfası.', kicker: 'Hesap', navOverview: 'Genel bakış', navSecurity: 'Giriş ve güvenlik', navData: 'Verilerin', daysLabel: 'gün kaldı', hoursLabel: 'saat kaldı', foreverLabel: 'bitiş tarihi yok', freePerDay: 'günde dosya', upgradeTitle: 'Pro neler sunar', choosePlan: 'Plan seç', connected: 'Bağlı', dataText: 'Hakkında sakladığımız her şeyin bir kopyasını indir ya da hesabı kalıcı olarak sil.', resultsHint: 'Araçlardan çıkan hazır ZIP’ler burada 30 gün kalır.', purchasesHint: 'Kart veya PayPal ile alınan planlar ve girdiğin anahtarlar.', securityHint: 'Nasıl giriş yaptığın ve başkalarının gördüğü ad.', statusHint: 'Planın ve bugünkü kullanımın.', helpTitle: 'Yardım mı lazım?', statusTitle: 'Hesap durumu', planLabel: 'Mevcut plan', free: 'Free', pro: 'Pro', forever: 'Süresiz Pro', trial: 'Pro deneme', until: '{date} tarihine kadar', daysLeft: '{n} gün kaldı', lastDay: 'bir günden az kaldı', foreverNote: 'Bitiş tarihi yok', freeNote: 'Günlük dosya sınırlı temel plan', filesToday: 'Bugünkü dosyalar', unlimited: 'Sınırsız', ofLimit: '{limit} içinden · her gün sıfırlanır', results: 'Kayıtlı sonuçlar', resultsNote: 'Hazır ZIP’ler 30 gün saklanır', proTools: 'Pro araçları', tUpscale: 'Upscale', tLoop: 'Döngü', tDesign: 'Tasarım Seçimi', tCheck: 'Steam kontrolü', tMark: 'Filigransız', buy: 'Pro satın al', extend: 'Pro’yu uzat', haveKey: 'Anahtar gir', supportTitle: 'Destek', supportText: 'Bize yaz ve yanıtları destek merkezinde takip et.', supportBtn: 'Destek merkezine git', purchasesTitle: 'Satın alımlar', purchasesEmpty: 'Henüz satın alım yok.', srcGumroad: 'Kart / PayPal', srcKey: 'Erişim anahtarı', srcTrial: 'Deneme kodu', srcLicense: 'Gumroad lisansı', stGranted: 'Etkin', stRefunded: 'İade edildi', stPending: 'Bağlı değil', loginTitle: 'Giriş yöntemleri', emailLogin: 'E-posta', notLinked: 'bağlı değil', settingsTitle: 'Hesap ayarları', nick: 'Takma ad', saveNick: 'Takma adı kaydet', saving: 'Kaydediliyor…', saved: 'Takma ad kaydedildi', passTitle: 'Şifre değiştir', curPass: 'Mevcut şifre', newPass: 'Yeni şifre', repeatPass: 'Yeni şifreyi tekrarla', changePass: 'Şifreyi değiştir', fill: 'Tüm şifre alanlarını doldur', match: 'Yeni şifreler eşleşmiyor', short: 'En az 10 karakter', changing: 'Şifre değiştiriliyor…', changed: 'Şifre değiştirildi', noPassword: 'Şifresiz giriş yapıyorsun, burada değiştirilecek bir şey yok.', publicProfile: 'Herkese açık profil', logout: 'Çıkış yap', recentTitle: 'Son sonuçlar', recentEmpty: 'Hazır vitrinlerin burada görünecek.', openTools: 'Araçları aç', download: 'İndir', guestTitle: 'Hesabın', guestText: 'Planını, satın alımlarını ve ayarlarını görmek için giriş yap.', login: 'Giriş yap', register: 'Hesap oluştur', memberSince: '{date} tarihinden beri bizimle', gallery: 'Galeri çalışmaları', showcases: 'Profil vitrinleri', error: 'Hesap yüklenemedi. Tekrar dene.', retry: 'Tekrar dene', failed: 'Bir şeyler ters gitti', d1: '24 saat', d7: '7 gün', d30: '30 gün', d90: '90 gün', life: 'Süresiz' },
    fr: { publicHint: 'La page de vos vitrines et œuvres, visible par tous.', kicker: 'Compte', navOverview: 'Vue d’ensemble', navSecurity: 'Connexion et sécurité', navData: 'Vos données', daysLabel: 'jours restants', hoursLabel: 'heures restantes', foreverLabel: 'sans date de fin', freePerDay: 'fichiers par jour', upgradeTitle: 'Ce qu’apporte Pro', choosePlan: 'Choisir une offre', connected: 'Connecté', dataText: 'Téléchargez une copie de tout ce que nous conservons sur vous, ou supprimez le compte définitivement.', resultsHint: 'Les ZIP terminés des outils restent ici 30 jours.', purchasesHint: 'Offres achetées par carte ou PayPal et clés saisies.', securityHint: 'Comment vous vous connectez et le nom que les autres voient.', statusHint: 'Votre offre et l’utilisation du jour.', helpTitle: 'Besoin d’aide ?', statusTitle: 'État du compte', planLabel: 'Offre actuelle', free: 'Free', pro: 'Pro', forever: 'Pro à vie', trial: 'Essai Pro', until: 'jusqu’au {date}', daysLeft: 'encore {n} jours', lastDay: 'moins d’un jour restant', foreverNote: 'Sans date de fin', freeNote: 'Offre de base avec une limite quotidienne de fichiers', filesToday: 'Fichiers aujourd’hui', unlimited: 'Sans limite', ofLimit: 'sur {limit} · remis à zéro chaque jour', results: 'Résultats enregistrés', resultsNote: 'Les ZIP terminés sont gardés 30 jours', proTools: 'Outils Pro', tUpscale: 'Upscale', tLoop: 'Boucle', tDesign: 'Sélection de design', tCheck: 'Vérification Steam', tMark: 'Sans filigrane', buy: 'Acheter Pro', extend: 'Prolonger Pro', haveKey: 'Saisir une clé', supportTitle: 'Support', supportText: 'Écrivez-nous et suivez les réponses dans le centre d’assistance.', supportBtn: 'Ouvrir le centre d’assistance', purchasesTitle: 'Achats', purchasesEmpty: 'Aucun achat pour l’instant.', srcGumroad: 'Carte / PayPal', srcKey: 'Clé d’accès', srcTrial: 'Code d’essai', srcLicense: 'Licence Gumroad', stGranted: 'Actif', stRefunded: 'Remboursé', stPending: 'Non rattaché', loginTitle: 'Moyens de connexion', emailLogin: 'E-mail', notLinked: 'non lié', settingsTitle: 'Paramètres du compte', nick: 'Pseudo', saveNick: 'Enregistrer le pseudo', saving: 'Enregistrement…', saved: 'Pseudo enregistré', passTitle: 'Changer le mot de passe', curPass: 'Mot de passe actuel', newPass: 'Nouveau mot de passe', repeatPass: 'Répéter le nouveau mot de passe', changePass: 'Changer le mot de passe', fill: 'Remplissez tous les champs du mot de passe', match: 'Les nouveaux mots de passe ne correspondent pas', short: 'Au moins 10 caractères', changing: 'Changement du mot de passe…', changed: 'Mot de passe changé', noPassword: 'Vous vous connectez sans mot de passe : rien à changer ici.', publicProfile: 'Profil public', logout: 'Se déconnecter', recentTitle: 'Derniers résultats', recentEmpty: 'Vos vitrines terminées apparaîtront ici.', openTools: 'Ouvrir les outils', download: 'Télécharger', guestTitle: 'Votre compte', guestText: 'Connectez-vous pour voir votre offre, vos achats et vos paramètres.', login: 'Se connecter', register: 'Créer un compte', memberSince: 'Avec nous depuis le {date}', gallery: 'Œuvres de la galerie', showcases: 'Vitrines du profil', error: 'Impossible de charger le compte. Réessayez.', retry: 'Réessayer', failed: 'Une erreur est survenue', d1: '24 heures', d7: '7 jours', d30: '30 jours', d90: '90 jours', life: 'À vie' },
    uk: { publicHint: 'Сторінка з твоїми вітринами й роботами, яку бачать усі.', kicker: 'Акаунт', navOverview: 'Огляд', navSecurity: 'Вхід і безпека', navData: 'Твої дані', daysLabel: 'днів лишилося', hoursLabel: 'годин лишилося', foreverLabel: 'без терміну', freePerDay: 'файлів на день', upgradeTitle: 'Що дає Pro', choosePlan: 'Обрати тариф', connected: 'Підключено', dataText: 'Завантаж копію всього, що ми зберігаємо про тебе, або видали акаунт назавжди.', resultsHint: 'Готові ZIP з інструментів зберігаються тут 30 днів.', purchasesHint: 'Тарифи, куплені карткою чи PayPal, і введені ключі.', securityHint: 'Як ти входиш і яке ім’я бачать інші.', statusHint: 'Твій тариф і сьогоднішні ліміти.', helpTitle: 'Потрібна допомога?', statusTitle: 'Статус акаунта', planLabel: 'Поточний тариф', free: 'Free', pro: 'Pro', forever: 'Pro назавжди', trial: 'Пробний Pro', until: 'до {date}', daysLeft: 'лишилося {n} дн.', lastDay: 'лишилося менше доби', foreverNote: 'Без дати завершення', freeNote: 'Базовий тариф із денним лімітом файлів', filesToday: 'Файли сьогодні', unlimited: 'Без ліміту', ofLimit: 'з {limit} · оновлюється щодня', results: 'Збережені результати', resultsNote: 'Готові ZIP зберігаються 30 днів', proTools: 'Інструменти Pro', tUpscale: 'Апскейл', tLoop: 'Зациклити', tDesign: 'Підбір оформлення', tCheck: 'Перевірка Steam', tMark: 'Без водяного знака', buy: 'Купити Pro', extend: 'Продовжити Pro', haveKey: 'Ввести ключ', supportTitle: 'Підтримка', supportText: 'Створюй звернення й стеж за відповідями в центрі підтримки.', supportBtn: 'Перейти до центру підтримки', purchasesTitle: 'Покупки', purchasesEmpty: 'Покупок поки немає.', srcGumroad: 'Картка / PayPal', srcKey: 'Ключ доступу', srcTrial: 'Пробний код', srcLicense: 'Ліцензія Gumroad', stGranted: 'Активна', stRefunded: 'Повернення', stPending: 'Не прив’язана', loginTitle: 'Способи входу', emailLogin: 'Пошта', notLinked: 'не прив’язано', settingsTitle: 'Налаштування акаунта', nick: 'Нік', saveNick: 'Зберегти нік', saving: 'Зберігаємо…', saved: 'Нік збережено', passTitle: 'Зміна пароля', curPass: 'Поточний пароль', newPass: 'Новий пароль', repeatPass: 'Повтори новий пароль', changePass: 'Змінити пароль', fill: 'Заповни всі поля пароля', match: 'Нові паролі не збігаються', short: 'Щонайменше 10 символів', changing: 'Змінюємо пароль…', changed: 'Пароль змінено', noPassword: 'Ти входиш без пароля, тож змінювати тут нічого.', publicProfile: 'Публічний профіль', logout: 'Вийти', recentTitle: 'Останні результати', recentEmpty: 'Тут з’являться твої готові вітрини.', openTools: 'Відкрити інструменти', download: 'Завантажити', guestTitle: 'Твій акаунт', guestText: 'Увійди, щоб побачити тариф, покупки та налаштування.', login: 'Увійти', register: 'Створити акаунт', memberSince: 'З нами з {date}', gallery: 'Робіт у галереї', showcases: 'Вітрин у профілі', error: 'Не вдалося завантажити акаунт. Спробуй ще раз.', retry: 'Повторити', failed: 'Щось пішло не так', d1: '24 години', d7: '7 днів', d30: '30 днів', d90: '90 днів', life: 'Назавжди' },
    es: { publicHint: 'La página con tus escaparates y obras que todo el mundo puede ver.', kicker: 'Cuenta', navOverview: 'Resumen', navSecurity: 'Acceso y seguridad', navData: 'Tus datos', daysLabel: 'días restantes', hoursLabel: 'horas restantes', foreverLabel: 'sin fecha de fin', freePerDay: 'archivos al día', upgradeTitle: 'Qué añade Pro', choosePlan: 'Elegir un plan', connected: 'Conectado', dataText: 'Descarga una copia de todo lo que guardamos sobre ti o elimina la cuenta para siempre.', resultsHint: 'Los ZIP terminados de las herramientas se guardan aquí 30 días.', purchasesHint: 'Planes comprados con tarjeta o PayPal y claves introducidas.', securityHint: 'Cómo accedes y el nombre que ven los demás.', statusHint: 'Tu plan y el uso de hoy.', helpTitle: '¿Necesitas ayuda?', statusTitle: 'Estado de la cuenta', planLabel: 'Plan actual', free: 'Free', pro: 'Pro', forever: 'Pro para siempre', trial: 'Prueba de Pro', until: 'hasta el {date}', daysLeft: 'quedan {n} días', lastDay: 'queda menos de un día', foreverNote: 'Sin fecha de fin', freeNote: 'Plan básico con límite diario de archivos', filesToday: 'Archivos hoy', unlimited: 'Sin límite', ofLimit: 'de {limit} · se reinicia cada día', results: 'Resultados guardados', resultsNote: 'Los ZIP terminados se guardan 30 días', proTools: 'Herramientas Pro', tUpscale: 'Upscale', tLoop: 'Bucle', tDesign: 'Selección de diseño', tCheck: 'Comprobación de Steam', tMark: 'Sin marca de agua', buy: 'Comprar Pro', extend: 'Ampliar Pro', haveKey: 'Introducir una clave', supportTitle: 'Soporte', supportText: 'Escríbenos y sigue las respuestas en el centro de soporte.', supportBtn: 'Ir al centro de soporte', purchasesTitle: 'Compras', purchasesEmpty: 'Aún no hay compras.', srcGumroad: 'Tarjeta / PayPal', srcKey: 'Clave de acceso', srcTrial: 'Código de prueba', srcLicense: 'Licencia de Gumroad', stGranted: 'Activa', stRefunded: 'Reembolsada', stPending: 'Sin vincular', loginTitle: 'Formas de acceso', emailLogin: 'Correo', notLinked: 'sin vincular', settingsTitle: 'Ajustes de la cuenta', nick: 'Apodo', saveNick: 'Guardar apodo', saving: 'Guardando…', saved: 'Apodo guardado', passTitle: 'Cambiar contraseña', curPass: 'Contraseña actual', newPass: 'Nueva contraseña', repeatPass: 'Repite la nueva contraseña', changePass: 'Cambiar contraseña', fill: 'Rellena todos los campos de contraseña', match: 'Las nuevas contraseñas no coinciden', short: 'Al menos 10 caracteres', changing: 'Cambiando la contraseña…', changed: 'Contraseña cambiada', noPassword: 'Entras sin contraseña, así que aquí no hay nada que cambiar.', publicProfile: 'Perfil público', logout: 'Cerrar sesión', recentTitle: 'Últimos resultados', recentEmpty: 'Aquí aparecerán tus escaparates terminados.', openTools: 'Abrir las herramientas', download: 'Descargar', guestTitle: 'Tu cuenta', guestText: 'Inicia sesión para ver tu plan, tus compras y tus ajustes.', login: 'Iniciar sesión', register: 'Crear una cuenta', memberSince: 'Con nosotros desde el {date}', gallery: 'Obras en la galería', showcases: 'Escaparates del perfil', error: 'No se pudo cargar la cuenta. Inténtalo de nuevo.', retry: 'Reintentar', failed: 'Algo salió mal', d1: '24 horas', d7: '7 días', d30: '30 días', d90: '90 días', life: 'Para siempre' },
    pt: { publicHint: 'A página com suas vitrines e obras que todos podem ver.', kicker: 'Conta', navOverview: 'Visão geral', navSecurity: 'Acesso e segurança', navData: 'Seus dados', daysLabel: 'dias restantes', hoursLabel: 'horas restantes', foreverLabel: 'sem data de término', freePerDay: 'arquivos por dia', upgradeTitle: 'O que o Pro oferece', choosePlan: 'Escolher um plano', connected: 'Conectado', dataText: 'Baixe uma cópia de tudo o que guardamos sobre você ou exclua a conta para sempre.', resultsHint: 'Os ZIPs prontos das ferramentas ficam aqui por 30 dias.', purchasesHint: 'Planos comprados com cartão ou PayPal e chaves digitadas.', securityHint: 'Como você entra e o nome que os outros veem.', statusHint: 'Seu plano e o uso de hoje.', helpTitle: 'Precisa de ajuda?', statusTitle: 'Status da conta', planLabel: 'Plano atual', free: 'Free', pro: 'Pro', forever: 'Pro para sempre', trial: 'Teste do Pro', until: 'até {date}', daysLeft: 'faltam {n} dias', lastDay: 'falta menos de um dia', foreverNote: 'Sem data de término', freeNote: 'Plano básico com limite diário de arquivos', filesToday: 'Arquivos hoje', unlimited: 'Sem limite', ofLimit: 'de {limit} · zera todo dia', results: 'Resultados salvos', resultsNote: 'Os ZIPs prontos ficam guardados por 30 dias', proTools: 'Ferramentas Pro', tUpscale: 'Upscale', tLoop: 'Loop', tDesign: 'Seleção de design', tCheck: 'Verificação da Steam', tMark: 'Sem marca d’água', buy: 'Comprar o Pro', extend: 'Estender o Pro', haveKey: 'Digitar uma chave', supportTitle: 'Suporte', supportText: 'Escreva para nós e acompanhe as respostas na central de suporte.', supportBtn: 'Abrir a central de suporte', purchasesTitle: 'Compras', purchasesEmpty: 'Ainda não há compras.', srcGumroad: 'Cartão / PayPal', srcKey: 'Chave de acesso', srcTrial: 'Código de teste', srcLicense: 'Licença da Gumroad', stGranted: 'Ativa', stRefunded: 'Reembolsada', stPending: 'Não vinculada', loginTitle: 'Formas de entrar', emailLogin: 'E-mail', notLinked: 'não vinculado', settingsTitle: 'Configurações da conta', nick: 'Apelido', saveNick: 'Salvar apelido', saving: 'Salvando…', saved: 'Apelido salvo', passTitle: 'Alterar senha', curPass: 'Senha atual', newPass: 'Nova senha', repeatPass: 'Repita a nova senha', changePass: 'Alterar senha', fill: 'Preencha todos os campos de senha', match: 'As novas senhas não coincidem', short: 'Pelo menos 10 caracteres', changing: 'Alterando a senha…', changed: 'Senha alterada', noPassword: 'Você entra sem senha, então não há nada para alterar aqui.', publicProfile: 'Perfil público', logout: 'Sair', recentTitle: 'Últimos resultados', recentEmpty: 'Suas vitrines prontas aparecerão aqui.', openTools: 'Abrir as ferramentas', download: 'Baixar', guestTitle: 'Sua conta', guestText: 'Entre para ver seu plano, suas compras e suas configurações.', login: 'Entrar', register: 'Criar uma conta', memberSince: 'Conosco desde {date}', gallery: 'Obras na galeria', showcases: 'Vitrines do perfil', error: 'Não foi possível carregar a conta. Tente de novo.', retry: 'Tentar de novo', failed: 'Algo deu errado', d1: '24 horas', d7: '7 dias', d30: '30 dias', d90: '90 dias', life: 'Para sempre' }
  };
  var PLAN_LABEL = { '1d': 'd1', '7d': 'd7', '30d': 'd30', '90d': 'd90', unlimited: 'life' };
  var ICON = {
    logout: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 16l-4-4 4-4M6 12h10"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/>',
    box: '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    support: '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="2"/><rect x="17" y="14" width="4" height="6" rx="2"/>',
    receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    arrow: '<path d="m9 6 6 6-6 6"/>',
    grid: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    shield: '<path d="M12 3 4 6v6c0 4.5 3.4 8.3 8 9 4.6-.7 8-4.5 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    data: '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    download: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>'
  };
  var root = document.getElementById('accountPage');
  if (!root) return;
  var data = null;

  function lang() {
    var l = (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang || 'en').slice(0, 2);
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function t(key, vars) {
    var text = COPY[lang()][key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.split('{' + k + '}').join(vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function icon(name) { var s = el('span', 'acc-ico'); s.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICON[name] || '') + '</svg>'; return s; }
  function url(path) { return window.SMLang && SMLang.url ? SMLang.url(path) : path; }
  function date(ts, withTime) {
    if (!ts) return '';
    var options = withTime ? { dateStyle: 'long', timeStyle: 'short' } : { dateStyle: 'long' };
    try { return new Date(ts * 1000).toLocaleString(lang(), options); } catch (e) { return new Date(ts * 1000).toLocaleDateString(); }
  }
  function button(text, cls, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }
  function link(text, cls, href) { var a = el('a', cls, text); a.href = href; return a; }
  function openBuy(opts) { if (window.SSShell && SSShell.openActivation) SSShell.openActivation(opts || {}); }
  function cardHead(card, iconName, title) {
    var head = el('div', 'acc-card__head'); head.append(icon(iconName), el('h2', null, title)); card.append(head); return head;
  }

  // ---------------------------------------------------------------- guest / errors
  function guest() {
    root.replaceChildren();
    var box = el('section', 'acc-card acc-guest');
    box.append(glow(), icon('user'), el('h1', null, t('guestTitle')), el('p', null, t('guestText')));
    var row = el('div', 'acc-actions');
    row.append(button(t('login'), 'acc-btn acc-btn--main', function () { SSShell.openAuth && SSShell.openAuth('login'); }),
      button(t('register'), 'acc-btn', function () { SSShell.openAuth && SSShell.openAuth('register'); }));
    box.append(row);
    root.append(box);
  }
  function failure() {
    root.replaceChildren();
    var box = el('section', 'acc-card acc-guest');
    box.append(icon('lock'), el('h1', null, t('failed')), el('p', null, t('error')));
    box.append(button(t('retry'), 'acc-btn acc-btn--main', load));
    root.append(box);
  }
  function glow() { return el('span', 'acc-glow'); }

  // ---------------------------------------------------------------- page
  var SECTIONS = [['acc-overview', 'navOverview', 'spark'], ['acc-results', 'recentTitle', 'box'], ['acc-purchases', 'purchasesTitle', 'receipt'],
    ['acc-security', 'navSecurity', 'shield'], ['acc-data', 'navData', 'data']];

  function render() {
    if (!data) return;
    root.replaceChildren();
    var shell = el('div', 'acc-shell');
    var side = el('aside', 'acc-side'), main = el('div', 'acc-main');
    side.append(sideNav());
    main.append(hero(), overview(), resultsSection(), purchasesSection(), securitySection(), dataSection());
    shell.append(side, main);
    root.append(shell);
    mountAccountControls();
    watchSections();
  }

  function avatarNode(cls) {
    var u = data.user, avatar = el('div', cls);
    if (u.avatar_url) { var img = el('img'); img.src = u.avatar_url; img.alt = ''; img.decoding = 'async'; avatar.append(img); }
    else avatar.textContent = (u.name || 'S').charAt(0).toUpperCase();
    return avatar;
  }
  function badgeNode() {
    var plan = data.plan;
    return el('span', 'acc-badge' + (plan.pro ? ' is-pro' : ''), plan.pro ? (plan.lifetime ? 'PRO ∞' : 'PRO') : 'FREE');
  }

  function sideNav() {
    var box = el('div', 'acc-side__inner');
    var me = el('div', 'acc-side__me');
    var who = el('div'); who.append(el('b', null, data.user.name), badgeNode());
    me.append(avatarNode('acc-side__avatar'), who);
    box.append(me);
    var nav = el('nav', 'acc-nav'); nav.setAttribute('aria-label', t('kicker'));
    SECTIONS.forEach(function (s, index) {
      var a = el('a', 'acc-nav__link' + (index === 0 ? ' is-on' : '')); a.href = '#' + s[0]; a.dataset.section = s[0];
      a.append(icon(s[2]), el('span', null, t(s[1])));
      a.addEventListener('click', function (event) {
        event.preventDefault();
        var target = document.getElementById(s[0]);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        history.replaceState(null, '', '#' + s[0]);
      });
      nav.append(a);
    });
    box.append(nav);
    var help = el('div', 'acc-help');
    help.append(icon('support'), el('b', null, t('helpTitle')), el('p', null, t('supportText')));
    var go = link(t('supportBtn'), 'acc-help__link', url('/support')); go.append(icon('arrow'));
    help.append(go);
    box.append(help);
    return box;
  }

  function watchSections() {
    if (!('IntersectionObserver' in window)) return;
    var links = root.querySelectorAll('.acc-nav__link');
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) { a.classList.toggle('is-on', a.dataset.section === entry.target.id); });
      });
    }, { rootMargin: '-35% 0px -60% 0px' });
    SECTIONS.forEach(function (s) { var n = document.getElementById(s[0]); if (n) observer.observe(n); });
  }

  function sectionHead(section, titleKey, hintKey) {
    var head = el('header', 'acc-section__head');
    var text = el('div'); text.append(el('h2', null, t(titleKey)));
    if (hintKey) text.append(el('p', null, t(hintKey)));
    head.append(text);
    section.append(head);
    return head;
  }

  function hero() {
    var u = data.user, box = el('section', 'acc-hero');
    box.append(glow());
    var who = el('div', 'acc-hero__who');
    var nameRow = el('div', 'acc-hero__name'); nameRow.append(el('h1', null, u.name), badgeNode());
    who.append(el('span', 'acc-kicker', t('kicker')), nameRow);
    var chips = el('div', 'acc-chips');
    if (u.steam) chips.append(chip('steam', 'Steam', u.steam_name || u.steam));
    if (u.email) chips.append(chip('mail', t('emailLogin'), u.email));
    if (u.discord) chips.append(chip('discord', 'Discord', u.discord === '✓' ? '' : u.discord));
    if (u.google) chips.append(chip('google', 'Google', ''));
    if (u.telegram) chips.append(chip('telegram', 'Telegram', u.telegram === '✓' ? '' : u.telegram));
    who.append(chips);
    if (u.created_at) who.append(el('p', 'acc-hero__since', t('memberSince', { date: date(u.created_at) })));
    var tools = el('div', 'acc-hero__tools');
    var pub = link(t('publicProfile'), 'acc-btn', url(u.username ? '/profile/' + encodeURIComponent(u.username) : '/profile')); pub.prepend(icon('grid'));
    tools.append(pub);
    var out = button('', 'acc-icon-btn', logout); out.append(icon('logout')); out.setAttribute('aria-label', t('logout')); out.title = t('logout');
    tools.append(out);
    var avatar = el('div', 'acc-hero__avatar'); avatar.append(avatarNode('acc-avatar'));
    box.append(avatar, who, tools);
    return box;
  }
  function chip(kind, label, value) {
    var c = el('span', 'acc-chip acc-chip--' + kind); c.append(brand(kind), el('b', null, label)); if (value) c.append(el('span', null, value)); return c;
  }

  function overview() {
    var plan = data.plan, quota = data.quota, section = el('section', 'acc-section'); section.id = 'acc-overview';
    sectionHead(section, 'statusTitle', 'statusHint');

    // Plan: what you have + the big number (days left / ∞ / files per day) + the actions.
    var card = el('div', 'acc-plan' + (plan.pro ? ' is-pro' : '') + (plan.lifetime ? ' is-life' : ''));
    card.append(glow());
    var info = el('div', 'acc-plan__info');
    info.append(el('span', 'acc-plan__label', t('planLabel')));
    info.append(el('strong', 'acc-plan__name', plan.pro ? (plan.lifetime ? t('forever') : plan.trial ? t('trial') : t('pro')) : t('free')));
    info.append(el('span', 'acc-plan__note', plan.pro ? (plan.lifetime ? t('foreverNote') : t('until', { date: date(plan.until, true) })) : t('freeNote')));
    var actions = el('div', 'acc-plan__actions');
    if (!plan.lifetime) actions.append(button(plan.pro ? t('extend') : t('buy'), 'acc-btn acc-btn--main', function () { openBuy(); }));
    var key = button(t('haveKey'), 'acc-btn', function () { openBuy({ key: true }); }); key.prepend(icon('key'));
    actions.append(key);
    info.append(actions);
    var big = el('div', 'acc-plan__big');
    if (plan.pro && plan.lifetime) big.append(el('b', null, '∞'), el('span', null, t('foreverLabel')));
    else if (plan.pro) {
      var hours = Math.max(0, Math.floor((plan.until * 1000 - Date.now()) / 3600000));
      if (plan.days_left) big.append(el('b', null, String(plan.days_left)), el('span', null, t('daysLabel')));
      else big.append(el('b', null, String(hours)), el('span', null, t('hoursLabel')));
    } else big.append(el('b', null, String(Math.max(0, quota.limit || 0))), el('span', null, t('freePerDay')));
    card.append(info, big);
    section.append(card);

    var tiles = el('div', 'acc-tiles');
    var files = tile('file', t('filesToday'));
    if (plan.pro || quota.limit < 0) files.append(el('strong', 'acc-tile__value', '∞'), el('p', 'acc-tile__note', t('unlimited')));
    else {
      var limit = Math.max(1, quota.limit || 1), used = Math.min(limit, quota.used || 0);
      var value = el('strong', 'acc-tile__value', String(used)); value.append(el('small', null, ' / ' + limit));
      var meter = el('div', 'acc-meter'), fill = el('i'); fill.style.width = (used / limit * 100) + '%'; meter.append(fill);
      files.append(value, meter);
    }
    var saved = tile('box', t('results')); saved.append(el('strong', 'acc-tile__value', String(data.stats.results || 0)), el('p', 'acc-tile__note', t('resultsNote')));
    var works = tile('grid', t('gallery')); works.append(el('strong', 'acc-tile__value', String(data.stats.gallery || 0)), el('p', 'acc-tile__note', t('showcases') + ': ' + (data.stats.showcases || 0)));
    tiles.append(files, saved, works);
    section.append(tiles);

    var pro = el('div', 'acc-perks' + (plan.pro ? ' is-on' : ''));
    pro.append(el('b', 'acc-perks__title', plan.pro ? t('proTools') : t('upgradeTitle')));
    var list = el('div', 'acc-tools');
    (plan.pro ? [] : ['unlimited']).concat(['tUpscale', 'tLoop', 'tDesign', 'tCheck', 'tMark']).forEach(function (k) {
      var item = el('span', 'acc-tool' + (plan.pro ? ' is-on' : '')); item.append(icon(plan.pro ? 'check' : 'lock'), document.createTextNode(t(k)));
      list.append(item);
    });
    pro.append(list);
    if (!plan.pro) pro.append(button(t('choosePlan'), 'acc-btn acc-btn--small', function () { openBuy(); }));
    section.append(pro);
    return section;
  }
  function tile(name, label) { var box = el('div', 'acc-tile'); var h = el('div', 'acc-tile__head'); h.append(icon(name), el('span', null, label)); box.append(h); return box; }

  function emptyState(iconName, text, actionText, onAction, href) {
    var box = el('div', 'acc-empty');
    box.append(icon(iconName), el('p', null, text));
    if (actionText) box.append(href ? link(actionText, 'acc-btn acc-btn--small', href) : button(actionText, 'acc-btn acc-btn--small', onAction));
    return box;
  }

  function resultsSection() {
    var section = el('section', 'acc-section'); section.id = 'acc-results';
    var head = sectionHead(section, 'recentTitle', 'resultsHint');
    var items = data.results || [];
    if (!items.length) { section.append(emptyState('box', t('recentEmpty'), t('openTools'), null, url('/app'))); return section; }
    var more = link(t('openTools'), 'acc-link', url('/app')); more.append(icon('arrow')); head.append(more);
    var grid = el('div', 'acc-results');
    items.forEach(function (item) {
      var card = el('article', 'acc-result');
      var thumb = el('div', 'acc-result__thumb');
      if (item.thumb_url) { var img = el('img'); img.src = item.thumb_url; img.alt = ''; img.loading = 'lazy'; thumb.append(img); }
      else thumb.append(icon('box'));
      var meta = el('div', 'acc-result__meta');
      meta.append(el('b', null, item.title || item.mode || item.kind || 'ZIP'), el('small', null, date(item.created_at)));
      var dl = link('', 'acc-icon-btn acc-icon-btn--small', item.download_url); dl.append(icon('download')); dl.setAttribute('aria-label', t('download')); dl.title = t('download');
      var row = el('div', 'acc-result__row'); row.append(meta, dl);
      card.append(thumb, row);
      grid.append(card);
    });
    section.append(grid);
    return section;
  }

  function purchasesSection() {
    var section = el('section', 'acc-section'); section.id = 'acc-purchases';
    sectionHead(section, 'purchasesTitle', 'purchasesHint');
    var items = data.purchases || [];
    if (!items.length) {
      section.append(emptyState('receipt', t('purchasesEmpty'), data.plan.lifetime ? '' : t('choosePlan'), function () { openBuy(); }));
      return section;
    }
    var list = el('ul', 'acc-buys');
    items.forEach(function (item) {
      var li = el('li', 'acc-buy');
      var what = item.plan ? t(PLAN_LABEL[item.plan] || item.plan) : t(item.source === 'trial' ? 'srcTrial' : item.source === 'gumroad_license' ? 'srcLicense' : 'srcKey');
      var via = item.source === 'gumroad' ? t('srcGumroad') : '';
      var mark = el('span', 'acc-buy__mark' + (item.plan === 'unlimited' ? ' is-life' : ''));
      if (item.plan === 'unlimited') mark.textContent = '∞'; else if (item.plan) mark.textContent = item.plan.replace('d', ''); else mark.append(icon('key'));
      var main = el('div', 'acc-buy__main'); main.append(el('b', null, what), el('small', null, [via, date(item.at)].filter(Boolean).join(' · ')));
      var status = item.status === 'granted' ? 'stGranted' : (item.status === 'refunded' || item.status === 'revoked') ? 'stRefunded' : 'stPending';
      var side = el('div', 'acc-buy__side');
      if (item.price) side.append(el('span', 'acc-buy__price', item.price));
      side.append(el('span', 'acc-buy__status is-' + status, t(status)));
      li.append(mark, main, side);
      list.append(li);
    });
    section.append(list);
    return section;
  }

  function securitySection() {
    var u = data.user, section = el('section', 'acc-section'); section.id = 'acc-security';
    sectionHead(section, 'navSecurity', 'securityHint');
    var logins = el('div', 'acc-logins');
    [['mail', t('emailLogin'), u.email], ['steam', 'Steam', u.steam_name || u.steam], ['discord', 'Discord', u.discord],
      ['google', 'Google', u.google ? '✓' : ''], ['telegram', 'Telegram', u.telegram]].forEach(function (row) {
      var on = !!row[2];
      var card = el('div', 'acc-login acc-login--' + row[0] + (on ? ' is-on' : ''));
      var text = el('div', 'acc-login__text'); text.append(el('b', null, row[1]), el('small', null, on ? (row[2] === '✓' ? t('connected') : row[2]) : t('notLinked')));
      card.append(brand(row[0]), text, el('span', 'acc-login__dot'));
      logins.append(card);
    });
    section.append(logins);

    var forms = el('div', 'acc-forms');
    var nickCard = el('div', 'acc-form');
    nickCard.append(el('h3', null, t('nick')));
    var nickInput = el('input', 'acc-input'); nickInput.id = 'accNick'; nickInput.maxLength = 40; nickInput.autocomplete = 'nickname'; nickInput.value = u.display_name || '';
    var nickState = el('p', 'acc-state'); nickState.setAttribute('aria-live', 'polite');
    var nickRow = el('div', 'acc-inline');
    nickRow.append(nickInput, button(t('saveNick'), 'acc-btn', function (event) { saveNick(event.currentTarget, nickInput, nickState); }));
    nickCard.append(nickRow, nickState);
    // Left column: nickname + the public page it belongs to (fills the space next to the password form).
    var leftCol = el('div', 'acc-forms__col');
    var pubCard = el('div', 'acc-form acc-form--public');
    var pubPath = u.username ? '/profile/' + encodeURIComponent(u.username) : '/profile';
    pubCard.append(el('h3', null, t('publicProfile')), el('p', 'acc-form__text', t('publicHint')));
    var pubRow = el('div', 'acc-public');
    pubRow.append(el('code', null, location.host + url(pubPath)));
    var open = link('', 'acc-icon-btn acc-icon-btn--small', url(pubPath)); open.append(icon('arrow')); open.setAttribute('aria-label', t('publicProfile'));
    pubRow.append(open);
    pubCard.append(pubRow);
    leftCol.append(nickCard, pubCard);
    forms.append(leftCol);

    var passCard = el('div', 'acc-form');
    passCard.append(el('h3', null, t('passTitle')));
    if (!u.password) passCard.append(el('p', 'acc-form__text', t('noPassword')));
    else {
      var fields = [['accPassCur', 'curPass', 'current-password'], ['accPassNew', 'newPass', 'new-password'], ['accPassRep', 'repeatPass', 'new-password']].map(function (f) {
        var label = el('label', 'acc-field'); label.append(el('span', null, t(f[1])));
        var input = el('input', 'acc-input'); input.type = 'password'; input.id = f[0]; input.autocomplete = f[2]; input.minLength = 10;
        label.append(input); passCard.append(label); return input;
      });
      var passState = el('p', 'acc-state'); passState.setAttribute('aria-live', 'polite');
      passCard.append(button(t('changePass'), 'acc-btn acc-btn--wide', function (event) { changePassword(event.currentTarget, fields, passState); }), passState);
    }
    forms.append(passCard);
    section.append(forms);
    return section;
  }

  function dataSection() {
    var section = el('section', 'acc-section acc-settings'); section.id = 'acc-data';
    sectionHead(section, 'navData', 'dataText');
    var body = el('div', 'acc-data'); body.id = 'accountContent';
    // Hidden field read by account-controls.js (export / delete confirmation); it mounts its two blocks here.
    var email = el('input'); email.type = 'hidden'; email.id = 'accountEmail'; email.value = (window.SS_ME && SS_ME.email) || data.user.email || '';
    body.append(email);
    section.append(body);
    return section;
  }

  // Brand marks for sign-in methods (simple glyphs; colours in account-page.css).
  var BRAND = {
    steam: '<path d="M12 2a10 10 0 0 0-9.9 8.6l5.3 2.2a2.8 2.8 0 0 1 1.7-.5l2.4-3.4v-.1a3.8 3.8 0 1 1 3.8 3.8h-.1l-3.4 2.4v.1a2.8 2.8 0 0 1-5.6.3L2.4 14A10 10 0 1 0 12 2Z" fill="currentColor"/><circle cx="15.3" cy="8.8" r="2.4" fill="currentColor"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="m4 7 8 6 8-6" fill="none" stroke="currentColor" stroke-width="1.8"/>',
    discord: '<path d="M19.3 5.3A16.5 16.5 0 0 0 15.2 4l-.5 1a15 15 0 0 0-5.4 0l-.5-1a16.5 16.5 0 0 0-4.1 1.3C2.1 9.2 1.4 13 1.7 16.7a16.6 16.6 0 0 0 5 2.6l1.1-1.7a10.7 10.7 0 0 1-1.7-.8l.4-.3a11.8 11.8 0 0 0 11 0l.4.3c-.5.3-1.1.6-1.7.8l1.1 1.7a16.6 16.6 0 0 0 5-2.6c.4-4.3-.6-8-3-11.4ZM8.5 14.5c-1 0-1.8-.9-1.8-2s.8-2 1.8-2 1.8.9 1.8 2-.8 2-1.8 2Zm7 0c-1 0-1.8-.9-1.8-2s.8-2 1.8-2 1.8.9 1.8 2-.8 2-1.8 2Z" fill="currentColor"/>',
    google: '<path d="M21.6 12.2c0-.7-.1-1.4-.2-2H12v3.8h5.4a4.6 4.6 0 0 1-2 3v2.5h3.2c1.9-1.7 3-4.3 3-7.3Z" fill="#4285F4"/><path d="M12 22c2.7 0 5-.9 6.6-2.5l-3.2-2.5c-.9.6-2 1-3.4 1-2.6 0-4.8-1.8-5.6-4.1H3.1v2.6A10 10 0 0 0 12 22Z" fill="#34A853"/><path d="M6.4 13.9a6 6 0 0 1 0-3.8V7.5H3.1a10 10 0 0 0 0 9Z" fill="#FBBC05"/><path d="M12 6c1.5 0 2.8.5 3.8 1.5l2.9-2.9A10 10 0 0 0 3.1 7.5l3.3 2.6C7.2 7.8 9.4 6 12 6Z" fill="#EA4335"/>',
    telegram: '<path d="M21.5 4.3 18.3 19.5c-.2 1-.9 1.3-1.7.8l-4.6-3.4-2.2 2.1c-.3.3-.5.5-1 .5l.3-4.7 8.6-7.8c.4-.3-.1-.5-.6-.2L6.5 13.5l-4.6-1.4c-1-.3-1-1 .2-1.5l18-6.9c.8-.3 1.6.2 1.4 1.6Z" fill="currentColor"/>'
  };
  function brand(kind) { var s = el('span', 'acc-brand acc-brand--' + kind); s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + (BRAND[kind] || '') + '</svg>'; return s; }

  // ---------------------------------------------------------------- actions
  function state(node, text, kind) { node.textContent = text || ''; node.className = 'acc-state' + (kind ? ' is-' + kind : ''); }

  function saveNick(btn, input, out) {
    var name = input.value.trim();
    state(out, t('saving'), 'wait'); btn.disabled = true;
    fetch('/api/profile/update', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_name: name }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) throw new Error(d.msg || t('failed'));
        state(out, t('saved'), 'ok'); data.user.display_name = name; if (name) data.user.name = name;
        var h1 = root.querySelector('.acc-who__name h1'); if (h1 && name) h1.textContent = name;
        if (window.SSShell && SSShell.loadMe) SSShell.loadMe();
      })
      .catch(function (e) { state(out, e.message || t('failed'), 'bad'); })
      .then(function () { btn.disabled = false; });
  }

  function changePassword(btn, fields, out) {
    var current = fields[0].value, next = fields[1].value, repeat = fields[2].value;
    if (!current || !next || !repeat) { state(out, t('fill'), 'bad'); return; }
    if (next !== repeat) { state(out, t('match'), 'bad'); return; }
    if (next.length < 10) { state(out, t('short'), 'bad'); return; }
    state(out, t('changing'), 'wait'); btn.disabled = true;
    fetch('/api/auth/change-password', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password: current, new_password: next }) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) throw new Error(d.msg || t('failed'));
        fields.forEach(function (f) { f.value = ''; });
        state(out, t('changed'), 'ok');
      })
      .catch(function (e) { state(out, e.message || t('failed'), 'bad'); })
      .then(function () { btn.disabled = false; });
  }

  function logout() {
    fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
      .catch(function () {})
      .then(function () { location.href = url('/'); });
  }

  // Export + delete live in account-controls.js; it mounts itself into #accountContent.
  function mountAccountControls() {
    if (document.querySelector('script[data-account-controls]')) {
      if (window.SMAccountControlsMount) window.SMAccountControlsMount();
      return;
    }
    var script = document.createElement('script');
    script.src = '/static/js/account-controls.js?v=20261006-acc1'; script.dataset.accountControls = '1';
    document.body.appendChild(script);
  }

  function load() {
    root.replaceChildren(el('div', 'acc-loading'));
    fetch('/api/account/overview', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { if (r.status === 401) return { login: true }; return r.ok ? r.json() : null; })
      .then(function (d) {
        if (d && d.login) { data = null; guest(); return; }
        if (!d || !d.ok) { failure(); return; }
        data = d; render();
      })
      .catch(failure);
  }

  if (location.hash === '#purchases') setTimeout(function () { var n = document.getElementById('acc-purchases'); if (n) n.scrollIntoView({ block: 'start' }); }, 800);
  window.addEventListener('sm:langchange', function () { if (data) render(); else if (root.querySelector('.acc-guest')) guest(); });
  load();
})();
