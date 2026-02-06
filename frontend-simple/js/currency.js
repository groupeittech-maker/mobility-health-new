(function () {
    const STORAGE_KEY = 'mh_currency_pref_v1';
    const DEFAULT_LOCALE = 'fr-FR';
    const DEFAULT_REGION = 'SN';
    const DEFAULT_CURRENCY = 'XOF';
    const EXPIRATION_MS = 1000 * 60 * 60 * 12; // 12 heures

    const REGION_TO_CURRENCY = {
        SN: 'XOF',
        CI: 'XOF',
        BJ: 'XOF',
        BF: 'XOF',
        ML: 'XOF',
        NE: 'XOF',
        TG: 'XOF',
        GW: 'XOF',
        CG: 'XAF',
        CM: 'XAF',
        TD: 'XAF',
        GA: 'XAF',
        GQ: 'XAF',
        CF: 'XAF',
        FR: 'EUR',
        BE: 'EUR',
        LU: 'EUR',
        DE: 'EUR',
        ES: 'EUR',
        IT: 'EUR',
        PT: 'EUR',
        NL: 'EUR',
        IE: 'EUR',
        US: 'USD',
        GB: 'GBP',
        CA: 'CAD',
        CH: 'CHF',
        MA: 'MAD',
        DZ: 'DZD',
        TN: 'TND',
        ZA: 'ZAR',
        NG: 'XAF',
        GH: 'GHS',
        KE: 'KES',
        AE: 'AED',
    };

    const TIMEZONE_TO_REGION = {
        'africa/dakar': 'SN',
        'africa/abidjan': 'CI',
        'africa/bamako': 'ML',
        'africa/niamey': 'NE',
        'africa/accra': 'GH',
        'africa/douala': 'CM',
        'africa/lagos': 'NG',
        'africa/casablanca': 'MA',
        'africa/tunis': 'TN',
        'africa/algiers': 'DZ',
        'europe/paris': 'FR',
        'europe/brussels': 'BE',
        'europe/luxembourg': 'LU',
        'europe/madrid': 'ES',
        'europe/berlin': 'DE',
        'europe/rome': 'IT',
        'europe/london': 'GB',
        'america/new_york': 'US',
        'america/toronto': 'CA',
        'america/montreal': 'CA',
    };

    const CURRENCY_SYMBOLS = {
        XOF: 'F CFA',
        XAF: 'F CFA',
        EUR: '€',
        USD: '$',
        CAD: '$',
        GBP: '£',
        CHF: 'CHF',
        MAD: 'د.م.',
        DZD: 'دج',
        TND: 'د.ت',
        ZAR: 'R',
        GHS: '₵',
        KES: 'KSh',
        AED: 'د.إ',
    };

    const safeJSONParse = (value) => {
        try {
            return JSON.parse(value);
        } catch (error) {
            return null;
        }
    };

    const readStoredPreference = () => {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                return null;
            }
            return safeJSONParse(raw);
        } catch {
            return null;
        }
    };

    const persistPreference = (pref) => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(pref));
        } catch {
            // stockage indisponible (mode privé, quota plein, ...).
        }
    };

    const detectLocale = () => {
        if (Array.isArray(navigator.languages) && navigator.languages.length > 0) {
            return navigator.languages[0];
        }
        return navigator.language || DEFAULT_LOCALE;
    };

    const extractRegionFromLocale = (locale) => {
        if (!locale) {
            return null;
        }
        const match = locale.match(/-([A-Z]{2})/i);
        return match ? match[1].toUpperCase() : null;
    };

    const detectRegion = (locale) => {
        const fromLocale = extractRegionFromLocale(locale);
        if (fromLocale) {
            return fromLocale;
        }
        try {
            const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').toLowerCase();
            return TIMEZONE_TO_REGION[tz] || null;
        } catch {
            return null;
        }
    };

    const computePreference = () => {
        const locale = detectLocale() || DEFAULT_LOCALE;
        const region = detectRegion(locale) || DEFAULT_REGION;
        const currency = REGION_TO_CURRENCY[region] || DEFAULT_CURRENCY;
        const preference = {
            locale,
            region,
            currency,
            updatedAt: Date.now(),
        };
        persistPreference(preference);
        return preference;
    };

    const resolvePreference = () => {
        const stored = readStoredPreference();
        if (stored && stored.currency && Date.now() - (stored.updatedAt || 0) < EXPIRATION_MS) {
            return stored;
        }
        return computePreference();
    };

    let preference = resolvePreference();

    const getLocale = () => preference.locale || DEFAULT_LOCALE;
    const getCurrency = () => (preference.currency || DEFAULT_CURRENCY).toUpperCase();
    const getRegion = () => preference.region || DEFAULT_REGION;
    const getSymbol = (code = getCurrency()) => CURRENCY_SYMBOLS[code.toUpperCase()] || code.toUpperCase();

    const formatAmount = (amount, options = {}) => {
        if (amount === null || amount === undefined || amount === '') {
            return '—';
        }
        const numeric = Number(amount);
        if (!Number.isFinite(numeric)) {
            return '—';
        }
        const locale = options.locale || getLocale();
        const currency = options.currency || getCurrency();
        const formatterOptions = {
            style: 'currency',
            currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
            ...options,
        };
        try {
            return new Intl.NumberFormat(locale, formatterOptions).format(numeric);
        } catch {
            return `${numeric.toFixed(0)} ${currency}`;
        }
    };

    const refreshPreference = () => {
        preference = computePreference();
        updateCurrencyPlaceholders();
        return preference;
    };

    const setCurrency = (currencyCode) => {
        if (!currencyCode) {
            return;
        }
        preference = {
            ...preference,
            currency: currencyCode.toUpperCase(),
            updatedAt: Date.now(),
        };
        persistPreference(preference);
        updateCurrencyPlaceholders();
    };

    const updateCurrencyPlaceholders = (root = document) => {
        if (!root || typeof root.querySelectorAll !== 'function') {
            return;
        }
        const symbol = getSymbol();
        const code = getCurrency();
        root.querySelectorAll('[data-currency-symbol]').forEach((node) => {
            node.textContent = symbol;
        });
        root.querySelectorAll('[data-currency-code]').forEach((node) => {
            node.textContent = code;
        });
    };

    document.addEventListener('DOMContentLoaded', () => updateCurrencyPlaceholders());

    window.CurrencyHelper = {
        getLocale,
        getCurrency,
        getRegion,
        getSymbol,
        format: formatAmount,
        setCurrency,
        refresh: refreshPreference,
        updateCurrencyPlaceholders,
    };
})();

