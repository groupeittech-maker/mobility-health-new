document.addEventListener('DOMContentLoaded', () => {
    const messageEl = document.getElementById('confirmMessage');
    if (!messageEl) return;

    const params = new URLSearchParams(window.location.search);
    const status = (params.get('status') || 'info').toLowerCase();
    const message = params.get('message') || 'Le traitement de votre activation est terminé.';

    messageEl.textContent = message;
    messageEl.classList.remove('confirm-status--success', 'confirm-status--error', 'confirm-status--info');

    if (status === 'success') {
        messageEl.classList.add('confirm-status--success');
    } else if (status === 'error') {
        messageEl.classList.add('confirm-status--error');
    } else {
        messageEl.classList.add('confirm-status--info');
    }
});
