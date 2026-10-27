/* Réclamations back-office (workflow V3 §8.1) : file de traitement, changements
 * de statut, messages à l'assuré. La contestation crée une réclamation liée. */

const REC_STATUT_LABELS = {
    recue: 'Reçue',
    en_analyse: "En cours d'analyse",
    infos_requises: 'Informations requises',
    traitee: 'Traitée',
    cloturee: 'Clôturée',
};
const REC_STATUT_CLASS = {
    recue: 'status-inactive',
    en_analyse: 'status-pending',
    infos_requises: 'status-pending',
    traitee: 'status-active',
    cloturee: 'status-inactive',
};

let _recItems = [];
let _recCurrent = null;

function _recEsc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _recDate(v) {
    if (!v) return '—';
    const d = new Date(v);
    return isNaN(d) ? String(v) : d.toLocaleString('fr-FR');
}

async function loadReclamations() {
    const container = document.getElementById('reclamationsTableContainer');
    const statut = document.getElementById('reclamationStatusFilter').value;
    try {
        const query = statut ? `?statut=${encodeURIComponent(statut)}` : '?statut=';
        _recItems = await apiCall(`/reclamations/admin/list${query}`);
        renderReclamationsTable();
    } catch (e) {
        container.innerHTML = `<div class="alert alert-error">${_recEsc(e.message || 'Chargement impossible.')}</div>`;
    }
}

