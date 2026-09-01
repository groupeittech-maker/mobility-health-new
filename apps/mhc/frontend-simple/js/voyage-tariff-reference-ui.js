/**
 * Affichage commun du tarifaire voyage (API /admin/tarification/voyage-reference)
 * : tableau PRIMES + FRAIS DE SERVICES + surprimes âge — aligné sur le moteur backend.
 */
(function (global) {
    function escapeHtml(s) {
        if (s == null || s === '') return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatFcfa(n) {
        if (n == null || Number.isNaN(Number(n))) return '—';
        return `${new Intl.NumberFormat('fr-FR').format(Number(n))} FCFA`;
    }

    /**
     * @param {HTMLElement} rootEl
     * @param {() => Promise<object>} fetchReference - doit retourner le JSON voyage-reference
     */
    async function renderVoyageTariffReference(rootEl, fetchReference) {
        if (!rootEl) return;
        rootEl.innerHTML =
            '<p class="text-muted small" style="margin:0;">Chargement du tarifaire…</p>';
        try {
            const d = await fetchReference();
            const bands = d.duration_bands || [];
            const zones = d.zones_order || [];
            const labels = d.zone_row_labels_fr || {};
            const primes = d.primes_fcfa_by_zone || {};
            const frais = d.frais_fcfa_by_zone || {};

            let html = '<div class="mh-voyage-ref">';
            html += '<div class="mh-voyage-ref__head">';
            html += '<h3 class="mh-voyage-ref__title">PRIMES &amp; FRAIS DE SERVICES</h3>';
            const pctFrais = d.frais_sur_prime_pct != null ? String(d.frais_sur_prime_pct) : '15';
            html +=
                `<p class="mh-voyage-ref__subtitle">Par zone tarifaire (parcours résidence → destination) et durée. Frais de services = ${escapeHtml(pctFrais)}&nbsp;% de la prime <strong>après</strong> surprime âge (ci-dessous : indicatif 18–69 ans, sans surprime). Devise : FCFA.</p>`;
            html += '</div>';

            html += '<div class="mh-primes-table-wrap">';
            html += '<table class="mh-primes-table">';
            html += '<thead><tr><th scope="col">Zone / durée</th>';
            bands.forEach((b) => {
                html += `<th scope="col">${escapeHtml(b.label_fr)}</th>`;
            });
            html += '</tr></thead><tbody>';
            zones.forEach((zc) => {
                const label = labels[zc] || zc;
                html += '<tr>';
                html += `<th scope="row"><span class="mh-primes-zone-label">${escapeHtml(label)}</span><span class="mh-primes-zone-code">${escapeHtml(zc)}</span></th>`;
                bands.forEach((b) => {
                    const rowP = primes[zc] || {};
                    const rowF = frais[zc] || {};
                    const vp = rowP[b.code];
                    const vf = rowF[b.code];
                    let cell = '—';
                    if (vp != null && vf != null) {
                        cell = `<span class="mh-primes-amount">${formatFcfa(vp)}</span>`;
                        cell += `<br><span class="mh-primes-frais">+ frais ${formatFcfa(vf)}</span>`;
                    } else if (vp != null) {
                        cell = `<span class="mh-primes-amount">${formatFcfa(vp)}</span>`;
                    }
                    html += `<td class="mh-primes-cell">${cell}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table></div>';

            html += '<div class="mh-surprime-block">';
            html += '<h4 class="mh-surprime-block__title">Surprimes âge</h4>';
            html +=
                '<p class="mh-surprime-block__hint">Pourcentage <strong>ajouté</strong> sur la prime du tableau. Les frais de services sont ensuite recalculés en pourcentage de la <strong>nouvelle</strong> prime (prime + surprime). Référence 18–69 ans : pas de surprime. Valeurs par défaut si le produit laisse les champs vides.</p>';
            html += '<table class="mh-surprime-table">';
            html += '<thead><tr><th>Tranche d’âge</th><th>Surprime</th></tr></thead><tbody>';
            (d.surprime_labels_fr || []).forEach((row) => {
                html += `<tr><td>${escapeHtml(row.tranche)}</td><td><strong>+${escapeHtml(row.pct)}&nbsp;%</strong></td></tr>`;
            });
            html += `<tr class="mh-surprime-table__ref"><td>${escapeHtml('18 à 69 ans')}</td><td>${escapeHtml(d.reference_18_69 || '0 %')}</td></tr>`;
            html += '</tbody></table></div>';

            if (d.engine_note) {
                html += `<p class="mh-voyage-ref__note text-muted small">${escapeHtml(d.engine_note)}</p>`;
            }
            html += '</div>';
            rootEl.innerHTML = html;
        } catch (e) {
            rootEl.innerHTML = `<div class="alert alert-error" style="margin:0;">Impossible de charger le tarifaire : ${escapeHtml(e.message || 'erreur')}</div>`;
        }
    }

    global.renderVoyageTariffReference = renderVoyageTariffReference;
})(typeof window !== 'undefined' ? window : globalThis);
