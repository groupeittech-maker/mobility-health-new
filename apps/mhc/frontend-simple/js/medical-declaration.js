/**
 * Rendu partagé de la déclaration de santé (questionnaire médical de souscription).
 * Utilisé par hospital-doctor.js et hospital-alert-details.js — ne pas dupliquer.
 *
 * Le questionnaire enregistre chaque réponse sous deux noms (snake_case et
 * camelCase) et les réponses détaillées par voyageur dans `adult` / `enfants` :
 * le rendu déduplique et présente une ligne par question, « Oui » en tête avec
 * les personnes concernées et la précision de l'assuré.
 */
(function () {
    'use strict';

    const HEALTH_QUESTIONS = [
        ['malade_souscription', 'Malade au moment de la souscription'],
        ['malade_12_mois', 'Malade au cours des 12 derniers mois'],
        ['maladie_chronique', 'Maladie chronique'],
        ['enceinte', 'Grossesse en cours'],
        ['voyage_medical', 'Voyage pour raisons médicales'],
        ['activite_sportive_pro', 'Activité sportive professionnelle'],
    ];

    const KEY_ALIASES = {
        maladeSouscription: 'malade_souscription',
        malade12Mois: 'malade_12_mois',
        maladieChronique: 'maladie_chronique',
        pregnancy: 'enceinte',
        voyageMedical: 'voyage_medical',
        activiteSportivePro: 'activite_sportive_pro',
        activite: 'activite_sportive_pro',
        moisGrossesse: 'mois_grossesse',
        photoMedicale: 'photo_medicale',
    };

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatKeyLabel(key) {
        return String(key || '')
            .replace(/_/g, ' ')
            .replace(/([a-z])([A-Z])/g, '$1 $2')
            .replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function formatPlainValue(value) {
        if (value === null || value === undefined) return '—';
        if (typeof value === 'boolean') return value ? 'Oui' : 'Non';
        if (typeof value === 'number') return String(value);
        if (typeof value === 'string') {
            const trimmed = value.trim();
            if (!trimmed) return '—';
            if (trimmed.toLowerCase() === 'oui') return 'Oui';
            if (trimmed.toLowerCase() === 'non') return 'Non';
            if (trimmed.toLowerCase() === 'non_concerne') return 'Non concerné';
            return trimmed;
        }
        if (Array.isArray(value)) {
            return value.map((item) => formatPlainValue(item)).join(', ') || '—';
        }
        if (typeof value === 'object') {
            const parts = Object.entries(value).map(([k, v]) => `${formatKeyLabel(k)} : ${formatPlainValue(v)}`);
            return parts.join(' · ') || '—';
        }
        return String(value);
    }

    function getImageDataUrl(value) {
        if (typeof value === 'string' && value.trim().startsWith('data:image')) {
            return value.trim();
        }
        return null;
    }

    /** Déduplique les alias snake_case/camelCase — la clé canonique prime. */
    function normalize(raw) {
        const out = {};
        Object.entries(raw || {}).forEach(([key, value]) => {
            const canonical = KEY_ALIASES[key];
            if (!canonical) {
                out[key] = value;
            } else if (raw[canonical] === undefined && out[canonical] === undefined) {
                out[canonical] = value;
            }
        });
        return out;
    }

    function answerKind(value) {
        if (value === true) return 'yes';
        if (value === false) return 'no';
        const v = String(value ?? '').trim().toLowerCase();
        if (v === 'oui') return 'yes';
        if (v === 'non') return 'no';
        if (v === 'non_concerne') return 'na';
        return v ? 'other' : null;
    }

    /**
     * Construit le bloc « déclaration de santé ».
     * Retourne { html, used: Set } ou null si le questionnaire n'est pas à ce format.
     */
    function build(responses) {
        const persons = [];
        if (responses.adult && typeof responses.adult === 'object') {
            persons.push({
                nom: responses.adult.nom || 'Adulte',
                reponses: normalize(responses.adult.reponses),
            });
        }
        (Array.isArray(responses.enfants) ? responses.enfants : []).forEach((child) => {
            if (child && typeof child === 'object') {
                persons.push({ nom: child.nom || 'Enfant', reponses: normalize(child.reponses) });
            }
        });

        const used = new Set(['adult', 'enfants', 'voyageurs', 'adulte_voyage', 'version', 'mois_grossesse']);
        const rows = [];
        HEALTH_QUESTIONS.forEach(([key, label]) => {
            const personKinds = persons.map((person) => answerKind(person.reponses[key]));
            let kind = answerKind(responses[key]);
            if (!kind) {
                if (personKinds.includes('yes')) kind = 'yes';
                else if (personKinds.some(Boolean)) kind = 'no';
            }
            used.add(key);
            used.add(`${key}_precision`);
            used.add(`${key}_personnes`);
            if (!kind) {
                return;
            }
            const details = [];
            if (kind === 'yes') {
                let concerned = Array.isArray(responses[`${key}_personnes`]) ? responses[`${key}_personnes`] : [];
                if (!concerned.length) {
                    concerned = persons.filter((_, i) => personKinds[i] === 'yes').map((person) => person.nom);
                }
                if (concerned.length && persons.length > 1) {
                    details.push(`<span class="health-decl__detail-label">Concerne</span> ${escapeHtml(concerned.join(', '))}`);
                }
                if (key === 'enceinte' && responses.mois_grossesse != null && responses.mois_grossesse !== '') {
                    details.push(`<span class="health-decl__detail-label">Terme</span> ${escapeHtml(String(responses.mois_grossesse))}ᵉ mois`);
                }
                const precision =
                    responses[`${key}_precision`] ||
                    persons.map((person) => person.reponses[`${key}_precision`]).find(Boolean);
                if (precision) {
                    details.push(`<span class="health-decl__detail-label">Précision</span> ${escapeHtml(String(precision))}`);
                } else if (key !== 'enceinte') {
                    details.push('<span class="health-decl__detail-missing">Aucune précision fournie par l’assuré</span>');
                }
            }
            const badgeText =
                kind === 'yes' ? 'Oui' : kind === 'no' ? 'Non' : kind === 'na' ? 'Non concerné' : formatPlainValue(responses[key]);
            rows.push({ kind, html: `
            <li class="health-decl__row${kind === 'yes' ? ' is-yes' : ''}">
                <span class="health-decl__q">${escapeHtml(label)}</span>
                <span class="health-decl__badge health-decl__badge--${kind}">${escapeHtml(badgeText)}</span>
                ${details.length ? `<div class="health-decl__detail">${details.map((d) => `<div>${d}</div>`).join('')}</div>` : ''}
            </li>` });
        });
        // Anciens questionnaires (texte libre) : une ou deux questions communes ne
        // suffisent pas à conclure « aucun antécédent ».
        if (rows.length < 3) {
            return null;
        }

        let photoUrl = null;
        ['photo_medicale', 'photo_identity', 'photoMedicale'].forEach((key) => {
            photoUrl = photoUrl || getImageDataUrl(responses[key]);
            used.add(key);
        });
        used.add('declaration_sante');
        used.add('date_soumission');

        const yesCount = rows.filter((row) => row.kind === 'yes').length;
        const summary = yesCount
            ? `<strong>${yesCount} point${yesCount > 1 ? 's' : ''} d’attention</strong><span>sur ${rows.length} questions — détail ci-dessous</span>`
            : `<strong>Aucun antécédent déclaré</strong><span>${rows.length} questions, toutes négatives</span>`;

        const meta = [];
        const travelers = Array.isArray(responses.voyageurs) ? responses.voyageurs : persons.map((person) => person.nom);
        if (travelers.length > 1) {
            meta.push(`Voyageurs : ${escapeHtml(travelers.join(', '))}`);
        }
        if (responses.date_soumission) {
            const d = new Date(responses.date_soumission);
            const when = Number.isNaN(d.getTime()) ? '' : ` le ${escapeHtml(d.toLocaleString('fr-FR', { dateStyle: 'long', timeStyle: 'short' }))}`;
            meta.push(`Déclaré${responses.declaration_sante ? ' et certifié exact' : ''} par l’assuré${when}`);
        }

        // Les « Oui » remontent en tête de liste.
        rows.sort((a, b) => (b.kind === 'yes') - (a.kind === 'yes'));
        const html = `
        <div class="health-decl">
            <div class="health-decl__head">
                ${photoUrl ? `<img class="health-decl__photo" src="${photoUrl.replace(/"/g, '&quot;')}" alt="Photo de l’assuré">` : ''}
                <div class="health-decl__summary health-decl__summary--${yesCount ? 'alert' : 'ok'}">${summary}</div>
            </div>
            <ul class="health-decl__list">${rows.map((row) => row.html).join('')}</ul>
            ${meta.length ? `<p class="health-decl__meta">${meta.join(' · ')}</p>` : ''}
        </div>`;
        return { html, used };
    }

    window.MhMedicalDeclaration = { build, normalize, formatPlainValue, formatKeyLabel };
})();
