(function () {
  'use strict';

  var DELETE_ERROR_COPY = {
    en: { unauthorized: 'Sign in again to delete your account.', active: 'Wait for active processing jobs to finish.', mismatch: 'The confirmation email does not match.', failed: 'Could not delete the account.' },
    ru: { unauthorized: 'Войдите снова, чтобы удалить аккаунт.', active: 'Дождитесь завершения активной обработки.', mismatch: 'Email для подтверждения не совпадает.', failed: 'Не удалось удалить аккаунт.' },
    de: { unauthorized: 'Melde dich erneut an, um dein Konto zu löschen.', active: 'Warte, bis die aktive Verarbeitung abgeschlossen ist.', mismatch: 'Die Bestätigungs-E-Mail stimmt nicht überein.', failed: 'Das Konto konnte nicht gelöscht werden.' },
    tr: { unauthorized: 'Hesabını silmek için yeniden giriş yap.', active: 'Etkin işlemlerin tamamlanmasını bekle.', mismatch: 'Onay e-posta adresi eşleşmiyor.', failed: 'Hesap silinemedi.' },
    fr: { unauthorized: 'Reconnectez-vous pour supprimer votre compte.', active: 'Attendez la fin des traitements en cours.', mismatch: 'L’adresse e-mail de confirmation ne correspond pas.', failed: 'Impossible de supprimer le compte.' },
    uk: { unauthorized: 'Увійдіть знову, щоб видалити обліковий запис.', active: 'Дочекайтеся завершення активної обробки.', mismatch: 'Email для підтвердження не збігається.', failed: 'Не вдалося видалити обліковий запис.' },
    es: { unauthorized: 'Vuelve a iniciar sesión para eliminar tu cuenta.', active: 'Espera a que finalicen los procesos activos.', mismatch: 'El correo de confirmación no coincide.', failed: 'No se pudo eliminar la cuenta.' },
    pt: { unauthorized: 'Inicia sessão novamente para eliminar a conta.', active: 'Aguarda a conclusão dos processamentos ativos.', mismatch: 'O email de confirmação não corresponde.', failed: 'Não foi possível eliminar a conta.' }
  };

  function byId(id) { return document.getElementById(id); }
  function language() {
    var value = window.SMLang && typeof window.SMLang.get === 'function'
      ? window.SMLang.get()
      : (document.documentElement.lang || 'en');
    return String(value || 'en').toLowerCase().split('-')[0];
  }
  function copy() {
    var catalog = window.SS_ACCOUNT_COPY || {};
    return catalog[language()] || catalog.en || {};
  }
  function deleteError(status) {
    var errors = DELETE_ERROR_COPY[language()] || DELETE_ERROR_COPY.en;
    if (status === 401) return errors.unauthorized;
    if (status === 409) return errors.active;
    if (status === 400) return errors.mismatch;
    return errors.failed;
  }
  function setState(text, kind) {
    var node = byId('accountPrivacyState');
    if (!node) return;
    node.textContent = text || '';
    node.className = 'account-state' + (kind ? ' ' + kind : '');
  }
  function accountEmail() {
    var field = byId('accountEmail');
    return String((field && field.value) || (window.SS_ME && window.SS_ME.email) || '').trim().toLowerCase();
  }
  function updateDeleteState() {
    var input = byId('accountDeleteEmail');
    var button = byId('accountDeleteButton');
    if (!input || !button) return;
    button.disabled = !accountEmail() || input.value.trim().toLowerCase() !== accountEmail();
  }
  function fileName(response) {
    var header = response.headers.get('content-disposition') || '';
    var match = header.match(/filename="?([^";]+)"?/i);
    return match ? match[1] : 'showcase-maker-account.json';
  }
  function downloadExport() {
    var button = byId('accountExportButton');
    var words = copy();
    if (!button) return;
    button.disabled = true;
    setState(words.preparingExport, 'wait');
    fetch('/api/auth/account-export', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) throw new Error(words.exportFailed);
        return Promise.all([response.blob(), Promise.resolve(fileName(response))]);
      })
      .then(function (result) {
        var url = URL.createObjectURL(result[0]);
        var link = document.createElement('a');
        link.href = url;
        link.download = result[1];
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        setState('');
      })
      .catch(function (error) { setState(error.message || words.exportFailed, 'bad'); })
      .finally(function () { button.disabled = false; });
  }
  function deleteAccount() {
    var input = byId('accountDeleteEmail');
    var button = byId('accountDeleteButton');
    var words = copy();
    var email = accountEmail();
    if (!input || !button || input.value.trim().toLowerCase() !== email) {
      setState(words.deleteMismatch, 'bad');
      updateDeleteState();
      return;
    }
    if (!window.confirm(words.deleteConfirm)) return;
    button.disabled = true;
    setState(words.deleting, 'wait');
    fetch('/api/auth/account-delete', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_email: email, confirm: 'DELETE' })
    })
      .then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (data) {
          if (!response.ok || !data.ok) throw new Error(deleteError(response.status));
          return data;
        });
      })
      .then(function () { window.location.assign('/'); })
      .catch(function (error) {
        setState(error.message || words.deleteFailed, 'bad');
        updateDeleteState();
      });
  }
  function paint() {
    var words = copy();
    var values = {
      accountExportTitle: words.exportTitle,
      accountExportDesc: words.exportDesc,
      accountExportButton: words.downloadData,
      accountDeleteTitle: words.deleteTitle,
      accountDeleteDesc: words.deleteDesc,
      accountDeleteButton: words.deleteAccount
    };
    Object.keys(values).forEach(function (id) {
      var node = byId(id);
      if (node) node.textContent = values[id] || '';
    });
    var input = byId('accountDeleteEmail');
    if (input) input.placeholder = words.confirmEmail || '';
    updateDeleteState();
  }
  function mount() {
    var host = byId('accountContent');
    if (!host || byId('accountPrivacyControls')) return;
    var section = document.createElement('div');
    section.className = 'account-section account-privacy-controls';
    section.id = 'accountPrivacyControls';
    section.innerHTML =
      '<div class="account-data-action">' +
        '<h3 id="accountExportTitle"></h3>' +
        '<p id="accountExportDesc"></p>' +
        '<button class="btn ghost full" type="button" id="accountExportButton"></button>' +
      '</div>' +
      '<div class="account-data-action account-data-action--danger">' +
        '<h3 id="accountDeleteTitle"></h3>' +
        '<p id="accountDeleteDesc"></p>' +
        '<input class="input" id="accountDeleteEmail" type="email" autocomplete="off" spellcheck="false">' +
        '<button class="btn full account-delete-button" type="button" id="accountDeleteButton" disabled></button>' +
      '</div>' +
      '<p class="account-state" id="accountPrivacyState" aria-live="polite"></p>';
    host.appendChild(section);
    byId('accountExportButton').addEventListener('click', downloadExport);
    byId('accountDeleteButton').addEventListener('click', deleteAccount);
    byId('accountDeleteEmail').addEventListener('input', updateDeleteState);
    document.addEventListener('ss:me', function () { setTimeout(updateDeleteState, 0); });
    window.addEventListener('sm:langchange', paint);
    paint();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
