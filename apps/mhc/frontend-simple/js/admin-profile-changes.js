/* Demandes de modification de profil (workflow V3 §3.3/§4.3) : validation MHC,
 * consultation de la pièce d'identité, refus motivé. */

const PC_STATUT_LABELS = { pending: 'En attente', approved: 'Validée', rejected: 'Refusée' };
const PC_STATUT_CLASS = { pending: 'status-pending', approved: 'status-active', rejected: 'status-inactive' };

let _pcItems = [];

function _pcEsc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _pcDate(v) {
    if (!v) return '—';
    const d = new Date(v);
    return isNaN(d) ? String(v) : d.toLocaleString('fr-FR');
}

async function loadProfileChanges() {
    const container = document.getElementById('profileChangesTableContainer');
    const statut = document.getElementById('profileChangeStatusFilter').value;
    try {
        const query = statut ? `?statut=${encodeURIComponent(statut)}` : '?statut=';
        _pcItems = await apiCall(`/profile-change-requests${query}`);
        renderProfileChangesTable();
    } catch (e) {
        container.innerHTML = `<div class="alert alert-error">${_pcEsc(e.message || 'Chargement impossible.')}</div>`;
    }
}

function renderProfileChangesTable() {
    const container = document.getElementById('profileChangesTableContainer');
    if (!_pcItems.length) {
        container.innerHTML = '<div class="alert alert-info">Aucune demande.</div>';
        return;
    }
    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Assuré</th>
                    <th>Champs demandés</th>
                    <th>Pièce</th>
                    <th>Statut</th>
                    <th>Demandée le</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${_pcItems.map((r) => `
                    <tr>
                        <td>${_recEscName(r)}<br><span class="muted-text">${_pcEsc((r.assure && r.assure.email) || '')}</span></td>
                        <td>${_pcEsc(Object.values(r.libelles || {}).join(', '))}</td>
                        <td>${r.piece_identite ? 'Oui' : '—'}</td>
                        <td><span class="status-badge ${PC_STATUT_CLASS[r.statut] || ''}">${_pcEsc(PC_STATUT_LABELS[r.statut] || r.statut)}</span></td>
                        <td>${_pcDate(r.created_at)}</td>
                        <td><button class="btn btn-outline btn-sm" onclick="openProfileChange(${r.id})">Examiner</button></td>
                    </tr>`).join('')}
            </tbody>
        </table>`;
}

function _recEscName(r) {
    return _pcEsc((r.assure && r.assure.nom) || `Utilisateur #${r.user_id || '?'}`);
}

function openProfileChange(id) {
    const r = _pcItems.find((x) => x.id === id);
    if (!r) return;
    document.getElementById('profileChangeTitle').textContent = `Demande #${r.id} — ${_recEscName(r)}`;
    const rows = Object.entries(r.libelles || {}).map(([field, label]) => {
        const ancienne = (r.anciennes_valeurs || {})[field];
        const nouvelle = (r.champs || {})[field];
        return `<tr>
            <td>${_pcEsc(label)}</td>
            <td>${_pcEsc(ancienne || '—')}</td>
            <td><strong>${_pcEsc(nouvelle || '—')}</strong></td>
        </tr>`;
    }).join('');
    const piece = r.piece_identite;
    const pieceHtml = piece && piece.data_url
        ? `<button class="btn btn-outline btn-sm" onclick="viewIdentityPiece(${r.id})">Voir la pièce (${_pcEsc(piece.nom || 'document')})</button>`
        : '<span class="muted-text">Aucune pièce jointe</span>';
    document.getElementById('profileChangeBody').innerHTML = `
        <table class="data-table">
            <thead><tr><th>Champ</th><th>Valeur actuelle</th><th>Nouvelle valeur</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <div style="margin-top:0.8rem;">${pieceHtml}</div>
        ${r.statut === 'pending' ? `
        <div class="form-group" style="margin-top:0.8rem;">
            <label for="profileChangeMotif">Motif du refus (obligatoire si refus)</label>
            <textarea id="profileChangeMotif" rows="2" class="form-control"></textarea>
        </div>` : `
        <p class="muted-text" style="margin-top:0.8rem;">
            ${r.statut === 'rejected' && r.motif_refus ? `Motif du refus : ${_pcEsc(r.motif_refus)} • ` : ''}Traitée le ${_pcDate(r.decided_at)}
        </p>`}
    `;
    document.getElementById('profileChangeActions').innerHTML = r.statut === 'pending'
        ? `<button class="btn btn-danger btn-sm" onclick="decideProfileChange(${r.id}, false)">Refuser</button>
           <button class="btn btn-success btn-sm" onclick="decideProfileChange(${r.id}, true)">Valider</button>`
        : '';
    document.getElementById('profileChangeModal').classList.add('show');
}

function viewIdentityPiece(id) {
    const r = _pcItems.find((x) => x.id === id);
    const piece = r && r.piece_identite;
    if (!piece || !piece.data_url) return;
    const w = window.open('', '_blank', 'noopener');
    if (!w) return;
    if (piece.data_url.startsWith('data:image/')) {
        w.document.write(`<img src="${piece.data_url}" style="max-width:100%">`);
    } else {
        w.document.write(`<iframe src="${piece.data_url}" style="width:100%;height:100vh;border:0"></iframe>`);
    }
}

async function decideProfileChange(id, approved) {
    const motif = (document.getElementById('profileChangeMotif')?.value || '').trim();
    if (!approved && !motif) {
        showAlert('Le motif du refus est obligatoire.', 'error');
        return;
    }
    try {
        await apiCall(`/profile-change-requests/${id}/decision`, {
            method: 'POST',
            body: JSON.stringify({ approved, motif: motif || null }),
        });
        showAlert(approved ? 'Demande validée : le profil est mis à jour.' : 'Demande refusée.', 'success');
        document.getElementById('profileChangeModal').classList.remove('show');
        loadProfileChanges();
    } catch (e) {
        showAlert(e.message || 'Décision impossible.', 'error');
    }
}

function initProfileChangesAdmin() {
    document.getElementById('profileChangeStatusFilter').addEventListener('change', loadProfileChanges);
    document.getElementById('profileChangeModalClose').onclick =
        () => document.getElementById('profileChangeModal').classList.remove('show');
    document.getElementById('profileChangeModal').addEventListener('click', (e) => {
        if (e.target.id === 'profileChangeModal') e.target.classList.remove('show');
    });
    loadProfileChanges();
}

document.addEventListener('DOMContentLoaded', initProfileChangesAdmin);
