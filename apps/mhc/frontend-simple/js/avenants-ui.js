/* Actions sur une police (workflow MyMHC V3) : annulation, modification, prorogation.
 * Une seule demande en cours par attestation : les autres actions sont désactivées
 * tant qu'une modification / prorogation attend le paiement de son complément. */

const AVENANT_TYPE_LABELS = {
    annulation: "Avenant d'annulation",
    modification: 'Avenant de modification',
    prorogation: 'Avenant de prorogation',
};
const AVENANT_STATUT_LABELS = {
    attente_paiement: 'En attente du paiement du complément',
    emis: 'Émis',
    abandonne: 'Abandonné',
};
const RISTOURNE_STATUT_LABELS = { a_rembourser: 'Remboursement en cours', rembourse: 'Remboursé' };
const ACTION_PAYMENT_TYPES = {
    mobile_money_mtn: 'Mobile Money MTN',
    mobile_money_airtel: 'Airtel Money',
    carte_bancaire: 'Carte bancaire',
};

let _policyState = { subscription: null, info: null, action: null, simulation: null, avenant: null };

function _esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _money(v, devise) {
    const n = Number(v || 0);
    return `${n.toLocaleString('fr-FR', { maximumFractionDigits: 0 })} ${devise || 'FCFA'}`;
}

function _fmtDate(v) {
    if (!v) return '—';
    const d = new Date(v);
    return isNaN(d) ? String(v) : d.toLocaleDateString('fr-FR');
}

