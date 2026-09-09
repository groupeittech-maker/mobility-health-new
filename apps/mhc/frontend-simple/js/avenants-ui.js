/* UI des avenants de police (suspension / réémission) — côté assuré et assureur. */

const AVENANT_STATUT_LABELS = {
    demande: 'En attente de validation',
    valide: 'Validée',
    refuse: 'Refusée',
    emis: 'Émis',
};
const AVENANT_TYPE_LABELS = {
    suspension: 'Avenant de suspension',
    reemission: 'Avenant de réémission',
    annulation: "Avenant d'annulation",
};

let _avenantCatalog = null;
let _suspensionSubscription = null;

function _esc(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

async function loadAvenantCatalog() {
    if (_avenantCatalog) return _avenantCatalog;
    _avenantCatalog = await apiCall('/avenants/catalogue');
    return _avenantCatalog;
}

/* ------------------------- Côté assuré : demande ------------------------- */

async function showSuspensionModal(subscription) {
    _suspensionSubscription = subscription;
    const modal = document.getElementById('suspensionModal');
    if (!modal) return;
    const motifsBox = document.getElementById('suspensionMotifs');
    const piecesBox = document.getElementById('suspensionPieces');
    const autreGroup = document.getElementById('suspensionAutreGroup');
    const autreInput = document.getElementById('suspensionMotifAutre');
    const confirmBtn = document.getElementById('confirmSuspensionBtn');

    if (autreInput) autreInput.value = '';
    if (autreGroup) autreGroup.style.display = 'none';

    try {
        const catalog = await loadAvenantCatalog();
        motifsBox.innerHTML = Object.entries(catalog.motifs || {}).map(([key, label]) => `
            <label style="display:flex;gap:0.5rem;align-items:flex-start;margin:0.3rem 0;text-align:left;">
                <input type="checkbox" class="suspension-motif" value="${_esc(key)}" style="margin-top:0.2rem;flex:0 0 auto;">
                <span style="flex:1;">${_esc(label)}</span>
            </label>`).join('');
        piecesBox.innerHTML = Object.entries(catalog.pieces || {}).map(([key, label]) => `
            <label style="display:flex;gap:0.5rem;align-items:flex-start;margin:0.3rem 0;text-align:left;">
                <input type="checkbox" class="suspension-piece" value="${_esc(key)}" style="margin-top:0.2rem;flex:0 0 auto;">
                <span style="flex:1;">${_esc(label)}</span>
            </label>`).join('');
        // Afficher la zone « préciser » si « autre » est coché
        motifsBox.querySelectorAll('.suspension-motif').forEach((cb) => {
            cb.addEventListener('change', () => {
                const autreChecked = motifsBox.querySelector('.suspension-motif[value="autre"]')?.checked;
                if (autreGroup) autreGroup.style.display = autreChecked ? 'block' : 'none';
            });
        });
    } catch (e) {
        motifsBox.innerHTML = `<div class="alert alert-error">${_esc(e.message || 'Erreur de chargement des motifs')}</div>`;
    }

    if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Envoyer la demande';
        confirmBtn.onclick = submitSuspensionRequest;
    }
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
    modal.onclick = (e) => { if (e.target === modal) closeSuspensionModal(); };
}