function renderReclamationsTable() {
    const container = document.getElementById('reclamationsTableContainer');
    const needle = (document.getElementById('reclamationSearch').value || '').toLowerCase();
    const rows = _recItems.filter((r) => {
        const hay = `${r.reference || ''} ${r.objet || ''} ${(r.coordonnees && r.coordonnees.email) || ''} ${(r.coordonnees && r.coordonnees.nom) || ''}`.toLowerCase();
        return !needle || hay.includes(needle);
    });
    if (!rows.length) {
        container.innerHTML = '<div class="alert alert-info">Aucune réclamation.</div>';
        return;
    }
    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Référence</th>
                    <th>Assuré</th>
                    <th>Catégorie</th>
                    <th>Objet</th>
                    <th>Statut</th>
                    <th>Reçue le</th>
                    <th>1ʳᵉ réponse avant</th>
                    <th>Résolution avant</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${rows.map((r) => `
                    <tr>
                        <td><strong>${_recEsc(r.reference)}</strong>${r.parent_id ? ' <span class="muted-text">(contestation)</span>' : ''}</td>
                        <td>${_recEsc((r.coordonnees && r.coordonnees.nom) || (r.coordonnees && r.coordonnees.email) || '—')}</td>
                        <td>${_recEsc(r.categorie_libelle || r.categorie)}</td>
                        <td>${_recEsc(r.objet)}</td>
                        <td><span class="status-badge ${REC_STATUT_CLASS[r.statut] || ''}">${_recEsc(REC_STATUT_LABELS[r.statut] || r.statut)}</span></td>
                        <td>${_recDate(r.created_at)}</td>
                        <td>${_recDate(r.echeance_premiere_reponse)}</td>
                        <td>${_recDate(r.echeance_resolution)}</td>
                        <td><button class="btn btn-outline btn-sm" onclick="openReclamation(${r.id})">Traiter</button></td>
                    </tr>`).join('')}
            </tbody>
        </table>`;
}

async function openReclamation(id) {
    try {
        _recCurrent = await apiCall(`/reclamations/${id}`);
    } catch (e) {
        showAlert(e.message || 'Réclamation introuvable.', 'error');
        return;
    }
    const r = _recCurrent;
    document.getElementById('reclamationModalTitle').textContent = `${r.reference} — ${r.objet || ''}`;
    const hist = (r.historique || []).map((e) => `
        <li style="margin-bottom:0.5rem;">
            <span class="muted-text">${_recDate(e.date)} • ${e.auteur_est_assure ? 'Assuré' : 'MHC'}${e.type === 'statut' ? ' • statut' : ''}</span><br>
            ${_recEsc(e.type === 'statut' ? (e.statut_libelle || REC_STATUT_LABELS[e.statut] || e.statut) : (e.message || ''))}
        </li>`).join('');
    document.getElementById('reclamationModalBody').innerHTML = `
        <div class="personal-info-grid" style="margin-bottom:0.8rem;">
            <div class="personal-info-item"><span class="personal-info-label">Assuré</span>
                <strong class="personal-info-value">${_recEsc((r.coordonnees && r.coordonnees.nom) || '—')}</strong></div>
            <div class="personal-info-item"><span class="personal-info-label">E-mail</span>
                <strong class="personal-info-value">${_recEsc((r.coordonnees && r.coordonnees.email) || '—')}</strong></div>
            <div class="personal-info-item"><span class="personal-info-label">Téléphone</span>
                <strong class="personal-info-value">${_recEsc((r.coordonnees && r.coordonnees.telephone) || '—')}</strong></div>
            <div class="personal-info-item"><span class="personal-info-label">Catégorie</span>
                <strong class="personal-info-value">${_recEsc(r.categorie_libelle || r.categorie)}</strong></div>
        </div>
        <p style="white-space:pre-wrap;">${_recEsc(r.description)}</p>
        ${r.reponse ? `<div class="alert alert-info" style="margin-top:0.8rem;"><strong>Réponse :</strong> ${_recEsc(r.reponse)}</div>` : ''}
        ${r.parent_id ? `<p class="muted-text">Contestation de la réclamation #${r.parent_id}.</p>` : ''}
        <h4 style="margin-top:1rem;">Historique</h4>
        <ul style="list-style:none;padding:0;">${hist || '<li class="muted-text">—</li>'}</ul>
        <div class="form-group" style="margin-top:0.8rem;">
            <label for="reclamationMessage">Message / commentaire</label>
            <textarea id="reclamationMessage" rows="3" class="form-control" placeholder="Message envoyé à l'assuré ou motif interne…"></textarea>
        </div>`;
    document.getElementById('reclamationModalActions').innerHTML = _recActionsHtml(r);
    document.getElementById('reclamationModal').classList.add('show');
}

function _recActionsHtml(r) {
    const msg = `document.getElementById('reclamationMessage').value`;
    const buttons = [];
    if (r.statut === 'recue') {
        buttons.push(`<button class="btn btn-primary btn-sm" onclick="setReclamationStatut(${r.id}, 'en_analyse', ${msg})">Mettre en analyse</button>`);
    }
    if (['recue', 'en_analyse'].includes(r.statut)) {
        buttons.push(`<button class="btn btn-outline btn-sm" onclick="setReclamationStatut(${r.id}, 'infos_requises', ${msg}, true)">Demander des informations</button>`);
    }
    if (!['traitee', 'cloturee'].includes(r.statut)) {
        buttons.push(`<button class="btn btn-success btn-sm" onclick="setReclamationStatut(${r.id}, 'traitee', ${msg}, true)">Marquer traitée (réponse)</button>`);
    }
    if (r.statut === 'traitee') {
        buttons.push(`<button class="btn btn-secondary btn-sm" onclick="setReclamationStatut(${r.id}, 'cloturee', ${msg})">Clôturer</button>`);
    }
    return buttons.join('');
}

async function setReclamationStatut(id, statut, message, requireMessage) {
    message = (message || '').trim();
    if (requireMessage && !message) {
        showAlert('Un message est obligatoire pour cette action.', 'error');
        return;
    }
    try {
        await apiCall(`/reclamations/${id}/statut`, {
            method: 'POST',
            body: JSON.stringify({ statut, message: message || null }),
        });
        showAlert('Réclamation mise à jour.', 'success');
        document.getElementById('reclamationModal').classList.remove('show');
        loadReclamations();
    } catch (e) {
        showAlert(e.message || 'Action impossible.', 'error');
    }
}

function initReclamationsAdmin() {
    document.getElementById('reclamationStatusFilter').addEventListener('change', loadReclamations);
    document.getElementById('reclamationSearch').addEventListener('input', renderReclamationsTable);
    document.getElementById('reclamationModalClose').onclick =
        () => document.getElementById('reclamationModal').classList.remove('show');
    document.getElementById('reclamationModal').addEventListener('click', (e) => {
        if (e.target.id === 'reclamationModal') e.target.classList.remove('show');
    });
    loadReclamations();
}

document.addEventListener('DOMContentLoaded', initReclamationsAdmin);