function _isoDay(v) {
    const d = v ? new Date(v) : new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function _addDays(iso, days) {
    const d = new Date(`${iso}T00:00:00`);
    d.setDate(d.getDate() + days);
    return _isoDay(d);
}

/* ------------------------------ Chargement ------------------------------ */

async function renderPolicyActions(subscription, containerEl) {
    _policyState.subscription = subscription;
    let info;
    try {
        info = await apiCall(`/subscriptions/${subscription.id}/actions`);
    } catch (e) {
        console.warn('Actions police indisponibles :', e);
        return;
    }
    _policyState.info = info;
    _renderActionButtons(info);
    if (containerEl) containerEl.innerHTML = _sectionHtml(info);
}

function _renderActionButtons(info) {
    const buttons = {
        annulation: document.getElementById('annulationBtn'),
        modification: document.getElementById('modificationBtn'),
        prorogation: document.getElementById('prorogationBtn'),
    };
    const statut = info.statut_souscription;
    const visible = !['resiliee', 'refusee', 'expiree', 'en_attente', 'pending'].includes(statut);
    Object.entries(buttons).forEach(([action, btn]) => {
        if (!btn) return;
        const state = info.actions[action] || {};
        // L'annulation reste proposée avant paiement (validation en attente) ;
        // modification et prorogation n'ont de sens que sur une police active.
        const show = visible && (action === 'annulation' || statut === 'active');
        btn.style.display = show ? 'inline-block' : 'none';
        btn.disabled = !state.disponible;
        btn.title = state.disponible ? '' : (state.motif || '');
        btn.onclick = () => openPolicyActionModal(action);
    });
}

function _sectionHtml(info) {
    const pending = info.action_en_cours;
    const pendingHtml = pending ? `
        <div class="alert alert-info" style="margin-bottom:0.8rem;">
            <strong>Demande en cours : ${_esc(AVENANT_TYPE_LABELS[pending.type_avenant] || pending.type_avenant)}</strong>
            <div>Nouvelles dates : du ${_fmtDate(pending.nouvelle_date_debut)} au ${_fmtDate(pending.nouvelle_date_fin)}</div>
            <div>Complément de prime à régler : <strong>${_money(pending.montant_ajustement)}</strong></div>
            <div class="muted-text">Les autres actions sur cette attestation sont désactivées jusqu'à la clôture de la demande.</div>
            <div style="margin-top:0.5rem;display:flex;gap:0.4rem;flex-wrap:wrap;">
                <button class="btn btn-primary btn-sm" onclick="openAvenantPaymentModal(${pending.id})">Payer le complément</button>
                <button class="btn btn-outline btn-sm" onclick="abandonAvenant(${pending.id})">Renoncer à la demande</button>
            </div>
        </div>` : '';

    const avenants = (info.avenants || []).filter((a) => a.statut !== 'attente_paiement');
    const avenantRows = avenants.map((a) => `
        <li class="card-item" style="margin-bottom:0.6rem;">
            <strong>${_esc(AVENANT_TYPE_LABELS[a.type_avenant] || a.type_avenant)}</strong>
            <div class="muted-text">${a.statut === 'emis' ? `N° ${_esc(a.numero)} • ` : ''}${_esc(AVENANT_STATUT_LABELS[a.statut] || a.statut)}</div>
            ${a.type_avenant === 'modification' && a.statut === 'emis' && a.payload && a.payload.nouvelle_destination
                ? `<div class="muted-text">Destination : ${_esc(a.payload.ancienne_destination || '—')} → ${_esc(a.payload.nouvelle_destination)}</div>` : ''}
            ${a.type_avenant === 'prorogation' && a.statut === 'emis'
                ? `<div class="muted-text">Couverture : du ${_fmtDate(a.nouvelle_date_debut)} au ${_fmtDate(a.nouvelle_date_fin)}</div>` : ''}
            ${a.statut === 'emis' ? `<div style="margin-top:0.4rem;">
                <a class="btn btn-outline btn-sm" href="#" onclick="return openPolicyPdf(event, '/avenants/${a.id}/download')">Télécharger l'avenant</a>
            </div>` : ''}
        </li>`).join('');

    const ristourneRows = (info.ristournes || []).map((r) => `
        <li class="card-item" style="margin-bottom:0.6rem;">
            <strong>Remboursement de ${_money(r.montant_total, r.devise)}</strong>
            <div class="muted-text">${_esc(RISTOURNE_STATUT_LABELS[r.statut] || r.statut)}${r.numero ? ` • Quittance N° ${_esc(r.numero)}` : ''}</div>
            <div class="muted-text">${_esc(r.motif || '')}</div>
            ${r.statut === 'rembourse' ? `<div style="margin-top:0.4rem;">
                <a class="btn btn-outline btn-sm" href="#" onclick="return openPolicyPdf(event, '/ristournes/${r.id}/download')">Quittance de ristourne</a>
            </div>` : ''}
        </li>`).join('');

    if (!pendingHtml && !avenantRows && !ristourneRows) return '';
    return `
        <div class="detail-section">
            <h3>Actions sur la police</h3>
            ${pendingHtml}
            ${avenantRows ? `<ul style="list-style:none;padding:0;">${avenantRows}</ul>` : ''}
            ${ristourneRows ? `<h4 style="margin-top:0.8rem;">Remboursements</h4><ul style="list-style:none;padding:0;">${ristourneRows}</ul>` : ''}
        </div>`;
}

/* -------------------------------- Modale -------------------------------- */

function _modal() { return document.getElementById('policyActionModal'); }

function _openModal(title, subtitle, bodyHtml, actionsHtml) {
    const modal = _modal();
    if (!modal) return;
    document.getElementById('policyActionTitle').textContent = title;
    document.getElementById('policyActionSubtitle').textContent = subtitle || '';
    document.getElementById('policyActionBody').innerHTML = bodyHtml;
    document.getElementById('policyActionActions').innerHTML = actionsHtml;
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    modal.onclick = (e) => { if (e.target === modal) closePolicyActionModal(); };
}

function closePolicyActionModal() {
    const modal = _modal();
    if (modal) modal.classList.remove('show');
    document.body.style.overflow = '';
    _policyState.action = null;
    _policyState.simulation = null;
}

function openPolicyActionModal(action) {
    const sub = _policyState.subscription;
    const maxDays = (_policyState.info && _policyState.info.duree_max_jours) || 92;
    const today = _isoDay();
    const start = _isoDay(sub.date_debut);
    const end = _isoDay(sub.date_fin);
    _policyState.action = action;
    _policyState.simulation = null;

    const cancelBtn = '<button type="button" class="btn btn-secondary" onclick="closePolicyActionModal()">Fermer</button>';
    const simulateBtn = '<button type="button" class="btn btn-primary" id="policySimulateBtn" onclick="simulatePolicyAction()">Calculer</button>';
    const motif = `<div class="form-group"><label for="policyMotif">Motif (optionnel)</label>
        <textarea id="policyMotif" rows="2" class="form-control"></textarea></div>`;

    if (action === 'annulation') {
        _openModal(
            'Annuler la police',
            "L'annulation est définitive. Elle n'est possible qu'avant la date d'effet de la police.",
            `${motif}<div id="policySimulation"></div>`,
            cancelBtn + simulateBtn,
        );
        simulatePolicyAction();
    } else if (action === 'modification') {
        _openModal(
            'Changer de destination',
            "La nouvelle destination doit être dans la même zone tarifaire que la destination initiale. "
            + "Les dates de couverture et la prime sont inchangées : aucun supplément ni remboursement. "
            + "L'avenant de modification est émis immédiatement.",
            `<div class="form-group"><label for="policyNewDestination">Nouvelle destination</label>
                <select id="policyNewDestination" class="form-control"><option value="">Chargement…</option></select></div>
             <div class="form-group"><label for="policyNewVille">Ville (optionnel)</label>
                <input type="text" id="policyNewVille" class="form-control" placeholder="Ex. : Bruxelles"></div>
             ${motif}<div id="policySimulation"></div>`,
            cancelBtn + simulateBtn,
        );
        apiCall('/destinations/countries?actif_seulement=true')
            .then((countries) => {
                const select = document.getElementById('policyNewDestination');
                if (!select) return;
                const currentId = sub.projet_voyage && sub.projet_voyage.destination_country_id;
                select.innerHTML = '<option value="">— Choisir —</option>'
                    + (countries || [])
                        .filter((c) => c.id !== currentId)
                        .map((c) => `<option value="${c.id}">${_esc(c.nom)}</option>`)
                        .join('');
            })
            .catch(() => {
                const select = document.getElementById('policyNewDestination');
                if (select) select.innerHTML = '<option value="">Destinations indisponibles</option>';
            });
    } else {
        _openModal(
            'Prolonger la police',
            `Jusqu'à la date de fin de couverture initiale. Durée totale maximale : ${maxDays} jours. Prime complémentaire au prorata.`,
            `<div class="form-group"><label for="policyNewEnd">Nouvelle date de fin de couverture</label>
                <input type="date" id="policyNewEnd" class="form-control" min="${_addDays(end, 1)}" max="${_addDays(start, maxDays)}" value="${_addDays(end, 1)}"></div>
             ${motif}<div id="policySimulation"></div>`,
            cancelBtn + simulateBtn,
        );
    }
}

function _actionPayload(confirm) {
    const payload = { confirmer: confirm, motif: (document.getElementById('policyMotif')?.value || '').trim() || null };
    const destInput = document.getElementById('policyNewDestination');
    const villeInput = document.getElementById('policyNewVille');
    const endInput = document.getElementById('policyNewEnd');
    if (destInput) payload.destination_country_id = destInput.value ? Number(destInput.value) : null;
    if (villeInput && villeInput.value.trim()) payload.destination_ville = villeInput.value.trim();
    if (endInput) payload.nouvelle_date_fin = endInput.value;
    return payload;
}

async function simulatePolicyAction() {
    const sub = _policyState.subscription;
    const action = _policyState.action;
    const box = document.getElementById('policySimulation');
    try {
        const res = await apiCall(`/subscriptions/${sub.id}/actions/${action}`, {
            method: 'POST',
            body: JSON.stringify(_actionPayload(false)),
        });
        _policyState.simulation = res;
        const m = res.montants || {};
        let summary;
        if (action === 'annulation') {
            summary = Number(m.total) > 0
                ? `Montant remboursable : <strong>${_money(m.total)}</strong> (prime ${_money(m.prime)}, taxes ${_money(Number(m.taxes) + Number(m.frais_services))}). Le remboursement est traité séparément par Mobility Health Care.`
                : "Aucun paiement n'a été effectué : aucun remboursement n'est dû.";
            summary += `<label style="display:flex;gap:0.5rem;margin-top:0.6rem;"><input type="checkbox" id="policyConfirmCheck">
                <span>Je confirme vouloir annuler définitivement cette police.</span></label>`;
        } else if (res.nature_ajustement === 'complement') {
            summary = `Complément de prime à régler : <strong>${_money(m.total)}</strong>. L'avenant sera émis après paiement.`;
        } else if (res.nature_ajustement === 'remboursement') {
            summary = `Remboursement partiel : <strong>${_money(m.total)}</strong>. L'avenant est émis immédiatement, le remboursement est traité séparément.`;
        } else {
            const info = res.payment_info || {};
            const dest = info.nouvelle_destination
                ? `Nouvelle destination : <strong>${_esc(info.nouvelle_destination)}</strong> (zone ${_esc(info.zone_tarifaire || '')}). `
                : '';
            summary = `${dest}Dates et prime inchangées : aucun ajustement. L'avenant est émis immédiatement.`;
        }
        box.innerHTML = `<div class="alert alert-info">${summary}</div>`;
        document.getElementById('policyActionActions').innerHTML = `
            <button type="button" class="btn btn-secondary" onclick="closePolicyActionModal()">Fermer</button>
            ${action !== 'annulation' ? '<button type="button" class="btn btn-outline" onclick="simulatePolicyAction()">Recalculer</button>' : ''}
            <button type="button" class="btn ${action === 'annulation' ? 'btn-danger' : 'btn-primary'}" id="policyConfirmBtn" onclick="confirmPolicyAction()">Confirmer</button>`;
    } catch (e) {
        box.innerHTML = `<div class="alert alert-error">${_esc(e.message || 'Action impossible.')}</div>`;
    }
}

async function confirmPolicyAction() {
    const sub = _policyState.subscription;
    const action = _policyState.action;
    if (action === 'annulation' && !document.getElementById('policyConfirmCheck')?.checked) {
        showAlert("Veuillez cocher la confirmation d'annulation.", 'error');
        return;
    }
    const btn = document.getElementById('policyConfirmBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Envoi…'; }
    try {
        const res = await apiCall(`/subscriptions/${sub.id}/actions/${action}`, {
            method: 'POST',
            body: JSON.stringify(_actionPayload(true)),
        });
        if (res.avenant && res.avenant.statut === 'attente_paiement') {
            openAvenantPaymentModal(res.avenant.id, res.avenant.montant_ajustement);
            return;
        }
        showAlert(action === 'annulation' ? 'Votre police est annulée.' : 'Avenant émis.', 'success');
        closePolicyActionModal();
        setTimeout(() => window.location.reload(), 800);
    } catch (e) {
        showAlert(e.message || 'Action impossible.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Confirmer'; }
    }
}

/* ------------------------- Paiement du complément ------------------------ */

function openAvenantPaymentModal(avenantId, montant) {
    const pending = _policyState.info && _policyState.info.action_en_cours;
    const amount = montant != null ? montant : (pending ? pending.montant_ajustement : null);
    _policyState.avenant = avenantId;
    const options = Object.entries(ACTION_PAYMENT_TYPES)
        .map(([k, v]) => `<option value="${k}">${_esc(v)}</option>`).join('');
    _openModal(
        'Payer le complément de prime',
        "L'avenant est émis dès confirmation du paiement. En cas d'échec, aucune modification n'est appliquée.",
        `<div class="alert alert-info">Montant : <strong>${_money(amount)}</strong></div>
         <div class="form-group"><label for="policyPaymentType">Moyen de paiement</label>
            <select id="policyPaymentType" class="form-control">${options}</select></div>`,
        `<button type="button" class="btn btn-secondary" onclick="closePolicyActionModal(); window.location.reload();">Plus tard</button>
         <button type="button" class="btn btn-primary" id="policyPayBtn" onclick="payAvenant()">Payer</button>`,
    );
}

async function payAvenant() {
    const btn = document.getElementById('policyPayBtn');
    if (btn) { btn.disabled = true; btn.textContent = 'Paiement…'; }
    try {
        const res = await apiCall(`/avenants/${_policyState.avenant}/payer`, {
            method: 'POST',
            body: JSON.stringify({ payment_type: document.getElementById('policyPaymentType').value, flow: 'checkout' }),
        });
        if (res.payment_url) {
            window.location.href = res.payment_url;
            return;
        }
        if (res.avenant && res.avenant.statut === 'emis') {
            showAlert('Paiement confirmé : avenant émis.', 'success');
        } else {
            showAlert('Paiement en cours de traitement. Vous serez notifié de sa confirmation.', 'info');
        }
        closePolicyActionModal();
        setTimeout(() => window.location.reload(), 800);
    } catch (e) {
        showAlert(e.message || 'Le paiement a échoué.', 'error');
        if (btn) { btn.disabled = false; btn.textContent = 'Payer'; }
    }
}

async function abandonAvenant(avenantId) {
    if (!window.confirm('Renoncer à cette demande ? Les autres actions seront de nouveau disponibles.')) return;
    try {
        await apiCall(`/avenants/${avenantId}/abandon`, { method: 'POST' });
        showAlert('Demande abandonnée.', 'success');
        setTimeout(() => window.location.reload(), 600);
    } catch (e) {
        showAlert(e.message || 'Impossible de renoncer à la demande.', 'error');
    }
}

/* --------------------------------- PDF ---------------------------------- */

function openPolicyPdf(event, path) {
    event.preventDefault();
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    fetch(`${API_BASE_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
        .then((res) => { if (!res.ok) throw new Error('PDF indisponible'); return res.blob(); })
        .then((blob) => window.open(URL.createObjectURL(blob), '_blank', 'noopener'))
        .catch((err) => showAlert(err.message || "Impossible d'ouvrir le PDF.", 'error'));
    return false;
}