function closeSuspensionModal() {
    const modal = document.getElementById('suspensionModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

async function submitSuspensionRequest() {
    const subscription = _suspensionSubscription;
    if (!subscription) return;
    const confirmBtn = document.getElementById('confirmSuspensionBtn');
    const motifs = Array.from(document.querySelectorAll('.suspension-motif:checked')).map((c) => c.value);
    const pieces = Array.from(document.querySelectorAll('.suspension-piece:checked')).map((c) => c.value);
    const motifAutre = (document.getElementById('suspensionMotifAutre')?.value || '').trim();

    if (!motifs.length) {
        showAlert('Veuillez sélectionner au moins un motif.', 'error');
        return;
    }
    if (motifs.includes('autre') && !motifAutre) {
        showAlert('Veuillez préciser le motif « Autre ».', 'error');
        return;
    }
    if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = 'Envoi…'; }
    try {
        await apiCall(`/subscriptions/${subscription.id}/avenant-suspension`, {
            method: 'POST',
            body: JSON.stringify({ motifs, pieces, motif_autre: motifAutre || null }),
        });
        showAlert('Demande de suspension envoyée. En attente de validation de l\'assureur.', 'success');
        closeSuspensionModal();
        const holder = document.getElementById('avenantsSection');
        if (holder) await loadAvenantsList(subscription.id, holder);
    } catch (e) {
        showAlert(e.message || 'Impossible d\'envoyer la demande de suspension.', 'error');
    } finally {
        if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = 'Envoyer la demande'; }
    }
}

/* --------------------- Liste des avenants (assuré) ---------------------- */

async function loadAvenantsList(subscriptionId, containerEl) {
    if (!containerEl) return;
    try {
        const avenants = await apiCall(`/subscriptions/${subscriptionId}/avenants`);
        if (!avenants || !avenants.length) {
            containerEl.innerHTML = '';
            return;
        }
        const rows = avenants.map((a) => {
            const type = AVENANT_TYPE_LABELS[a.type_avenant] || a.type_avenant;
            const statut = AVENANT_STATUT_LABELS[a.statut] || a.statut;
            const canUpload = a.type_avenant === 'suspension' && a.statut === 'demande';
            return `<li class="card-item" style="margin-bottom:0.6rem;">
                <strong>${_esc(type)}</strong>
                <div class="muted-text">N° ${_esc(a.numero)} • ${_esc(statut)}</div>
                ${_fichiersHtml(a)}
                <div style="margin-top:0.4rem;">
                    <a class="btn btn-outline btn-sm" href="${API_BASE_URL}/avenants/${a.id}/download" target="_blank" rel="noopener" onclick="return openAvenantPdf(event, ${a.id})">Télécharger le PDF</a>
                </div>
                ${canUpload ? _uploadHtml(a.id) : ''}
            </li>`;
        }).join('');
        containerEl.innerHTML = `
            <div class="detail-section">
                <h3>Avenants de la police</h3>
                <ul style="list-style:none;padding:0;">${rows}</ul>
            </div>`;
    } catch (e) {
        containerEl.innerHTML = '';
    }
}

/* --------------------- Côté assureur : décision ------------------------ */

async function renderAssureurSuspensions(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = '<p class="muted">Chargement…</p>';
    try {
        const list = await apiCall('/avenants?type_avenant=suspension&statut=demande');
        if (!list || !list.length) {
            el.innerHTML = '<p class="muted">Aucune demande de suspension en attente.</p>';
            return;
        }
        const items = list.map((a) => `
            <li class="card-item" style="margin-bottom:0.6rem;">
                <strong>Suspension ${_esc(a.numero)}</strong>
                <div class="muted-text">Souscription #${_esc(a.souscription_id)} • Motifs : ${_esc((a.motifs || []).join(', '))}${a.motif_autre ? (' — ' + _esc(a.motif_autre)) : ''}</div>
                <div class="muted-text">Pièces annoncées : ${_esc((a.pieces_jointes || []).join(', ') || '—')}</div>
                ${_fichiersHtml(a)}
                <div style="margin-top:0.4rem;display:flex;gap:0.4rem;flex-wrap:wrap;">
                    <button class="btn btn-primary btn-sm" onclick="decideSuspension(${a.id}, true, '${containerId}')">Valider</button>
                    <button class="btn btn-outline btn-sm" onclick="decideSuspension(${a.id}, false, '${containerId}')">Refuser</button>
                    <a class="btn btn-outline btn-sm" href="${API_BASE_URL}/avenants/${a.id}/download" target="_blank" rel="noopener" onclick="return openAvenantPdf(event, ${a.id})">PDF</a>
                </div>
            </li>`).join('');
        el.innerHTML = `<ul style="list-style:none;padding:0;">${items}</ul>`;
    } catch (e) {
        el.innerHTML = `<div class="alert alert-error">${_esc(e.message || 'Erreur de chargement')}</div>`;
    }
}

