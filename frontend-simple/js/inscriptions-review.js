/**
 * Page Validation des inscriptions (médecin MH).
 * Consulter les informations enregistrées (civiles) puis valider ou refuser.
 */
document.addEventListener('DOMContentLoaded', async () => {
    const allowedRoles = ['medical_reviewer', 'admin'];
    const hasAccess = await requireAnyRole(allowedRoles, 'index.html');
    if (!hasAccess) return;

    const loadingEl = document.getElementById('inscriptionsLoading');
    const errorEl = document.getElementById('inscriptionsError');
    const emptyEl = document.getElementById('inscriptionsEmpty');
    const listEl = document.getElementById('inscriptionsList');

    async function loadInscriptions() {
        if (errorEl) errorEl.hidden = true;
        if (loadingEl) loadingEl.hidden = false;
        if (emptyEl) emptyEl.hidden = true;
        if (listEl) listEl.hidden = true;

        try {
            const data = await apiCall('/users?validation_inscription=pending&limit=200');
            const items = Array.isArray(data) ? data : [];
            if (loadingEl) loadingEl.hidden = true;
            if (!items.length) {
                if (emptyEl) emptyEl.hidden = false;
                return;
            }
            renderInscriptions(items);
            if (listEl) listEl.hidden = false;
        } catch (err) {
            if (loadingEl) loadingEl.hidden = true;
            if (errorEl) {
                errorEl.textContent = err.message || 'Impossible de charger les inscriptions.';
                errorEl.hidden = false;
            }
        }
    }

    function escapeHtml(str) {
        if (str == null) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatDate(val) {
        if (!val) return '—';
        const d = new Date(val);
        return isNaN(d.getTime()) ? String(val) : d.toLocaleDateString('fr-FR');
    }

    const rowStyle = 'display: flex; justify-content: space-between; align-items: flex-start; padding: 0.5rem 0; border-bottom: 1px solid #eee; gap: 0.75rem;';
    function renderDetailRow(label, value, valueHtml) {
        const content = valueHtml !== undefined ? valueHtml : escapeHtml(value || '—');
        return `
            <div class="inscription-detail-row" style="${rowStyle}">
                <span class="inscription-detail-label">${escapeHtml(label)}</span>
                <span class="inscription-detail-value">${content}</span>
            </div>
        `;
    }

    /** Court libellé pour une ligne d’antécédent (texte avant le premier ": "). */
    function parseAntecedentsRows(raw) {
        if (!raw || typeof raw !== 'string') return [];
        const lines = raw.trim().split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
        return lines.map((line) => {
            const idx = line.indexOf(': ');
            const label = idx >= 0 ? line.slice(0, idx).trim() : line;
            const value = idx >= 0 ? line.slice(idx + 2).trim() : '—';
            return { label, value };
        });
    }

    function parseTraitementRow(value) {
        if (!value || typeof value !== 'string') return null;
        const s = value.trim();
        if (!s) return null;
        const match = s.match(/Traitement médical régulier\s*:\s*(Oui|Non)(.*)/i);
        const val = match ? match[1] + (match[2].trim() ? ' ' + match[2].trim() : '') : s;
        return { label: 'Traitement en cours régulier', value: val };
    }

    function renderDetailContent(u) {
        const grossesseLabel = u.grossesse === true ? 'Oui' : u.grossesse === false ? 'Non' : '—';
        const sectionClass = 'inscription-modal-section';
        const sectionMedicalClass = 'inscription-modal-section inscription-modal-section-medical';
        const titleClass = 'inscription-modal-section-title';

        const donneesCiviles = [
            { label: 'Nom complet', value: u.full_name || u.username },
            { label: 'Date de naissance', value: formatDate(u.date_naissance) },
            { label: 'Sexe', value: u.sexe === 'M' ? 'Homme' : u.sexe === 'F' ? 'Femme' : u.sexe },
            { label: 'Nationalité', value: u.nationalite },
            { label: 'Pays de résidence', value: u.pays_residence },
            { label: 'N° passeport', value: u.numero_passeport },
            { label: 'Validité passeport', value: formatDate(u.validite_passeport) },
            { label: 'Téléphone', value: u.telephone },
            { label: 'Contact d\'urgence', value: u.contact_urgence },
        ].map((f) => renderDetailRow(f.label, f.value)).join('');

        const traitRow = parseTraitementRow(u.traitements_en_cours);
        const antecRows = parseAntecedentsRows(u.antecedents_recents);
        const donneesMedicales = [
            renderDetailRow('Maladies chroniques', u.maladies_chroniques),
            traitRow ? renderDetailRow(traitRow.label, traitRow.value) : renderDetailRow('Traitements en cours', u.traitements_en_cours),
            ...antecRows.map((r) => renderDetailRow(r.label, r.value)),
            renderDetailRow('Grossesse (si concernée)', grossesseLabel),
        ].join('');

        const donneesPersonnelles = [
            { label: 'Email', value: u.email },
            { label: 'Nom d\'utilisateur', value: u.username },
            { label: 'Date d\'inscription', value: formatDate(u.created_at) },
        ].map((f) => renderDetailRow(f.label, f.value)).join('');

        return `
            <div class="${sectionClass} inscription-modal-section-civiles">
                <h4 class="${titleClass}">Données civiles</h4>
                <div class="inscription-detail-fields">${donneesCiviles}</div>
            </div>
            <div class="${sectionMedicalClass}">
                <h4 class="${titleClass}">Données médicales</h4>
                <div class="inscription-detail-fields inscription-detail-fields-medical">${donneesMedicales}</div>
            </div>
            <div class="${sectionClass} inscription-modal-section-personnelles">
                <h4 class="${titleClass}">Données personnelles (pour connexion au compte)</h4>
                <div class="inscription-detail-fields">${donneesPersonnelles}</div>
            </div>
        `;
    }

    function openDetailModal(userId) {
        const overlay = document.getElementById('inscriptionDetailOverlay');
        const modal = document.getElementById('inscriptionDetailModal');
        const body = document.getElementById('inscriptionDetailBody');
        const detailLoading = document.getElementById('inscriptionDetailLoading');
        if (!overlay || !modal || !body) return;
        body.innerHTML = '';
        detailLoading.style.display = 'block';
        overlay.hidden = false;
        modal.hidden = false;
        apiCall(`/users/${userId}`)
            .then((u) => {
                detailLoading.style.display = 'none';
                body.innerHTML = `<div class="inscription-detail-fields">${renderDetailContent(u)}</div>
                    <div style="margin-top: 1.25rem; display: flex; gap: 0.5rem; justify-content: flex-end;">
                        <button type="button" class="btn btn-secondary btn-sm" id="inscriptionDetailCloseBtn">Fermer</button>
                        <button type="button" class="btn btn-primary btn-sm btn-approve" data-user-id="${u.id}">Valider</button>
                        <button type="button" class="btn btn-secondary btn-sm btn-reject" data-user-id="${u.id}">Refuser</button>
                    </div>`;
                document.getElementById('inscriptionDetailCloseBtn').onclick = closeDetailModal;
                body.querySelector('.btn-approve').onclick = () => { closeDetailModal(); handleValidate(Number(userId), true); };
                body.querySelector('.btn-reject').onclick = () => { closeDetailModal(); handleValidate(Number(userId), false); };
            })
            .catch((err) => {
                detailLoading.style.display = 'none';
                body.innerHTML = `<p class="alert alert-error">${escapeHtml(err.message || 'Impossible de charger le détail.')}</p>
                    <button type="button" class="btn btn-secondary btn-sm" onclick="document.getElementById('inscriptionDetailOverlay').hidden=true; document.getElementById('inscriptionDetailModal').hidden=true;">Fermer</button>`;
            });
    }

    function closeDetailModal() {
        const overlay = document.getElementById('inscriptionDetailOverlay');
        const modal = document.getElementById('inscriptionDetailModal');
        if (overlay) overlay.hidden = true;
        if (modal) modal.hidden = true;
    }

    window.closeInscriptionDetailModal = closeDetailModal;

    function renderInscriptions(items) {
        if (!listEl) return;
        listEl.innerHTML = `
            <h3>Inscriptions en attente (<span id="inscriptionsCount">${items.length}</span>)</h3>
            <div class="review-grid" id="inscriptionsGrid"></div>
        `;
        const grid = document.getElementById('inscriptionsGrid');
        if (!grid) return;
        grid.innerHTML = items.map((u) => {
            const name = escapeHtml(u.full_name || u.username || u.email || '—');
            const email = escapeHtml(u.email || '—');
            const created = u.created_at ? new Date(u.created_at).toLocaleDateString('fr-FR') : '—';
            return `
                <div class="card review-card" data-user-id="${u.id}">
                    <div class="card-body">
                        <h4 class="card-title">${name}</h4>
                        <p class="muted">${email}</p>
                        <p class="small">Inscription le ${created}</p>
                        <div class="review-card-actions" style="margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
                            <button type="button" class="btn btn-outline btn-sm btn-detail" data-user-id="${u.id}">Voir les informations</button>
                            <button type="button" class="btn btn-primary btn-sm btn-approve" data-user-id="${u.id}">Valider</button>
                            <button type="button" class="btn btn-secondary btn-sm btn-reject" data-user-id="${u.id}">Refuser</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        grid.querySelectorAll('.btn-detail').forEach((btn) => {
            btn.addEventListener('click', () => openDetailModal(Number(btn.dataset.userId)));
        });
        grid.querySelectorAll('.btn-approve').forEach((btn) => {
            btn.addEventListener('click', () => handleValidate(Number(btn.dataset.userId), true));
        });
        grid.querySelectorAll('.btn-reject').forEach((btn) => {
            btn.addEventListener('click', () => handleValidate(Number(btn.dataset.userId), false));
        });
    }

    async function handleValidate(userId, approved) {
        const notes = approved ? null : (window.prompt('Motif du refus (optionnel)') || null);
        try {
            await apiCall(`/users/${userId}/validate_inscription`, {
                method: 'POST',
                body: JSON.stringify({ approved, notes }),
            });
            if (typeof showAlert === 'function') {
                showAlert(approved ? 'Inscription validée. L\'abonné peut se connecter.' : 'Inscription refusée.', 'success');
            }
            await loadInscriptions();
        } catch (err) {
            if (typeof showAlert === 'function') {
                showAlert(err.message || 'Erreur lors de la validation.', 'error');
            }
        }
    }

    await loadInscriptions();
});
