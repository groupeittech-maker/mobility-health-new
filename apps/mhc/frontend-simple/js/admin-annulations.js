/* Demandes d'annulation en attente de validation (agent de production).
 * Page dédiée : le menu « Annulations à valider » y mène directement. */

function escapeHtml(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function _fmtAnnulationDate(value) {
    if (!value) return '—';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString('fr-FR');
}

async function loadAnnulationRequests() {
    const container = document.getElementById('annulationRequestsContainer');
    if (!container) return;
    try {
        const avenants = await apiCall('/avenants?statut=attente_validation&type_avenant=annulation');
        renderAnnulationRequests(avenants || []);
    } catch (e) {
        container.innerHTML = `<div class="alert alert-error">Impossible de charger les demandes : ${escapeHtml(e.message || 'erreur')}</div>`;
    }
}

function renderAnnulationRequests(avenants) {
    const container = document.getElementById('annulationRequestsContainer');
    if (!avenants.length) {
        container.innerHTML = '<div class="empty-state"><p>Aucune demande d\'annulation en attente.</p></div>';
        return;
    }
    const rows = avenants.map((a) => {
        const montant = a.montant_ajustement != null
            ? `${Number(a.montant_ajustement).toLocaleString('fr-FR')} FCFA`
            : '—';
        const remboursement = a.nature_ajustement === 'remboursement' ? 'Remboursement prévu' : 'Sans remboursement';
        return `<tr>
            <td><strong>${escapeHtml(a.police_numero || ('#' + a.souscription_id))}</strong></td>
            <td class="mono">${escapeHtml(a.numero || '')}</td>
            <td>${escapeHtml(a.motif_autre || '—')}</td>
            <td>${_fmtAnnulationDate(a.created_at)}</td>
            <td>${montant}<br><span class="muted-text">${remboursement}</span></td>
            <td class="table-actions">
                <select class="action-select">
                    <option value="">⚙️ Actions</option>
                    <option data-act="approuver" data-arg="${a.id}">✅ Approuver</option>
                    <option data-act="refuser" data-arg="${a.id}">❌ Refuser</option>
                </select>
            </td>
        </tr>`;
    }).join('');
    container.innerHTML = `<div class="table-wrapper"><table class="data-table"><thead><tr>
        <th>Police</th><th>Demande</th><th>Motif de l'assuré</th><th>Reçue le</th><th>Ajustement</th><th>Décision</th>
    </tr></thead><tbody>${rows}</tbody></table></div>`;
}

// Actions du tableau (select « Décision », câblé par permissions.js).
window.mhRowAction = function (act, arg) {
    if (act === 'approuver') decideAnnulation(Number(arg), true);
    else if (act === 'refuser') decideAnnulation(Number(arg), false);
};

async function decideAnnulation(avenantId, approuver) {
    let motif = null;
    if (!approuver) {
        motif = window.prompt("Motif du refus (visible par l'assuré) :", '');
        if (motif === null) return;
    } else if (!window.confirm("Approuver cette annulation ? La police sera résiliée et l'avenant 102 émis.")) {
        return;
    }
    try {
        await apiCall(`/avenants/${avenantId}/valider-annulation`, {
            method: 'POST',
            body: JSON.stringify({ approuver, motif }),
        });
        loadAnnulationRequests();
    } catch (e) {
        alert(e.message || 'Décision impossible.');
    }
}

document.addEventListener('DOMContentLoaded', loadAnnulationRequests);