async function decideSuspension(avenantId, approve, containerId) {
    if (!approve && !window.confirm('Refuser cette demande de suspension ?')) return;
    try {
        await apiCall(`/avenants/${avenantId}/suspension-decision`, {
            method: 'POST',
            body: JSON.stringify({ approve }),
        });
        showAlert(approve ? 'Suspension validée — police suspendue.' : 'Suspension refusée.', 'success');
        renderAssureurSuspensions(containerId);
    } catch (e) {
        showAlert(e.message || 'Impossible de traiter la décision.', 'error');
    }
}

/* --------------------- Pièces justificatives (upload) ------------------ */

function _fichiersHtml(avenant) {
    const fichiers = avenant.fichiers || [];
    if (!fichiers.length) return '';
    const links = fichiers.map((f, i) =>
        `<a class="btn btn-outline btn-sm" href="#" onclick="return downloadAvenantPiece(event, ${avenant.id}, ${i})" style="margin:0.15rem;">📎 ${_esc(f.nom || ('pièce ' + (i + 1)))}</a>`
    ).join('');
    return `<div class="muted-text" style="margin-top:0.3rem;">Pièces jointes : ${links}</div>`;
}

function _uploadHtml(avenantId) {
    return `<div style="margin-top:0.4rem;display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
        <input type="file" id="avenantPieceFile-${avenantId}" accept="application/pdf,image/*" style="font-size:0.85rem;">
        <button class="btn btn-secondary btn-sm" onclick="uploadAvenantPiece(${avenantId})">Ajouter une pièce</button>
    </div>`;
}

async function uploadAvenantPiece(avenantId) {
    const input = document.getElementById(`avenantPieceFile-${avenantId}`);
    const file = input && input.files && input.files[0];
    if (!file) { showAlert('Sélectionnez un fichier.', 'error'); return; }
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    const fd = new FormData();
    fd.append('file', file);
    try {
        const res = await fetch(`${API_BASE_URL}/avenants/${avenantId}/pieces`, {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: fd,
        });
        if (!res.ok) {
            let msg = 'Échec du téléversement.';
            try { msg = (await res.json()).detail || msg; } catch (e) {}
            throw new Error(msg);
        }
        showAlert('Pièce ajoutée.', 'success');
        const params = new URLSearchParams(window.location.search);
        const subId = parseInt(params.get('id'), 10);
        const holder = document.getElementById('avenantsSection');
        if (subId && holder) await loadAvenantsList(subId, holder);
    } catch (e) {
        showAlert(e.message || 'Échec du téléversement.', 'error');
    }
}

function downloadAvenantPiece(event, avenantId, index) {
    event.preventDefault();
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    fetch(`${API_BASE_URL}/avenants/${avenantId}/pieces/${index}/download`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
        .then((res) => { if (!res.ok) throw new Error('Fichier indisponible'); return res.blob(); })
        .then((blob) => window.open(URL.createObjectURL(blob), '_blank', 'noopener'))
        .catch((err) => showAlert(err.message || 'Impossible d\'ouvrir la pièce.', 'error'));
    return false;
}

function openAvenantPdf(event, avenantId) {
    event.preventDefault();
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    fetch(`${API_BASE_URL}/avenants/${avenantId}/download`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
        .then((res) => { if (!res.ok) throw new Error('PDF indisponible'); return res.blob(); })
        .then((blob) => window.open(URL.createObjectURL(blob), '_blank', 'noopener'))
        .catch((err) => showAlert(err.message || 'Impossible d\'ouvrir le PDF.', 'error'));
    return false;
}
