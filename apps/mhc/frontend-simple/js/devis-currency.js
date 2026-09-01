/**
 * Format des montants devis / souscriptions : XAF (FCFA) par défaut.
 */
(function (global) {
    'use strict';

    var DEFAULT = 'XAF';

    function formatMontantDevis(value, currencyCode, nonNumericLabel) {
        if (value === null || value === undefined || value === '') {
            return nonNumericLabel !== undefined ? nonNumericLabel : '—';
        }
        var num = typeof value === 'number' ? value : parseFloat(String(value).replace(',', '.'));
        if (!Number.isFinite(num)) {
            return nonNumericLabel !== undefined ? nonNumericLabel : String(value);
        }
        var code = (currencyCode && String(currencyCode).trim().toUpperCase()) || DEFAULT;
        try {
            return new Intl.NumberFormat('fr-FR', {
                style: 'currency',
                currency: code,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }).format(num);
        } catch (e) {
            return (
                num.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) +
                ' ' +
                code
            );
        }
    }

    global.DEFAULT_DEVISE_SOUSCRIPTION = DEFAULT;
    global.formatMontantDevis = formatMontantDevis;
})(typeof window !== 'undefined' ? window : globalThis);
