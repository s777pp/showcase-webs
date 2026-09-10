/* Shared site shell: one header + footer for every tab.
   Pages include ss.css + this file and get the same chrome, the same active-tab
   logic and the same auth pill. Nothing here touches page-local markup, so it
   can be added to an existing page without changing its behaviour. */
(function () {
  'use strict';

  var NAV = [
    { href: '/',        key: 'home',    label: { ru: 'Главная',    en: 'Home' },     icon: 'home' },
    { href: '/app',     key: 'tools',   label: { ru: 'Инструменты',en: 'Tools' },    icon: 'tools' },
    { href: '/profile', key: 'builder', label: { ru: 'Профиль',    en: 'Profile' },  icon: 'user', tag: 'new' },
    { href: '/gallery', key: 'gallery', label: { ru: 'Галерея',    en: 'Gallery' },  icon: 'grid' },
    { href: 'https://t.me/showcasemaker', key: 'support', label: { ru: 'Техподдержка', en: 'Support' }, icon: 'support', external: true }
  ];

  var GROUPS = [
    { title: { ru: 'Сайт',        en: 'Site' },    items: ['home', 'gallery'] },
    { title: { ru: 'Инструменты', en: 'Tools' },   items: ['tools', 'builder', 'support'] },
    { title: { ru: 'Аккаунт',     en: 'Account' }, items: ['account'] }
  ];

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5V21H3z"/>',
    tools: '<path d="M4 7h16M4 12h10M4 17h7"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
    grid: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    support: '<path d="M4 13v-1a8 8 0 0 1 16 0v1"/><path d="M4 13h3v6H5a1 1 0 0 1-1-1v-5Zm16 0h-3v6h2a1 1 0 0 0 1-1v-5ZM17 19c0 1.1-.9 2-2 2h-3"/>',
    key: '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M18 12v4"/>',
    card: '<rect x="2.5" y="5" width="19" height="14" rx="3"/><path d="M3 9h18M6 15h4"/>'
  };

  var OAUTH_ICONS = {
    discord: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#8b95ff" d="M20.3 4.4a19.7 19.7 0 0 0-4.9-1.5l-.6 1.2a18.3 18.3 0 0 0-5.5 0l-.6-1.2a19.7 19.7 0 0 0-4.9 1.5C.5 9-.3 13.6.1 18.1a19.9 19.9 0 0 0 6 3l1.2-2a13 13 0 0 1-1.9-.9l.4-.3c3.9 1.8 8.2 1.8 12.1 0l.4.3a12 12 0 0 1-1.9.9l1.2 2a19.8 19.8 0 0 0 6-3c.5-5.2-.8-9.7-3.3-13.7ZM8 15.3c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Zm8 0c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Z"/></svg>',
    google: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.5-.2-2.2H12v4.3h5.4a4.6 4.6 0 0 1-2 3v2.8h3.3c1.9-1.8 2.9-4.4 2.9-7.9Z"/><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.8c-.9.6-2.1 1-3.4 1a5.9 5.9 0 0 1-5.5-4.1H3.1v2.9A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.5 13.7a6 6 0 0 1 0-3.8V7H3.1a10 10 0 0 0 0 9.6l3.4-2.9Z"/><path fill="#EA4335" d="M12 5.8c1.5 0 2.8.5 3.8 1.5l2.9-2.8A9.7 9.7 0 0 0 12 2a10 10 0 0 0-8.9 5.4l3.4 2.5A5.9 5.9 0 0 1 12 5.8Z"/></svg>',
    telegram: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#26A5E4"/><path fill="#fff" d="m17.8 7-2 10c-.2.7-.6.9-1.2.5l-3-2.2-1.5 1.4c-.2.2-.3.3-.7.3l.2-3.1 5.7-5.2c.2-.2 0-.4-.4-.2l-7 4.4-3-.9c-.7-.2-.7-.7.1-1l11.7-4.5c.6-.2 1.1.1 1.1.5Z"/></svg>',
    steam: '<img src="/static/steam.png" width="20" height="20" alt="" aria-hidden="true" style="display:block;object-fit:contain">'
  };

  var ACCOUNT_COPY = {
    en: {maintenance:'Technical work is in progress. Some features may be temporarily unavailable.',forgot:'Forgot password?',forgotTitle:'Recover password',forgotSub:'Enter your account email. We will send a six-digit recovery code.',sendCode:'Send code',sending:'Sending code…',resetTitle:'Set a new password',resetSub:'Enter the code from the email and your new password.',codeLabel:'Code from email',yourCode:'YOUR CODE',newPassword:'New password',repeatPassword:'Repeat new password',savePassword:'Save new password',resetting:'Changing password…',resetDone:'Password changed. Log in with your new password.',passwordMismatch:'New passwords do not match.',passwordShort:'Password must contain at least 10 characters.',backLogin:'Back to login',recoverySent:'If an account exists for this address, a recovery code has been sent.',exportTitle:'Export account data',exportDesc:'Download your account, projects, profile, gallery activity and settings as JSON.',downloadData:'Download my data',preparingExport:'Preparing export…',exportFailed:'The account export could not be downloaded.',deleteTitle:'Delete account',deleteDesc:'Permanently deletes your account, projects, profile, gallery uploads and stored media. This cannot be undone.',confirmEmail:'Type your account email to confirm',deleteAccount:'Delete account permanently',deleteConfirm:'Permanently delete this account and all its data?',deleting:'Deleting account…',deleteMismatch:'Enter the exact email address of this account.',deleteFailed:'The account could not be deleted.'},
    ru: {maintenance:'Ведутся технические работы. Некоторые функции могут быть временно недоступны.',forgot:'Забыли пароль?',forgotTitle:'Восстановление пароля',forgotSub:'Введите почту аккаунта. Мы отправим шестизначный код восстановления.',sendCode:'Отправить код',sending:'Отправляем код…',resetTitle:'Новый пароль',resetSub:'Введите код из письма и новый пароль.',codeLabel:'Код из письма',yourCode:'ВАШ КОД',newPassword:'Новый пароль',repeatPassword:'Повторите новый пароль',savePassword:'Сохранить новый пароль',resetting:'Меняем пароль…',resetDone:'Пароль изменён. Войдите с новым паролем.',passwordMismatch:'Новые пароли не совпадают.',passwordShort:'Пароль должен содержать не менее 10 символов.',backLogin:'Вернуться ко входу',recoverySent:'Если аккаунт с такой почтой существует, код восстановления отправлен.',exportTitle:'Экспорт данных аккаунта',exportDesc:'Скачайте данные аккаунта, проекты, профиль, активность галереи и настройки в формате JSON.',downloadData:'Скачать мои данные',preparingExport:'Готовим экспорт…',exportFailed:'Не удалось скачать экспорт аккаунта.',deleteTitle:'Удаление аккаунта',deleteDesc:'Навсегда удаляет аккаунт, проекты, профиль, работы в галерее и сохранённые медиа. Отменить это действие нельзя.',confirmEmail:'Введите почту аккаунта для подтверждения',deleteAccount:'Удалить аккаунт навсегда',deleteConfirm:'Навсегда удалить этот аккаунт и все его данные?',deleting:'Удаляем аккаунт…',deleteMismatch:'Введите точный адрес почты этого аккаунта.',deleteFailed:'Не удалось удалить аккаунт.'},
    de: {maintenance:'Technische Arbeiten laufen. Einige Funktionen sind möglicherweise vorübergehend nicht verfügbar.',forgot:'Passwort vergessen?',forgotTitle:'Passwort wiederherstellen',forgotSub:'Geben Sie die E-Mail-Adresse Ihres Kontos ein. Wir senden einen sechsstelligen Wiederherstellungscode.',sendCode:'Code senden',sending:'Code wird gesendet…',resetTitle:'Neues Passwort festlegen',resetSub:'Geben Sie den Code aus der E-Mail und Ihr neues Passwort ein.',codeLabel:'Code aus der E-Mail',yourCode:'IHR CODE',newPassword:'Neues Passwort',repeatPassword:'Neues Passwort wiederholen',savePassword:'Neues Passwort speichern',resetting:'Passwort wird geändert…',resetDone:'Passwort geändert. Melden Sie sich mit dem neuen Passwort an.',passwordMismatch:'Die neuen Passwörter stimmen nicht überein.',passwordShort:'Das Passwort muss mindestens 10 Zeichen enthalten.',backLogin:'Zurück zur Anmeldung',recoverySent:'Falls ein Konto mit dieser Adresse existiert, wurde ein Wiederherstellungscode gesendet.',exportTitle:'Kontodaten exportieren',exportDesc:'Laden Sie Konto, Projekte, Profil, Galerieaktivität und Einstellungen als JSON herunter.',downloadData:'Meine Daten herunterladen',preparingExport:'Export wird vorbereitet…',exportFailed:'Der Kontoexport konnte nicht heruntergeladen werden.',deleteTitle:'Konto löschen',deleteDesc:'Löscht Konto, Projekte, Profil, Galeriebeiträge und gespeicherte Medien dauerhaft. Dies kann nicht rückgängig gemacht werden.',confirmEmail:'E-Mail-Adresse des Kontos zur Bestätigung eingeben',deleteAccount:'Konto dauerhaft löschen',deleteConfirm:'Dieses Konto und alle Daten dauerhaft löschen?',deleting:'Konto wird gelöscht…',deleteMismatch:'Geben Sie die genaue E-Mail-Adresse dieses Kontos ein.',deleteFailed:'Das Konto konnte nicht gelöscht werden.'},
    tr: {maintenance:'Teknik çalışma devam ediyor. Bazı özellikler geçici olarak kullanılamayabilir.',forgot:'Parolanızı mı unuttunuz?',forgotTitle:'Parolayı kurtar',forgotSub:'Hesabınızın e-posta adresini girin. Altı haneli bir kurtarma kodu göndereceğiz.',sendCode:'Kodu gönder',sending:'Kod gönderiliyor…',resetTitle:'Yeni parola belirle',resetSub:'E-postadaki kodu ve yeni parolanızı girin.',codeLabel:'E-postadaki kod',yourCode:'KODUNUZ',newPassword:'Yeni parola',repeatPassword:'Yeni parolayı tekrarla',savePassword:'Yeni parolayı kaydet',resetting:'Parola değiştiriliyor…',resetDone:'Parola değiştirildi. Yeni parolanızla giriş yapın.',passwordMismatch:'Yeni parolalar eşleşmiyor.',passwordShort:'Parola en az 10 karakter olmalıdır.',backLogin:'Girişe dön',recoverySent:'Bu adres için bir hesap varsa kurtarma kodu gönderildi.',exportTitle:'Hesap verilerini dışa aktar',exportDesc:'Hesabınızı, projelerinizi, profilinizi, galeri etkinliğinizi ve ayarlarınızı JSON olarak indirin.',downloadData:'Verilerimi indir',preparingExport:'Dışa aktarım hazırlanıyor…',exportFailed:'Hesap dışa aktarımı indirilemedi.',deleteTitle:'Hesabı sil',deleteDesc:'Hesabınızı, projelerinizi, profilinizi, galeri yüklemelerinizi ve kayıtlı medyayı kalıcı olarak siler. Bu işlem geri alınamaz.',confirmEmail:'Onaylamak için hesap e-postanızı yazın',deleteAccount:'Hesabı kalıcı olarak sil',deleteConfirm:'Bu hesap ve tüm verileri kalıcı olarak silinsin mi?',deleting:'Hesap siliniyor…',deleteMismatch:'Bu hesabın e-posta adresini eksiksiz girin.',deleteFailed:'Hesap silinemedi.'},
    fr: {maintenance:'Des travaux techniques sont en cours. Certaines fonctions peuvent être temporairement indisponibles.',forgot:'Mot de passe oublié ?',forgotTitle:'Récupérer le mot de passe',forgotSub:'Saisissez l’adresse e-mail de votre compte. Nous enverrons un code de récupération à six chiffres.',sendCode:'Envoyer le code',sending:'Envoi du code…',resetTitle:'Définir un nouveau mot de passe',resetSub:'Saisissez le code reçu par e-mail et votre nouveau mot de passe.',codeLabel:'Code reçu par e-mail',yourCode:'VOTRE CODE',newPassword:'Nouveau mot de passe',repeatPassword:'Répéter le nouveau mot de passe',savePassword:'Enregistrer le nouveau mot de passe',resetting:'Modification du mot de passe…',resetDone:'Mot de passe modifié. Connectez-vous avec le nouveau mot de passe.',passwordMismatch:'Les nouveaux mots de passe ne correspondent pas.',passwordShort:'Le mot de passe doit contenir au moins 10 caractères.',backLogin:'Retour à la connexion',recoverySent:'Si un compte existe pour cette adresse, un code de récupération a été envoyé.',exportTitle:'Exporter les données du compte',exportDesc:'Téléchargez votre compte, vos projets, votre profil, l’activité de la galerie et vos réglages au format JSON.',downloadData:'Télécharger mes données',preparingExport:'Préparation de l’export…',exportFailed:'Impossible de télécharger l’export du compte.',deleteTitle:'Supprimer le compte',deleteDesc:'Supprime définitivement le compte, les projets, le profil, les publications de la galerie et les médias enregistrés. Cette action est irréversible.',confirmEmail:'Saisissez l’e-mail du compte pour confirmer',deleteAccount:'Supprimer définitivement le compte',deleteConfirm:'Supprimer définitivement ce compte et toutes ses données ?',deleting:'Suppression du compte…',deleteMismatch:'Saisissez l’adresse e-mail exacte de ce compte.',deleteFailed:'Impossible de supprimer le compte.'},
    uk: {maintenance:'Тривають технічні роботи. Деякі функції можуть бути тимчасово недоступні.',forgot:'Забули пароль?',forgotTitle:'Відновлення пароля',forgotSub:'Введіть електронну пошту облікового запису. Ми надішлемо шестизначний код відновлення.',sendCode:'Надіслати код',sending:'Надсилаємо код…',resetTitle:'Новий пароль',resetSub:'Введіть код із листа та новий пароль.',codeLabel:'Код із листа',yourCode:'ВАШ КОД',newPassword:'Новий пароль',repeatPassword:'Повторіть новий пароль',savePassword:'Зберегти новий пароль',resetting:'Змінюємо пароль…',resetDone:'Пароль змінено. Увійдіть із новим паролем.',passwordMismatch:'Нові паролі не збігаються.',passwordShort:'Пароль має містити щонайменше 10 символів.',backLogin:'Повернутися до входу',recoverySent:'Якщо обліковий запис із цією адресою існує, код відновлення надіслано.',exportTitle:'Експорт даних облікового запису',exportDesc:'Завантажте дані облікового запису, проєкти, профіль, активність галереї та налаштування у форматі JSON.',downloadData:'Завантажити мої дані',preparingExport:'Готуємо експорт…',exportFailed:'Не вдалося завантажити експорт облікового запису.',deleteTitle:'Видалення облікового запису',deleteDesc:'Назавжди видаляє обліковий запис, проєкти, профіль, роботи в галереї та збережені медіафайли. Цю дію неможливо скасувати.',confirmEmail:'Введіть пошту облікового запису для підтвердження',deleteAccount:'Видалити обліковий запис назавжди',deleteConfirm:'Назавжди видалити цей обліковий запис і всі його дані?',deleting:'Видаляємо обліковий запис…',deleteMismatch:'Введіть точну адресу пошти цього облікового запису.',deleteFailed:'Не вдалося видалити обліковий запис.'},
    es: {maintenance:'Hay trabajos técnicos en curso. Algunas funciones pueden no estar disponibles temporalmente.',forgot:'¿Has olvidado la contraseña?',forgotTitle:'Recuperar contraseña',forgotSub:'Introduce el correo de tu cuenta. Enviaremos un código de recuperación de seis dígitos.',sendCode:'Enviar código',sending:'Enviando código…',resetTitle:'Crear una nueva contraseña',resetSub:'Introduce el código del correo y tu nueva contraseña.',codeLabel:'Código del correo',yourCode:'TU CÓDIGO',newPassword:'Nueva contraseña',repeatPassword:'Repetir la nueva contraseña',savePassword:'Guardar nueva contraseña',resetting:'Cambiando contraseña…',resetDone:'Contraseña cambiada. Inicia sesión con la nueva contraseña.',passwordMismatch:'Las nuevas contraseñas no coinciden.',passwordShort:'La contraseña debe tener al menos 10 caracteres.',backLogin:'Volver al inicio de sesión',recoverySent:'Si existe una cuenta para esta dirección, se ha enviado un código de recuperación.',exportTitle:'Exportar datos de la cuenta',exportDesc:'Descarga tu cuenta, proyectos, perfil, actividad de la galería y ajustes en formato JSON.',downloadData:'Descargar mis datos',preparingExport:'Preparando exportación…',exportFailed:'No se pudo descargar la exportación de la cuenta.',deleteTitle:'Eliminar cuenta',deleteDesc:'Elimina permanentemente la cuenta, los proyectos, el perfil, las publicaciones de la galería y los archivos guardados. No se puede deshacer.',confirmEmail:'Escribe el correo de la cuenta para confirmar',deleteAccount:'Eliminar cuenta permanentemente',deleteConfirm:'¿Eliminar permanentemente esta cuenta y todos sus datos?',deleting:'Eliminando cuenta…',deleteMismatch:'Introduce el correo exacto de esta cuenta.',deleteFailed:'No se pudo eliminar la cuenta.'},
    pt: {maintenance:'Há trabalhos técnicos em andamento. Alguns recursos podem ficar temporariamente indisponíveis.',forgot:'Esqueceu a senha?',forgotTitle:'Recuperar senha',forgotSub:'Digite o e-mail da sua conta. Enviaremos um código de recuperação de seis dígitos.',sendCode:'Enviar código',sending:'Enviando código…',resetTitle:'Definir uma nova senha',resetSub:'Digite o código recebido por e-mail e a nova senha.',codeLabel:'Código do e-mail',yourCode:'SEU CÓDIGO',newPassword:'Nova senha',repeatPassword:'Repetir a nova senha',savePassword:'Salvar nova senha',resetting:'Alterando senha…',resetDone:'Senha alterada. Entre com a nova senha.',passwordMismatch:'As novas senhas não coincidem.',passwordShort:'A senha deve ter pelo menos 10 caracteres.',backLogin:'Voltar ao login',recoverySent:'Se existir uma conta para este endereço, um código de recuperação foi enviado.',exportTitle:'Exportar dados da conta',exportDesc:'Baixe sua conta, projetos, perfil, atividade da galeria e configurações em JSON.',downloadData:'Baixar meus dados',preparingExport:'Preparando exportação…',exportFailed:'Não foi possível baixar a exportação da conta.',deleteTitle:'Excluir conta',deleteDesc:'Exclui permanentemente a conta, projetos, perfil, envios da galeria e mídia armazenada. Esta ação não pode ser desfeita.',confirmEmail:'Digite o e-mail da conta para confirmar',deleteAccount:'Excluir conta permanentemente',deleteConfirm:'Excluir permanentemente esta conta e todos os seus dados?',deleting:'Excluindo conta…',deleteMismatch:'Digite o endereço de e-mail exato desta conta.',deleteFailed:'Não foi possível excluir a conta.'}
  };
  window.SS_ACCOUNT_COPY = ACCOUNT_COPY;

  function accountCopy() {
    return ACCOUNT_COPY[lang()] || ACCOUNT_COPY.en;
  }

  var RESET_ERROR_COPY = {
    en:{invalid_email:'Enter a valid email address.',rate_limited:'Too many attempts. Try again later.',delivery_failed:'The email could not be sent. Try again later.',invalid_code:'The code is incorrect or has expired.',weak_password:'Password must contain at least 10 characters.',failed:'Password recovery failed. Try again.'},
    ru:{invalid_email:'Введите корректный адрес почты.',rate_limited:'Слишком много попыток. Попробуйте позже.',delivery_failed:'Не удалось отправить письмо. Попробуйте позже.',invalid_code:'Код неверный или срок его действия истёк.',weak_password:'Пароль должен содержать не менее 10 символов.',failed:'Не удалось восстановить пароль. Попробуйте снова.'},
    de:{invalid_email:'Geben Sie eine gültige E-Mail-Adresse ein.',rate_limited:'Zu viele Versuche. Versuchen Sie es später erneut.',delivery_failed:'Die E-Mail konnte nicht gesendet werden. Versuchen Sie es später erneut.',invalid_code:'Der Code ist falsch oder abgelaufen.',weak_password:'Das Passwort muss mindestens 10 Zeichen enthalten.',failed:'Die Passwortwiederherstellung ist fehlgeschlagen. Versuchen Sie es erneut.'},
    tr:{invalid_email:'Geçerli bir e-posta adresi girin.',rate_limited:'Çok fazla deneme yapıldı. Daha sonra tekrar deneyin.',delivery_failed:'E-posta gönderilemedi. Daha sonra tekrar deneyin.',invalid_code:'Kod yanlış veya süresi dolmuş.',weak_password:'Parola en az 10 karakter olmalıdır.',failed:'Parola kurtarma başarısız oldu. Tekrar deneyin.'},
    fr:{invalid_email:'Saisissez une adresse e-mail valide.',rate_limited:'Trop de tentatives. Réessayez plus tard.',delivery_failed:'Impossible d’envoyer l’e-mail. Réessayez plus tard.',invalid_code:'Le code est incorrect ou a expiré.',weak_password:'Le mot de passe doit contenir au moins 10 caractères.',failed:'La récupération du mot de passe a échoué. Réessayez.'},
    uk:{invalid_email:'Введіть коректну адресу електронної пошти.',rate_limited:'Забагато спроб. Спробуйте пізніше.',delivery_failed:'Не вдалося надіслати лист. Спробуйте пізніше.',invalid_code:'Код неправильний або термін його дії минув.',weak_password:'Пароль має містити щонайменше 10 символів.',failed:'Не вдалося відновити пароль. Спробуйте ще раз.'},
    es:{invalid_email:'Introduce una dirección de correo válida.',rate_limited:'Demasiados intentos. Inténtalo de nuevo más tarde.',delivery_failed:'No se pudo enviar el correo. Inténtalo más tarde.',invalid_code:'El código es incorrecto o ha caducado.',weak_password:'La contraseña debe tener al menos 10 caracteres.',failed:'No se pudo recuperar la contraseña. Inténtalo de nuevo.'},
    pt:{invalid_email:'Digite um endereço de e-mail válido.',rate_limited:'Muitas tentativas. Tente novamente mais tarde.',delivery_failed:'Não foi possível enviar o e-mail. Tente novamente mais tarde.',invalid_code:'O código está incorreto ou expirou.',weak_password:'A senha deve ter pelo menos 10 caracteres.',failed:'Não foi possível recuperar a senha. Tente novamente.'}
  };
  function resetErrorMessage(data) {
    var messages = RESET_ERROR_COPY[lang()] || RESET_ERROR_COPY.en;
    return messages[data && data.code] || messages.failed;
  }

  function lang() {
    try { return window.SMLang ? SMLang.get() : (localStorage.getItem('sm_lang') || localStorage.getItem('ss_lang') || 'en'); } catch (e) { return 'en'; }
  }
  function analyticsHeaders() {
    try { return window.SMAnalytics ? window.SMAnalytics.headers() : {}; } catch (e) { return {}; }
  }
  function t(obj) { return window.SMLang && SMLang.pick ? SMLang.pick(obj) : (obj[lang()] || obj.en || obj.ru); }
  function siteUrl(href) { return window.SMLang && SMLang.url ? SMLang.url(href) : href; }
  function svg(name) {
    return '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="width:18px;height:18px;flex:none">' +
      (ICONS[name] || '') + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function active(href) {
    var p = location.pathname.replace(/^\/(?:en|ru|de|tr|fr|uk|es|pt)(?=\/|$)/, '').replace(/\/+$/, '') || '/';
    if (href === '/') return p === '/';
    /* конструктор пока живёт на временном адресе /profile2 — подсвечиваем «Профиль» */
    if (href === '/profile' && p === '/profile2') return true;
    return p === href || p.indexOf(href + '/') === 0;
  }

  function navHTML() {
    return NAV.map(function (n) {
      return '<a class="ss-nav__i' + (active(n.href) ? ' is-on' : '') + '" href="' + siteUrl(n.href) + '"' +
        (n.external ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' +
        svg(n.icon) + '<span>' + esc(t(n.label)) + '</span>' +
        (n.tag ? '<i class="ss-nav__tag">' + esc(lang() === 'ru' ? 'новое' : n.tag) + '</i>' : '') + '</a>';
    }).join('');
  }

  function drawerHTML() {
    var byKey = {};
    NAV.forEach(function (n) { byKey[n.key] = n; });
    byKey.account = { href: '/profile#account', key: 'account', icon: 'key',
                      label: { ru: 'Аккаунт и Pro-ключ', en: 'Account & Pro key' } };
    var groups = GROUPS.map(function (g) {
      var links = g.items.map(function (k) {
        var n = byKey[k];
        if (!n) return '';
        return '<a href="' + siteUrl(n.href) + '"' + (active(n.href) ? ' class="is-on"' : '') +
          (n.external ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' +
          svg(n.icon) + esc(t(n.label)) + '</a>';
      }).join('');
      return '<div class="ss-drawer__g"><p class="ss-drawer__t">' + esc(t(g.title)) + '</p>' + links + '</div>';
    }).join('');
    var languageOptions = (window.SMLang ? SMLang.SUPPORTED : ['en','ru']).map(function(code) {
      var name = window.SMLang && SMLang.NAMES ? SMLang.NAMES[code] : code.toUpperCase();
      return '<option data-no-translate value="' + code + '"' + (code === lang() ? ' selected' : '') + '>' + esc(name) + '</option>';
    }).join('');
    return groups + '<div class="ss-drawer__language"><label for="ssDrawerLanguage">' + esc(t({ru:'Язык',en:'Language'})) + '</label><select id="ssDrawerLanguage">' + languageOptions + '</select></div>' +
      '<div class="ss-drawer__auth"><button class="ss-drawer__auth-btn" id="ssDrawerAuth" type="button">' +
      svg('user') + '<span>' + (lang() === 'ru' ? 'Войти' : 'Log in') + '</span></button></div>';
  }

  function langHTML() {
    var cur = lang();
    var supported = window.SMLang ? SMLang.SUPPORTED : ['en','ru'];
    var names = window.SMLang ? SMLang.NAMES : {en:'English',ru:'Русский'};
    return '<div class="ss-lang" id="ssLang"><button class="ss-lang__btn" id="ssLangToggle" type="button" aria-haspopup="listbox" aria-expanded="false" aria-label="Language"><span data-no-translate>' + cur.toUpperCase() + '</span><i aria-hidden="true">⌄</i></button>' +
      '<div class="ss-lang__menu" id="ssLangMenu" role="listbox" aria-label="Language">' + supported.map(function(code){return '<button type="button" role="option" data-language="'+code+'" aria-selected="'+(code===cur)+'"><b data-no-translate>'+code.toUpperCase()+'</b><span data-no-translate>'+esc(names[code]||code)+'</span></button>'}).join('') + '</div></div>';
  }

  function headerHTML() {
    return '<header class="ss-head"><div class="ss-wrap ss-head__in">' +
      '<a class="ss-logo" href="' + siteUrl('/') + '"><span class="ss-logo__mark"><img src="/static/icon.png" alt=""></span>' +
      '<span class="ss-logo__txt"><b>Showcase</b><span>Maker</span></span></a>' +
      '<div class="ss-account-primary">' +
        '<a class="ss-pill" id="ssUser" href="' + siteUrl('/profile') + '" hidden></a>' +
        '<button class="ss-btn ss-btn--sm ss-login-primary" id="ssLogin" type="button">' + svg('user') + '<span>' +
          (lang() === 'ru' ? 'Войти' : 'Log in') + '</span></button>' +
      '</div>' +
      '<nav class="ss-nav">' + navHTML() + '</nav>' +
      '<span class="ss-head__sp"></span>' +
      '<div class="ss-head__right"><button class="ss-activate" id="ssActivate" type="button">' + svg('key') + '<span>' +
        (lang() === 'ru' ? 'Активация' : 'Activate') + '</span></button>' + langHTML() +
        '<button class="ss-btn ss-btn--sm ss-btn--logout" id="ssLogout" type="button" hidden style="background:#c0392b;color:#fff;border-color:#c0392b">' +
          (lang() === 'ru' ? 'Выйти' : 'Log out') + '</button>' +
        '<button class="ss-burger" id="ssBurger" type="button" aria-label="Menu"><span></span></button>' +
      '</div></div></header>' +
      '<div class="ss-drawer" id="ssDrawer">' + drawerHTML() + '</div>';
  }

  function maintenanceHTML() {
    return '<div class="ss-maintenance" id="ssMaintenance" role="status" hidden>' +
      '<span class="ss-maintenance__dot" aria-hidden="true"></span>' +
      '<span id="ssMaintenanceText"></span></div>';
  }

  function loadMaintenance() {
    var banner = document.getElementById('ssMaintenance');
    var textNode = document.getElementById('ssMaintenanceText');
    if (!banner || !textNode) return;
    fetch('/api/maintenance', { credentials:'same-origin', cache:'no-store' })
      .then(function(response){ return response.json(); })
      .then(function(state){
        var enabled = !!(state && state.enabled);
        banner.hidden = !enabled;
        textNode.textContent = enabled ? (state.message || accountCopy().maintenance) : '';
        requestAnimationFrame(function(){
          document.documentElement.style.setProperty('--maintenance-h', enabled ? banner.offsetHeight + 'px' : '0px');
        });
      })
      .catch(function(){ banner.hidden = true; document.documentElement.style.setProperty('--maintenance-h','0px'); });
  }

  function activationHTML() {
    var ru = lang() === 'ru';
    return '<div class="ss-activation" id="ssActivation" aria-hidden="true"><div class="ss-activation__card" role="dialog" aria-modal="true" aria-labelledby="ssActivationTitle">' +
      '<button class="ss-auth__close" id="ssActivationClose" type="button" aria-label="Close">×</button>' +
      '<div class="ss-activation__icon">' + svg('key') + '</div>' +
      '<p class="ss-auth__eyebrow">SHOWCASE MAKER / PRO</p>' +
      '<h2 id="ssActivationTitle">' + (ru ? 'Активировать ключ' : 'Activate a key') + '</h2>' +
      '<p class="ss-auth__sub">' + (ru ? 'Ключ привязывается к аккаунту. Один ключ нельзя использовать повторно.' : 'The key is linked to your account and cannot be reused.') + '</p>' +
      '<form class="ss-activation__form" id="ssActivationForm"><label><span>' + (ru ? 'Ключ доступа' : 'Access key') + '</span><div class="ss-activation__entry"><input id="ssActivationCode" autocomplete="off" spellcheck="false" placeholder="XXXX-XXXX-XXXX"><button type="submit">' + (ru ? 'Активировать' : 'Activate') + '</button></div></label><p class="ss-auth__state" id="ssActivationState"></p></form>' +
      '<div class="ss-activation__divide"><span>' + (ru ? 'Купить ключ' : 'Buy a key') + '</span></div>' +
      '<div class="ss-activation__shops"><a class="ss-shop ss-shop--funpay" href="https://funpay.com/lots/offer?id=76420307" target="_blank" rel="noopener"><span class="ss-shop__icon"><img src="/static/img/funpay-favicon.ico" alt=""></span><span><b>FunPay</b><small>' + (ru ? 'Код сразу после оплаты' : 'Instant code after payment') + '</small></span><i>↗</i></a><a class="ss-shop ss-shop--telegram" href="https://t.me/SteamMakerBot" target="_blank" rel="noopener"><span class="ss-shop__icon ss-shop__icon--telegram">➤</span><span><b>Telegram</b><small>' + (ru ? 'Покупка через бота' : 'Buy via bot') + '</small></span><i>↗</i></a><a class="ss-shop ss-shop--card" href="https://store.showcasemaker.com" target="_blank" rel="noopener"><span class="ss-shop__icon">' + svg('card') + '</span><span><b>' + (ru ? 'Оплата картой' : 'Pay by card') + '</b><small>' + (ru ? 'Банковская карта · защищённая оплата' : 'Bank card · secure checkout') + '</small></span><i>↗</i></a></div>' +
    '</div></div>';
  }

  function authHTML() {
    var ru = lang() === 'ru';
    return '<div class="ss-auth" id="ssAuth" aria-hidden="true"><div class="ss-auth__card" role="dialog" aria-modal="true" aria-labelledby="ssAuthTitle">' +
      '<button class="ss-auth__close" id="ssAuthClose" type="button" aria-label="Close">×</button>' +
      '<div class="ss-auth__mark"><img src="/static/icon.png" alt=""></div>' +
      '<p class="ss-auth__eyebrow">SHOWCASE MAKER / ACCOUNT</p>' +
      '<h2 id="ssAuthTitle">' + (ru ? 'С возвращением' : 'Welcome back') + '</h2>' +
      '<p class="ss-auth__sub" id="ssAuthSub">' + (ru ? 'Войди, чтобы сохранять проекты и использовать Pro.' : 'Log in to save projects and use Pro.') + '</p>' +
      '<form class="ss-auth__form" id="ssAuthForm">' +
        '<label id="ssAuthEmailWrap"><span>Email</span><input id="ssAuthEmail" type="email" autocomplete="email" required placeholder="name@example.com"></label>' +
        '<label id="ssAuthPassWrap"><span id="ssAuthPassLabel">' + (ru ? 'Пароль' : 'Password') + '</span><input id="ssAuthPass" type="password" autocomplete="current-password" minlength="10" required placeholder="••••••••••"></label>' +
        '<label id="ssAuthRepeatWrap" style="display:none"><span id="ssAuthRepeatLabel"></span><input id="ssAuthRepeat" type="password" autocomplete="new-password" minlength="10" placeholder="••••••••••"></label>' +
        '<label id="ssAuthCodeWrap" style="display:none"><span id="ssAuthCodeLabel">' + (ru ? 'Код из письма' : 'Code from email') + '</span><input id="ssAuthCode" type="text" inputmode="numeric" pattern="[0-9]{6}" autocomplete="one-time-code" minlength="6" maxlength="6" required placeholder="' + (ru ? 'ВАШ КОД' : 'YOUR CODE') + '"></label>' +
        '<p class="ss-auth__state" id="ssAuthState"></p>' +
        '<button class="ss-auth__submit" id="ssAuthSubmit" type="submit">' + (ru ? 'Войти' : 'Log in') + '</button>' +
      '</form>' +
      '<div class="ss-auth__div" id="ssAuthDiv"><span>' + (ru ? 'или войти через' : 'or continue with') + '</span></div>' +
      '<div class="ss-auth__oauth" id="ssAuthOauth" style="display:flex;flex-direction:column;gap:10px;width:100%;margin:0 0 8px">' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthDiscord" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(88,101,242,.45);background:rgba(88,101,242,.18);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.discord + '<span>Discord</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthGoogle" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.06);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.google + '<span>Google</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthTelegram" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(38,165,228,.45);background:rgba(38,165,228,.14);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.telegram + '<span>Telegram</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthSteam" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(27,40,56,.9);background:linear-gradient(180deg,#2a475e,#1b2838);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.steam + '<span>Steam</span></button>' +
      '</div>' +
      '<div id="ssTgHost" style="display:none;text-align:center;margin-top:8px"></div>' +
      '<button class="ss-auth__switch" id="ssAuthSwitch" type="button">' + (ru ? 'Нет аккаунта? Создать' : 'No account? Sign up') + '</button>' +
      '<button class="ss-auth__recover" id="ssAuthRecover" type="button"></button>' +
    '</div></div>';
  }

  function footerHTML() {
    var ru = lang() === 'ru';
    var links = [
      ['/app', ru ? 'Инструменты' : 'Tools'],
      ['/gallery', ru ? 'Галерея' : 'Gallery'],
      ['/profile', ru ? 'Профиль' : 'Profile'],
      ['/#pricing', ru ? 'Тарифы' : 'Pricing'],
      ['/#faq', 'FAQ'],
      ['/privacy', ru ? 'Политика конфиденциальности' : 'Privacy policy']
    ];
    return '<footer class="ss-foot"><div class="ss-wrap ss-foot__in">' +
      '<nav class="ss-foot__nav">' + links.map(function (l) {
        return '<a href="' + siteUrl(l[0]) + '"' + (l[2] ? ' target="_blank" rel="noopener noreferrer"' : '') + '>' + esc(l[1]) + '</a>';
      }).join('') + '</nav>' +
      '<a class="ss-foot__telegram" href="https://t.me/showcasemaker" target="_blank" rel="noopener noreferrer" aria-label="Telegram channel" title="Telegram">' + OAUTH_ICONS.telegram + '</a>' +
      '<p class="ss-foot__note">' +
      (ru ? 'Steam и Valve — товарные знаки Valve Corporation. Проект неофициальный и не связан с Valve.' : 'Steam and Valve are trademarks of Valve Corporation. This project is unofficial and not affiliated with Valve.') +
      '</p></div></footer>';
  }

  /* auth pill — one request, cached on window so a page can reuse it */
  function paintUser(me) {
    var pill = document.getElementById('ssUser');
    var login = document.getElementById('ssLogin');
    var logout = document.getElementById('ssLogout');
    var logged = !!(me && (me.logged_in === true || me.ok === true && me.email));
    /* use display — [hidden] is overridden by .ss-btn { display:inline-flex } */
    if (pill) {
      pill.hidden = !logged;
      pill.style.display = logged ? 'inline-flex' : 'none';

      // User pill -> PUBLIC profile (/profile/{username}).
      // Nav item "Profile" still opens the editor at /profile.
      var publicUsername = '';
      if (me) {
        publicUsername = (me.profile_username || me.username || '').trim();
        if (!publicUsername && me.display_name) {
          publicUsername = String(me.display_name).trim().toLowerCase().replace(/[^a-z0-9_-]+/g, '').slice(0, 24);
        }
        if (!publicUsername && me.email) {
          publicUsername = String(me.email).split('@')[0].toLowerCase().replace(/[^a-z0-9_-]+/g, '').slice(0, 24);
        }
      }
      if (logged && publicUsername) {
        pill.href = siteUrl('/profile/' + encodeURIComponent(publicUsername));
        pill.title = (lang() === 'ru' ? 'Публичный профиль' : 'Public profile');
      } else if (logged) {
        // last resort: still avoid editor — API will ensure username on next load
        pill.href = siteUrl('/profile');
        pill.title = (lang() === 'ru' ? 'Профиль' : 'Profile');
      } else {
        /* Never send a user-pill click to the editor. Bootstrap normally
           supplies profile_username; keep the fallback on the public route. */
        var fallbackName = me && ((me.email || '').split('@')[0] || me.display_name);
        pill.href = siteUrl('/profile/' + encodeURIComponent(fallbackName || 'profile'));
      }
    }
    if (login) {
      login.hidden = logged;
      login.style.setProperty('display', logged ? 'none' : 'inline-flex', 'important');
    }
    if (logout) {
      logout.hidden = !logged;
      /* The mobile stylesheet must be able to hide this desktop-only action. */
      logout.style.display = logged ? 'inline-flex' : 'none';
    }
    var drawerAuth = document.getElementById('ssDrawerAuth');
    if (drawerAuth) {
      drawerAuth.dataset.authAction = logged ? 'logout' : 'login';
      drawerAuth.classList.toggle('is-logout', logged);
      drawerAuth.innerHTML = svg('user') + '<span>' +
        (logged ? (lang() === 'ru' ? 'Выйти' : 'Log out') : (lang() === 'ru' ? 'Войти' : 'Log in')) + '</span>';
    }
    var activate = document.getElementById('ssActivate');

    // Activation button state:
    // FREE -> show Activate
    // TRIAL -> show live countdown
    // PERMANENT PRO -> hide activation button
    if (window.SS_PRO_TIMER) {
      clearInterval(window.SS_PRO_TIMER);
      window.SS_PRO_TIMER = null;
    }

    if (activate) {
      if (!logged || !me.is_pro) {
        activate.style.display = 'inline-flex';
        activate.disabled = false;
        activate.onclick = openActivation;
        activate.innerHTML = svg('key') + '<span>' +
          (lang() === 'ru' ? 'Активация' : 'Activate') + '</span>';
      } else if (me.pro_until) {
        var untilMs = Number(me.pro_until) * 1000;

        var renderProTimer = function () {
          var left = Math.max(0, untilMs - Date.now());

          if (left <= 0) {
            if (window.SS_PRO_TIMER) {
              clearInterval(window.SS_PRO_TIMER);
              window.SS_PRO_TIMER = null;
            }
            activate.style.display = 'inline-flex';
            activate.disabled = false;
            activate.onclick = openActivation;
            activate.innerHTML = svg('key') + '<span>' +
              (lang() === 'ru' ? 'Активация' : 'Activate') + '</span>';
            return;
          }

          var total = Math.floor(left / 1000);
          var hours = Math.floor(total / 3600);
          var minutes = Math.floor((total % 3600) / 60);
          var seconds = total % 60;

          var timer =
            String(hours).padStart(2, '0') + ':' +
            String(minutes).padStart(2, '0') + ':' +
            String(seconds).padStart(2, '0');

          activate.style.display = 'inline-flex';
          activate.disabled = true;
          activate.onclick = null;
          activate.innerHTML = '<span>⏱ ' + timer + '</span>';
        };

        renderProTimer();
        window.SS_PRO_TIMER = setInterval(renderProTimer, 1000);
      } else {
        // Permanent Pro
        activate.style.display = 'none';
        activate.onclick = null;
      }
    }

    if (!logged || !pill) return;
    var name = me.display_name || (me.email || '').split('@')[0] || 'profile';
    var av = me.avatar_url || '';
    pill.innerHTML =
      (av ? '<img class="ss-pill__av" src="' + esc(av) + '" alt="">'
          : '<span class="ss-pill__av"></span>') +
      '<span>' + esc(name) + '</span>' +
      '<i class="ss-pill__plan ' + (me.is_pro ? 'is-pro">PRO' : 'is-free">FREE') + '</i>';
  }

  // One request for the whole shell. /api/bootstrap returns everything
  // /api/auth/me did plus the unread count, so a page's own scripts can reuse
  // this response instead of asking the server about the same session again.
  var _mePromise = null;

  function loadMe() {
    _mePromise = fetch('/api/bootstrap', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .catch(function () { return { logged_in: false }; })
      .then(function (me) {
        window.SS_ME = me;
        paintUser(me);
        document.dispatchEvent(new CustomEvent('ss:me', { detail: me }));
        return me;
      });
    return _mePromise;
  }

  // The in-flight (or already finished) bootstrap, without starting a second
  // request. Use loadMe() instead when the state must be re-read - after a
  // login, for instance.
  function me() { return _mePromise || loadMe(); }

  function wire() {
    var burger = document.getElementById('ssBurger');
    var drawer = document.getElementById('ssDrawer');
    if (burger && drawer) {
      burger.addEventListener('click', function () {
        drawer.classList.toggle('is-open');
        document.body.style.overflow = drawer.classList.contains('is-open') ? 'hidden' : '';
      });
    }
    var langToggle = document.getElementById('ssLangToggle');
    if (langToggle) {
      langToggle.addEventListener('click', function () {
        var box = document.getElementById('ssLang');
        var open = !box.classList.contains('is-open');
        box.classList.toggle('is-open', open);
        langToggle.setAttribute('aria-expanded', String(open));
      });
      document.querySelectorAll('#ssLangMenu [data-language]').forEach(function (button) {
        button.addEventListener('click', function () {
          var code = button.dataset.language;
          if (window.SMLang && SMLang.switchTo) SMLang.switchTo(code);
        });
      });
      document.addEventListener('click', function (event) {
        var box = document.getElementById('ssLang');
        if (box && box.classList.contains('is-open') && !box.contains(event.target)) {
          box.classList.remove('is-open');langToggle.setAttribute('aria-expanded','false');
        }
      }, { once:false });
    }
    var drawerLanguage = document.getElementById('ssDrawerLanguage');
    if (drawerLanguage) drawerLanguage.addEventListener('change', function () {
      if (window.SMLang && SMLang.switchTo) SMLang.switchTo(drawerLanguage.value);
    });
    wireAuth();
    wireActivation();
  }

  function openActivation() {
    var modal = document.getElementById('ssActivation');
    if (!modal) return;
    modal.classList.add('is-open'); modal.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden';
    setTimeout(function () { document.getElementById('ssActivationCode')?.focus(); }, 40);
  }
  function closeActivation() {
    var modal = document.getElementById('ssActivation');
    if (!modal) return;
    modal.classList.remove('is-open'); modal.setAttribute('aria-hidden', 'true'); document.body.style.overflow = '';
  }
  function wireActivation() {
    var open = document.getElementById('ssActivate'), close = document.getElementById('ssActivationClose');
    var modal = document.getElementById('ssActivation'), form = document.getElementById('ssActivationForm');
    if (open) open.onclick = openActivation;
    if (close) close.onclick = closeActivation;
    if (modal) modal.onclick = function (e) { if (e.target === modal) closeActivation(); };
    if (form) form.onsubmit = function (e) {
      e.preventDefault();
      var code = (document.getElementById('ssActivationCode').value || '').trim();
      var state = document.getElementById('ssActivationState'), button = form.querySelector('button[type="submit"]');
      if (!code) { state.textContent = lang() === 'ru' ? 'Введите ключ.' : 'Enter a key.'; state.className = 'ss-auth__state is-bad'; return; }
      state.textContent = lang() === 'ru' ? 'Проверяем ключ…' : 'Checking key…'; state.className = 'ss-auth__state is-wait'; button.disabled = true;
      fetch('/api/unlock', { method:'POST', credentials:'same-origin', headers:Object.assign({'Content-Type':'application/json'},analyticsHeaders()), body:JSON.stringify({code:code}) })
        .then(function (r) { return r.json().then(function (j) { return { status:r.status, data:j }; }); })
        .then(function (x) {
          if (!x.data || !x.data.ok) {
            if (x.status === 401) { closeActivation(); openAuth('login'); throw new Error(lang() === 'ru' ? 'Сначала войдите в аккаунт.' : 'Log in first.'); }
            throw new Error((x.data && x.data.msg) || 'Activation failed');
          }
          state.textContent = x.data.msg || (lang() === 'ru' ? 'Pro активирован.' : 'Pro activated.'); state.className = 'ss-auth__state is-ok';
          return loadMe();
        }).catch(function (err) { state.textContent = err.message; state.className = 'ss-auth__state is-bad'; })
        .then(function () { button.disabled = false; });
    };
  }

  var authMode = 'login';
  function openAuth(mode) {
    authMode = mode === 'register' ? 'register' : 'login';
    var modal = document.getElementById('ssAuth');
    if (!modal) return;
    paintAuth();
    modal.classList.add('is-open'); modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(function () { var e = document.getElementById('ssAuthEmail'); if (e) e.focus(); }, 40);
  }
  function closeAuth() {
    var modal = document.getElementById('ssAuth');
    if (!modal) return;
    modal.classList.remove('is-open'); modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  function authErrorMessage(data, fallback) {
    var ru = lang() === 'ru';
    var messages = {
      invalid_email: ru ? 'Проверь адрес электронной почты.' : 'Check the email address.',
      rate_limited: ru ? 'Слишком много попыток. Попробуй немного позже.' : 'Too many attempts. Try again later.',
      verification_unavailable: ru ? 'Подтверждение почты временно недоступно.' : 'Email verification is temporarily unavailable.',
      delivery_failed: ru ? 'Не удалось отправить письмо. Попробуй позже.' : 'The email could not be sent. Try again later.',
      weak_password: ru ? 'Пароль должен содержать не менее 10 символов.' : 'Password must contain at least 10 characters.',
      invalid_code: ru ? 'Код неверный или срок его действия истёк.' : 'The code is incorrect or has expired.',
      account_unavailable: ru ? 'Не удалось создать аккаунт с этими данными.' : 'An account could not be created with these details.'
    };
    return messages[data && data.code] || (data && data.msg) || fallback;
  }
  function paintAuth() {
    var ru = lang() === 'ru', reg = authMode === 'register', ver = authMode === 'verify';
    var recover = authMode === 'reset_request', reset = authMode === 'reset_confirm';
    var copy = accountCopy();
    var title = document.getElementById('ssAuthTitle'), sub = document.getElementById('ssAuthSub');
    var submit = document.getElementById('ssAuthSubmit'), sw = document.getElementById('ssAuthSwitch');
    
    var emailWrap = document.getElementById('ssAuthEmailWrap');
    var passWrap = document.getElementById('ssAuthPassWrap');
    var repeatWrap = document.getElementById('ssAuthRepeatWrap');
    var codeWrap = document.getElementById('ssAuthCodeWrap');
    var div = document.getElementById('ssAuthDiv');
    var oauth = document.getElementById('ssAuthOauth');
    var recoverButton = document.getElementById('ssAuthRecover');
    
    if (emailWrap) emailWrap.style.display = (ver || reset) ? 'none' : 'block';
    if (passWrap) passWrap.style.display = (ver || recover) ? 'none' : 'block';
    if (repeatWrap) repeatWrap.style.display = reset ? 'grid' : 'none';
    if (codeWrap) {
        codeWrap.style.display = (ver || reset) ? 'grid' : 'none';
        var codeInp = document.getElementById('ssAuthCode');
        if (codeInp) codeInp.required = ver || reset;
    }
    var codeLabel = document.getElementById('ssAuthCodeLabel');
    var codeInput = document.getElementById('ssAuthCode');
    var passLabel = document.getElementById('ssAuthPassLabel');
    var repeatLabel = document.getElementById('ssAuthRepeatLabel');
    var passInput = document.getElementById('ssAuthPass');
    var repeatInput = document.getElementById('ssAuthRepeat');
    if (codeLabel) codeLabel.textContent = reset ? copy.codeLabel : (ru ? 'Код из письма' : 'Code from email');
    if (codeInput) codeInput.placeholder = reset ? copy.yourCode : (ru ? 'ВАШ КОД' : 'YOUR CODE');
    if (passLabel) passLabel.textContent = reset ? copy.newPassword : (ru ? 'Пароль' : 'Password');
    if (repeatLabel) repeatLabel.textContent = copy.repeatPassword;
    if (passInput) { passInput.required = !ver && !recover; passInput.autocomplete = reset ? 'new-password' : 'current-password'; }
    if (repeatInput) repeatInput.required = reset;
    if (div) div.style.display = (ver || recover || reset) ? 'none' : 'block';
    if (oauth) oauth.style.display = (ver || recover || reset) ? 'none' : 'flex';
    if (recoverButton) { recoverButton.style.display = authMode === 'login' ? 'block' : 'none'; recoverButton.textContent = copy.forgot; }

    if (title) {
        if (recover) title.textContent = copy.forgotTitle;
        else if (reset) title.textContent = copy.resetTitle;
        else if (ver) title.textContent = ru ? 'Введите код' : 'Enter code';
        else title.textContent = reg ? (ru ? 'Создать аккаунт' : 'Create account') : (ru ? 'С возвращением' : 'Welcome back');
    }
    if (sub) {
        if (recover) sub.textContent = copy.forgotSub;
        else if (reset) sub.textContent = copy.resetSub;
        else if (ver) sub.textContent = ru ? 'Код отправлен на ваш email.' : 'Code sent to your email.';
        else sub.textContent = reg ? (ru ? 'Один аккаунт для проектов, галереи и Pro.' : 'One account for projects, gallery and Pro.') : (ru ? 'Войди, чтобы сохранять проекты и использовать Pro.' : 'Log in to save projects and use Pro.');
    }
    if (submit) {
        if (recover) submit.textContent = copy.sendCode;
        else if (reset) submit.textContent = copy.savePassword;
        else if (ver) submit.textContent = ru ? 'Подтвердить' : 'Confirm';
        else submit.textContent = reg ? (ru ? 'Зарегистрироваться' : 'Sign up') : (ru ? 'Войти' : 'Log in');
    }
    if (sw) {
        if (recover || reset) sw.textContent = copy.backLogin;
        else if (ver) sw.textContent = ru ? 'Назад' : 'Back';
        else sw.textContent = reg ? (ru ? 'Уже есть аккаунт? Войти' : 'Already registered? Log in') : (ru ? 'Нет аккаунта? Создать' : 'No account? Sign up');
    }
  }
  function wireAuth() {
    var login = document.getElementById('ssLogin'), modal = document.getElementById('ssAuth');
    var drawerAuth = document.getElementById('ssDrawerAuth'), logout = document.getElementById('ssLogout');
    var close = document.getElementById('ssAuthClose'), sw = document.getElementById('ssAuthSwitch');
    var recoverButton = document.getElementById('ssAuthRecover');
    var form = document.getElementById('ssAuthForm');
    var oneTimeCode = document.getElementById('ssAuthCode');
    if (oneTimeCode) oneTimeCode.addEventListener('input', function () {
      oneTimeCode.value = oneTimeCode.value.replace(/\D/g, '').slice(0, 6);
    });
    if (login) login.onclick = function () { openAuth('login'); };
    if (logout) logout.onclick = performLogout;
    if (drawerAuth) drawerAuth.onclick = function () {
      if (drawerAuth.dataset.authAction === 'logout') { performLogout(); return; }
      var drawer = document.getElementById('ssDrawer');
      if (drawer) drawer.classList.remove('is-open');
      document.body.style.overflow = '';
      openAuth('login');
    };
    if (close) close.onclick = closeAuth;
    if (modal) modal.onclick = function (e) { if (e.target === modal) closeAuth(); };
    if (sw) sw.onclick = function () { 
        if (authMode === 'reset_request' || authMode === 'reset_confirm') {
            authMode = 'login';
        } else if (authMode === 'verify') {
            authMode = 'register';
            var state = document.getElementById('ssAuthState');
            if (state) { state.textContent = ''; state.className = 'ss-auth__state'; }
        } else {
            authMode = authMode === 'login' ? 'register' : 'login'; 
        }
        paintAuth(); 
    };
    if (recoverButton) recoverButton.onclick = function () {
      authMode = 'reset_request';
      var state = document.getElementById('ssAuthState');
      if (state) { state.textContent = ''; state.className = 'ss-auth__state'; }
      paintAuth();
      setTimeout(function(){ document.getElementById('ssAuthEmail')?.focus(); }, 40);
    };
    if (form) form.onsubmit = function (e) {
      e.preventDefault();
      var email = document.getElementById('ssAuthEmail').value.trim();
      var password = document.getElementById('ssAuthPass').value;
      var code = document.getElementById('ssAuthCode') ? document.getElementById('ssAuthCode').value.trim() : '';
      var state = document.getElementById('ssAuthState'), submit = document.getElementById('ssAuthSubmit');
      var repeatPassword = document.getElementById('ssAuthRepeat') ? document.getElementById('ssAuthRepeat').value : '';
      var copy = accountCopy();

      if (authMode === 'reset_request') {
          state.textContent = copy.sending; state.className = 'ss-auth__state is-wait'; submit.disabled = true;
          fetch('/api/auth/password-reset/request', {method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email})})
            .then(function(r){return r.json()}).then(function(j){
              if(!j||!j.ok)throw new Error(resetErrorMessage(j));
              state.textContent = copy.recoverySent; state.className = 'ss-auth__state is-ok';
              authMode = 'reset_confirm'; paintAuth();
              setTimeout(function(){ document.getElementById('ssAuthCode')?.focus(); },40);
            }).catch(function(err){state.textContent=err.message;state.className='ss-auth__state is-bad'})
            .then(function(){submit.disabled=false});
          return;
      }

      if (authMode === 'reset_confirm') {
          if (password.length < 10) { state.textContent=copy.passwordShort; state.className='ss-auth__state is-bad'; return; }
          if (password !== repeatPassword) { state.textContent=copy.passwordMismatch; state.className='ss-auth__state is-bad'; return; }
          state.textContent=copy.resetting;state.className='ss-auth__state is-wait';submit.disabled=true;
          fetch('/api/auth/password-reset/confirm',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:email,code:code,new_password:password})})
            .then(function(r){return r.json()}).then(function(j){
              if(!j||!j.ok)throw new Error(resetErrorMessage(j));
              authMode='login';paintAuth();state.textContent=copy.resetDone;state.className='ss-auth__state is-ok';
              document.getElementById('ssAuthPass').value='';document.getElementById('ssAuthRepeat').value='';document.getElementById('ssAuthCode').value='';
            }).catch(function(err){state.textContent=err.message;state.className='ss-auth__state is-bad'})
            .then(function(){submit.disabled=false});
          return;
      }
      
      if (authMode === 'register') {
          state.textContent = lang() === 'ru' ? 'Отправляем код…' : 'Sending code…'; state.className = 'ss-auth__state is-wait';
          submit.disabled = true;
          fetch('/api/auth/send-code', { method:'POST', credentials:'include', headers:Object.assign({'Content-Type':'application/json'},analyticsHeaders()), body:JSON.stringify({email:email}) })
            .then(function (r) { return r.json(); }).then(function (j) {
              if (!j || !j.ok) throw new Error(authErrorMessage(j, lang() === 'ru' ? 'Не удалось отправить код.' : 'Failed to send code.'));
              state.textContent = ''; state.className = 'ss-auth__state';
              authMode = 'verify';
              paintAuth();
              setTimeout(function(){ document.getElementById('ssAuthCode').focus(); }, 40);
            }).catch(function (err) { state.textContent = err.message; state.className = 'ss-auth__state is-bad'; })
            .then(function () { submit.disabled = false; });
          return;
      }
      
      state.textContent = lang() === 'ru' ? 'Подключаем…' : 'Connecting…'; state.className = 'ss-auth__state is-wait';
      submit.disabled = true;
      var path = authMode === 'verify' ? '/api/auth/register' : '/api/auth/login';
      var bodyObj = {email:email,password:password};
      if (authMode === 'verify') bodyObj.code = code;
      
      fetch(path, { method:'POST', credentials:'include', headers:Object.assign({'Content-Type':'application/json'},analyticsHeaders()), body:JSON.stringify(bodyObj) })
        .then(function (r) { return r.json(); }).then(function (j) {
          if (!j || !j.ok) throw new Error(authErrorMessage(j, lang() === 'ru' ? 'Не удалось выполнить вход.' : 'Authentication failed.'));
          state.textContent = lang() === 'ru' ? 'Готово' : 'Done'; state.className = 'ss-auth__state is-ok';
          return loadMe().then(function () { setTimeout(closeAuth, 350); });
        }).catch(function (err) { state.textContent = err.message; state.className = 'ss-auth__state is-bad'; })
        .then(function () { submit.disabled = false; });
    };

    // The shell can be loaded either before or after DOMContentLoaded. OAuth
    // used to be wired only in the first case, leaving visible but inert social
    // buttons on some page loads. Bind them whenever the shell is (re)mounted.
    function openOAuth(path, name) {
      fetch(path, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.ok || !d.url) { alert((d && d.msg) || (name + ' not configured')); return; }
          var w = window.open(d.url, name + '_oauth', 'width=560,height=720');
          if (!w) location.href = d.url;
        })
        .catch(function (e) { alert(String(e)); });
    }
    var providers = {
      ssAuthDiscord: ['/api/auth/discord/login', 'discord'],
      ssAuthGoogle: ['/api/auth/google/login', 'google'],
      ssAuthSteam: ['/api/auth/steam/login', 'steam']
    };
    Object.keys(providers).forEach(function (id) {
      var btn = document.getElementById(id), cfg = providers[id];
      if (btn) btn.onclick = function () { openOAuth(cfg[0], cfg[1]); };
    });
    var telegram = document.getElementById('ssAuthTelegram');
    if (telegram) telegram.onclick = function () {
      fetch('/api/auth/telegram/config', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.ok || !d.bot_username) { alert((d && d.msg) || 'Telegram not configured'); return; }
          var host = document.getElementById('ssTgHost');
          if (!host) return;
          host.style.display = 'block'; host.innerHTML = '';
          window.onTelegramAuth = function (user) {
            fetch('/api/auth/telegram', {
              method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'},
              body:JSON.stringify(user)
            }).then(function (r) { return r.json(); }).then(function (j) {
              if (!j || !j.ok) { alert((j && j.msg) || 'Telegram auth failed'); return; }
              location.reload();
            });
          };
          var script = document.createElement('script');
          script.src = 'https://telegram.org/js/telegram-widget.js?22';
          script.setAttribute('data-telegram-login', d.bot_username);
          script.setAttribute('data-size', 'large');
          script.setAttribute('data-radius', '12');
          script.setAttribute('data-onauth', 'onTelegramAuth(user)');
          script.setAttribute('data-request-access', 'write');
          host.appendChild(script);
        }).catch(function (e) { alert(String(e)); });
    };
  }

  function performLogout() {
    fetch('/api/auth/logout', { method:'POST', credentials:'same-origin' })
      .then(function () {
        try { localStorage.removeItem('sm_session'); } catch (e) {}
        location.reload();
      });
  }

  function mount() {
    var head = document.getElementById('ssHeadHost');
    var foot = document.getElementById('ssFootHost');
    if (!document.getElementById('ssMaintenance')) {
      document.body.insertAdjacentHTML('afterbegin', maintenanceHTML());
    }
    if (head) head.innerHTML = headerHTML() + authHTML() + activationHTML();
    if (foot) foot.innerHTML = footerHTML();
    document.querySelectorAll('[data-privacy-link]').forEach(function (link) {
      link.href = siteUrl('/privacy');
      link.textContent = lang() === 'ru' ? 'Политика конфиденциальности' : 'Privacy policy';
    });
    wire();
    paintUser(window.SS_ME);
    loadMaintenance();
  }

  window.SSShell = { mount: mount, loadMe: loadMe, me: me, lang: lang, t: t, esc: esc, openAuth: openAuth, closeAuth: closeAuth, openActivation: openActivation, closeActivation: closeActivation };

  function initialize() {
    mount();
    // Old bearer tokens in localStorage are deliberately discarded. The
    // server-owned HttpOnly cookie is the only session source.
    try { localStorage.removeItem('sm_session'); } catch (e) {}
    loadMe();
    var authQuery = new URLSearchParams(location.search).get('auth');
    if (authQuery === '1' || authQuery === 'register') openAuth('register');
  }

  if (!window._ssOAuthMsgBound) {
    window._ssOAuthMsgBound = true;
    window.addEventListener('message', function (ev) {
      if (ev.origin !== location.origin || !ev.data) return;
      if (ev.data.type === 'discord_login' || ev.data.type === 'google_login' ||
          ev.data.type === 'telegram_login' || ev.data.type === 'steam_login') location.reload();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize, { once:true });
  else initialize();
})();
