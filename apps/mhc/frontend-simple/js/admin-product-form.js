// Formulaire produit de tarification (maquette : infos générales, zones, tarifs,
// surprimes, décompte A+B+C+D, courtage, répartition + résumé temps réel).
(function () {
    'use strict';

    let productId = null;
    let logoDataUrl = null;
    let surprimes = [];

    function $(id) { return document.getElementById(id); }
    function esc(v) {
        const d = document.createElement('div');
        d.textContent = v == null ? '' : String(v);
        return d.innerHTML;
    }
    function toast(msg, isError) {
        const t = $('toast');
        t.textContent = msg;
        t.className = 'toast show' + (isError ? ' error' : '');
        setTimeout(() => { t.className = 'toast'; }, 3500);
    }
    function num(id) {
        const v = parseFloat($(id).value);
        return Number.isFinite(v) ? v : null;
    }
    function fmt(n) {
        if (n == null || !Number.isFinite(n)) return '—';
        return n.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
    }

    // ---------- Chargement des référentiels ----------
    async function loadReferentials() {
        try {
            const assureurs = await apiCall('/assureurs/');
            $('fAssureur').innerHTML = '<option value="">— Sélectionner —</option>' +
                (assureurs || []).map(a => `<option value="${a.id}" data-pays="${esc(a.pays || '')}">${esc(a.nom || a.name)}</option>`).join('');
        } catch (_) { /* liste vide */ }
        try {
            const reassureurs = await apiCall('/admin/reassureurs/');
            $('fReassureur').innerHTML = '<option value="">— Sélectionner —</option>' +
                (reassureurs || []).filter(r => r.est_actif !== false)
                    .map(r => `<option value="${r.id}" data-cession="${r.cession_defaut_pct ?? ''}" data-comm="${r.commission_cession_defaut_pct ?? ''}">${esc(r.nom)}</option>`).join('');
        } catch (_) { /* non autorisé : select vide */ }
        try {
            const zones = await apiCall('/admin/tarification/zones');
            $('zonesChecks').innerHTML = (zones || []).map(z =>
                `<label style="display:flex;align-items:center;gap:.35rem;font-size:.8rem;border:1px solid #e2e4f0;border-radius:.5rem;padding:.4rem .7rem;cursor:pointer"><input type="checkbox" class="zone-check" value="${esc(z.nom || z.code)}"> ${esc(z.nom || z.code)}</label>`
            ).join('') || '<span style="color:#8a8fa3;font-size:.8rem">Aucune zone configurée — gérez les zones dans Tarification.</span>';
        } catch (_) {
            $('zonesChecks').innerHTML = '<span style="color:#8a8fa3;font-size:.8rem">Zones non accessibles.</span>';
        }
    }

    // ---------- Pré-remplissage (édition) ----------
    async function loadProduct() {
        if (!productId) return;
        $('pageTitle').textContent = 'Modifier le produit';
        $('bcCurrent').textContent = 'Modifier le produit';
        const p = await apiCall(`/admin/products/${productId}`);
        $('fNom').value = p.nom || '';
        $('fCode').value = p.code || '';
        $('fCode').readOnly = true;
        $('fVersion').value = p.version || '';
        $('fStatut').value = p.est_actif ? 'actif' : 'inactif';
        $('fPays').value = p.pays || '';
        $('fCurrency').value = p.currency || 'XAF';
        $('fAssureur').value = p.assureur_id || '';
        $('fReassureur').value = p.reassureur_id || '';
        $('fCout').value = p.cout ?? '';
        $('fRetention').value = p.retention_assureur_pct ?? '';
        $('fCession').value = p.cession_reassureur_pct ?? '';
        $('fCommCession').value = p.commission_cession_pct ?? '';
        $('fCoutPolice').value = p.cout_police_forfait ?? '';
        $('fTaxe').value = p.taxe_pct ?? '';
        $('fTaxeAdd').value = p.taxe_additionnelle_pct ?? '';
        $('fCourtage').value = p.commission_courtage_pct ?? '';
        if (p.logo_url) { $('logoPreview').src = p.logo_url; $('logoPreview').style.display = 'block'; logoDataUrl = p.logo_url; }
        const zones = (p.zones_geographiques && p.zones_geographiques.zones) || [];
        document.querySelectorAll('.zone-check').forEach(c => { c.checked = zones.includes(c.value); });
        $('fPaysExclus').value = ((p.zones_geographiques && p.zones_geographiques.pays_exclus) || []).join(', ');

        // Surprimes table
        try {
            surprimes = await apiCall(`/admin/products/${productId}/surprimes`);
        } catch (_) { surprimes = []; }
        renderSurprimes();
        // Grille finale (lecture)
        loadGrilleFinale();
        refreshSummary();
    }

    async function loadGrilleFinale() {
        try {
            const g = await apiCall(`/admin/products/${productId}/grille-finale`);
            const rows = (g && g.rows) || [];
            if (!rows.length) return;
            $('tarifsBody').innerHTML = rows.slice(0, 40).map(r =>
                `<tr><td>${esc(r.zone_nom || r.zone_id)}</td><td>${esc(r.fenetre_label || r.fenetre_duree_id)}</td><td>${esc(r.tranche_label || r.tranche_age_id)}</td><td style="text-align:right">${fmt(r.prix)} ${esc(r.devise || 'XAF')}</td><td><a href="admin-tarification.html" style="font-size:.72rem;color:#6c5ce7">Modifier</a></td></tr>`
            ).join('');
        } catch (_) { /* laisser le message par défaut */ }
    }

    // ---------- Surprimes ----------
    function renderSurprimes() {
        $('surprimesBody').innerHTML = surprimes.map((s, i) => `
            <tr>
                <td><input type="number" value="${s.age_min ?? ''}" data-i="${i}" data-f="age_min" class="sp-in" min="0" max="130"></td>
                <td><input type="number" value="${s.age_max ?? ''}" data-i="${i}" data-f="age_max" class="sp-in" min="0" max="130"></td>
                <td><select data-i="${i}" data-f="formule" class="sp-in">
                    <option value="pourcentage" ${s.formule !== 'montant_fixe' ? 'selected' : ''}>Surprime (%)</option>
                    <option value="montant_fixe" ${s.formule === 'montant_fixe' ? 'selected' : ''}>Montant fixe</option>
                </select></td>
                <td><input type="number" value="${s.taux_pct ?? 0}" data-i="${i}" data-f="taux_pct" class="sp-in" step="0.01" min="0"></td>
                <td><input type="number" value="${s.montant_fixe ?? ''}" data-i="${i}" data-f="montant_fixe" class="sp-in" step="0.01" min="0"></td>
                <td><button type="button" class="pf-delrow" data-del="${i}">✕</button></td>
            </tr>`).join('');
        $('surprimesBody').querySelectorAll('.sp-in').forEach(el => el.addEventListener('change', e => {
            const i = +e.target.dataset.i, f = e.target.dataset.f;
            surprimes[i][f] = f === 'formule' ? e.target.value : (e.target.value === '' ? null : +e.target.value);
        }));
        $('surprimesBody').querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', e => {
            surprimes.splice(+e.target.dataset.del, 1);
            renderSurprimes();
        }));
    }

    // ---------- Résumé temps réel ----------
    function computeDecompte() {
        const a = parseFloat($('simPrimeNette').value) || 0;
        const b = num('fCoutPolice') || 0;
        const c = a * (num('fTaxe') || 0) / 100;
        const d = a * (num('fTaxeAdd') || 0) / 100;
        const total = a + b + c + d;
        const cessionPct = num('fCession') || 0;
        const retentionPct = num('fRetention') || 0;
        const commCessPct = num('fCommCession') || 0;
        const courtagePct = num('fCourtage') || 0;
        const cession = a * cessionPct / 100;
        const retention = a * retentionPct / 100;
        const commCession = cession * commCessPct / 100;
        const courtage = a * courtagePct / 100;
        const reliquat = a - cession - retention;
        return { a, b, c, d, total, cession, retention, commCession, courtage, reliquat, cessionPct, retentionPct, commCessPct, courtagePct };
    }

    function refreshSummary() {
        const x = computeDecompte();
        const cur = $('fCurrency').value || 'XAF';
        $('simCurrency').textContent = cur;
        $('sumA').textContent = fmt(x.a) + ' ' + cur;
        $('sumB').textContent = fmt(x.b) + ' ' + cur;
        $('sumC').textContent = fmt(x.c) + ' ' + cur;
        $('sumD').textContent = fmt(x.d) + ' ' + cur;
        $('sumTotal').textContent = fmt(x.total) + ' ' + cur;

        $('decompteBody').innerHTML = [
            ['A', 'Prime nette', fmt(x.a)],
            ['B', 'Coût de police', fmt(x.b)],
            ['C', `Taxe (${num('fTaxe') || 0}%)`, fmt(x.c)],
            ['D', `Taxe additionnelle (${num('fTaxeAdd') || 0}%)`, fmt(x.d)],
            ['', '<strong>Prime totale</strong>', `<strong>${fmt(x.total)} ${esc(cur)}</strong>`],
        ].map(([c, l, m]) => `<tr><td><strong>${c}</strong></td><td>${l}</td><td style="text-align:right">${m}</td></tr>`).join('');

        $('fCourtageFormule').value = `${fmt(x.a)} × ${x.courtagePct}% = ${fmt(x.courtage)}`;

        $('repartitionBody').innerHTML = [
            ['Réassureur (cession)', 'Prime nette', x.cessionPct + '%', fmt(x.cession)],
            ['Commission de cession', 'Cession', x.commCessPct + '%', fmt(x.commCession)],
            ['Assureur (rétention)', 'Prime nette', x.retentionPct + '%', fmt(x.retention)],
            ['Intermédiaire (courtage)', 'Prime nette', x.courtagePct + '%', fmt(x.courtage)],
            ['Coût de police (MHC)', 'Forfait', '—', fmt(x.b)],
            ['Fisc (taxes C+D)', 'Taxes', '—', fmt(x.c + x.d)],
            ['Reliquat MHC', 'Prime nette', '—', fmt(x.reliquat)],
        ].map(r => `<tr>${r.map((c, i) => `<td${i === 3 ? ' style="text-align:right"' : ''}>${c}</td>`).join('')}</tr>`).join('');

        $('sumNote').innerHTML =
            `Cession réassureur : <strong>${fmt(x.cession)} ${cur}</strong> · Rétention assureur : <strong>${fmt(x.retention)} ${cur}</strong><br>` +
            `Courtage : <strong>${fmt(x.courtage)} ${cur}</strong> · Taxes : <strong>${fmt(x.c + x.d)} ${cur}</strong><br>` +
            `Reliquat MHC (hors B) : <strong>${fmt(x.reliquat)} ${cur}</strong>`;
    }

    // ---------- Enregistrement ----------
    async function save() {
        const nom = $('fNom').value.trim();
        if (!nom) { toast('Le nom du produit est requis', true); return; }
        const zones = Array.from(document.querySelectorAll('.zone-check:checked')).map(c => c.value);
        const paysExclus = $('fPaysExclus').value.split(',').map(s => s.trim()).filter(Boolean);
        const body = {
            nom,
            code: $('fCode').value.trim() || ('PRD-' + Date.now().toString(36).toUpperCase()),
            version: $('fVersion').value.trim() || null,
            est_actif: $('fStatut').value === 'actif',
            pays: $('fPays').value.trim() || null,
            currency: $('fCurrency').value,
            assureur_id: $('fAssureur').value ? +$('fAssureur').value : null,
            reassureur_id: $('fReassureur').value ? +$('fReassureur').value : null,
            cout: num('fCout') ?? 0,
            retention_assureur_pct: num('fRetention'),
            cession_reassureur_pct: num('fCession'),
            commission_cession_pct: num('fCommCession'),
            cout_police_forfait: num('fCoutPolice'),
            taxe_pct: num('fTaxe'),
            taxe_additionnelle_pct: num('fTaxeAdd'),
            commission_courtage_pct: num('fCourtage'),
            logo_url: logoDataUrl,
            zones_geographiques: { zones, pays_exclus: paysExclus },
        };
        try {
            let saved;
            if (productId) {
                saved = await apiCall(`/admin/products/${productId}`, { method: 'PUT', body: JSON.stringify(body) });
            } else {
                saved = await apiCall('/admin/products', { method: 'POST', body: JSON.stringify(body) });
                productId = saved.id;
            }
            // Surprimes
            const clean = surprimes.filter(s => s.age_min != null && s.age_max != null);
            await apiCall(`/admin/products/${productId}/surprimes`, { method: 'PUT', body: JSON.stringify(clean) });
            toast('Produit enregistré');
            setTimeout(() => { window.location.href = 'admin-products.html'; }, 900);
        } catch (err) {
            toast(err.message || 'Erreur lors de l\'enregistrement', true);
        }
    }

    // ---------- Init ----------
    document.addEventListener('DOMContentLoaded', async () => {
        const ok = await requireAuth();
        if (!ok) return;
        productId = new URLSearchParams(location.search).get('id');
        await loadReferentials();
        if (productId) {
            try { await loadProduct(); } catch (e) { toast(e.message || 'Produit introuvable', true); }
        } else {
            surprimes = [
                { age_min: 0, age_max: 17, taux_pct: 0, formule: 'pourcentage' },
                { age_min: 70, age_max: 75, taux_pct: 0, formule: 'pourcentage' },
                { age_min: 76, age_max: 80, taux_pct: 0, formule: 'pourcentage' },
                { age_min: 81, age_max: 89, taux_pct: 0, formule: 'pourcentage' },
            ];
            renderSurprimes();
            refreshSummary();
        }
        $('btnAddSurprime').addEventListener('click', () => {
            surprimes.push({ age_min: null, age_max: null, taux_pct: 0, formule: 'pourcentage' });
            renderSurprimes();
        });
        $('btnSave').addEventListener('click', save);
        // Résumé temps réel
        ['fCoutPolice', 'fTaxe', 'fTaxeAdd', 'fCession', 'fRetention', 'fCommCession', 'fCourtage', 'simPrimeNette', 'fCurrency']
            .forEach(id => $(id).addEventListener('input', refreshSummary));
        // Auto-remplissage pays depuis l'assureur
        $('fAssureur').addEventListener('change', e => {
            const opt = e.target.selectedOptions[0];
            if (opt && opt.dataset.pays && !$('fPays').value) $('fPays').value = opt.dataset.pays;
        });
        // Défauts réassureur
        $('fReassureur').addEventListener('change', e => {
            const opt = e.target.selectedOptions[0];
            if (opt && opt.dataset.cession && !$('fCession').value) { $('fCession').value = opt.dataset.cession; }
            if (opt && opt.dataset.comm && !$('fCommCession').value) { $('fCommCession').value = opt.dataset.comm; }
            refreshSummary();
        });
        // Logo → data URL
        $('fLogo').addEventListener('change', e => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = ev => {
                logoDataUrl = ev.target.result;
                $('logoPreview').src = logoDataUrl;
                $('logoPreview').style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    });
})();
