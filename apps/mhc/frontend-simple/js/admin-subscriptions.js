// Vérifier l'authentification et le rôle admin
(async function() {
    // Les souscriptions peuvent être gérées par admin ou finance_manager
    const isValid = await requireBackoffice('index.html');
    if (!isValid) {
        return; // requireAnyRole() a déjà redirigé
    }
})();

// API pour les souscriptions admin
const adminSubscriptionsAPI = {
    getPending: async () => {
        // Limiter à 100 par défaut pour éviter les timeouts
        return apiCall('/admin/subscriptions/pending?limit=100');
    },
    
    getAll: async () => {
        return apiCall('/admin/subscriptions/?limit=1000');
    },
    
    getById: async (id) => {
        return apiCall(`/admin/subscriptions/${id}`);
    },
    
    validate: async (id, data) => {
        return apiCall(`/admin/subscriptions/${id}/validate`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    getDossier: async (id) => {
        return apiCall(`/admin/subscriptions/${id}/dossier`);
    },

    validateMedical: async (id, data) => {
        return apiCall(`/admin/subscriptions/${id}/validate_medical`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    approveFinal: async (id, data) => {
        return apiCall(`/admin/subscriptions/${id}/approve_final`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
};

let subscriptionsCache = [];
let searchSubscriptionsTerm = '';
const ROWS_PER_PAGE = 6;
let currentPageSubscriptions = 0;

function getUserDisplayName(sub) {
    if (!sub) return '—';
    const u = sub.user;
    if (u) {
        if (u.full_name && u.full_name.trim()) return u.full_name.trim();
        if (u.email && u.email.trim()) return u.email.trim();
        if (u.username && u.username.trim()) return u.username.trim();
    }
    return sub.user_id != null ? `User #${sub.user_id}` : '—';
}

function escapeHtml(text) {
    if (text == null) return '';
    const s = String(text);
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Charger les souscriptions
async function loadSubscriptions() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        console.error('Container subscriptionsTableContainer non trouvé');
        return;
    }
    
    showLoading(container);
    
    try {
        // Vérifier la connexion au serveur avant de faire l'appel
        const apiUrl = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
        try {
            const healthCheck = await fetch(`${apiUrl.replace('/api/v1', '')}/health`);
            if (!healthCheck.ok) {
                throw new Error('Serveur backend non disponible');
            }
        } catch (healthError) {
            container.innerHTML = `
                <div class="alert alert-error">
                    <h3>Erreur de connexion</h3>
                    <p>Impossible de se connecter au serveur backend.</p>
                    <p><strong>Vérifications à effectuer :</strong></p>
                    <ul>
                        <li>Le serveur backend est-il accessible sur https://api.srv1324425.hstgr.cloud ?</li>
                        <li>Vérifiez la console du navigateur pour plus de détails</li>
                        <li>URL attendue : ${apiUrl}</li>
                    </ul>
                    <p><small>Erreur : ${healthError.message}</small></p>
                    <button class="btn btn-primary" onclick="loadSubscriptions()">Réessayer</button>
                </div>
            `;
            return;
        }
        
        const statusFilter = document.getElementById('statusFilter')?.value || 'all';
        let subscriptions = [];
        
        if (statusFilter === 'pending') {
            subscriptions = await adminSubscriptionsAPI.getPending();
        } else {
            subscriptions = await adminSubscriptionsAPI.getAll();
            if (statusFilter === 'active') {
                subscriptions = subscriptions.filter(s => s.statut === 'active');
            }
        }
        
        if (subscriptions.length === 0) {
            subscriptionsCache = [];
            container.innerHTML = '<p>Aucune souscription trouvée.</p>';
            return;
        }
        
        subscriptionsCache = subscriptions;
        searchSubscriptionsTerm = (document.getElementById('searchSubscriptions')?.value || '').trim().toLowerCase();
        renderSubscriptionsTable();
        bindSubscriptionsSearch();
    } catch (error) {
        console.error('Erreur lors du chargement des souscriptions:', error);
        const errorMessage = error.message || 'Erreur inconnue';
        
        // Vérifier si c'est une erreur de connexion
        const isConnectionError = errorMessage.includes('connecter') || 
                                  errorMessage.includes('Failed to fetch') ||
                                  errorMessage.includes('backend');
        
        container.innerHTML = `
            <div class="alert alert-error">
                <h3>Erreur de chargement</h3>
                <p>${errorMessage}</p>
                ${isConnectionError ? `
                    <p><strong>Le serveur backend n'est peut-être pas démarré.</strong></p>
                    <p>Vérifiez que le backend est accessible sur https://api.srv1324425.hstgr.cloud</p>
                    <p>Vous pouvez le démarrer avec : <code>.\scripts\start_backend.ps1</code></p>
                ` : ''}
                <p><small>Vérifiez la console pour plus de détails.</small></p>
                <button class="btn btn-primary" onclick="loadSubscriptions()">Réessayer</button>
            </div>
        `;
    }
}

function bindSubscriptionsSearch() {
    const searchEl = document.getElementById('searchSubscriptions');
    if (searchEl && !searchEl.dataset.bound) {
        searchEl.dataset.bound = 'true';
        searchEl.addEventListener('input', () => {
            searchSubscriptionsTerm = (searchEl.value || '').trim().toLowerCase();
            if (subscriptionsCache.length) {
                renderSubscriptionsTable();
            }
        });
    }
}

function renderSubscriptionsTable() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        return;
    }
        const filtered = searchSubscriptionsTerm
        ? subscriptionsCache.filter((sub) => {
            const numero = (sub.numero_souscription || '').toLowerCase();
            const userDisplay = getUserDisplayName(sub).toLowerCase();
            const userId = (sub.user_id != null ? String(sub.user_id) : '').toLowerCase();
            const statut = (sub.statut || '').toLowerCase();
            const date = new Date(sub.created_at).toLocaleDateString('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).toLowerCase();
            return numero.includes(searchSubscriptionsTerm) || userDisplay.includes(searchSubscriptionsTerm) ||
                userId.includes(searchSubscriptionsTerm) || statut.includes(searchSubscriptionsTerm) ||
                date.includes(searchSubscriptionsTerm);
        })
        : subscriptionsCache;

    if (filtered.length === 0) {
        container.innerHTML = '<p>' + (subscriptionsCache.length ? 'Aucune souscription ne correspond à la recherche.' : 'Aucune souscription trouvée.') + '</p>';
        return;
    }

    const totalPages = Math.max(1, Math.ceil(filtered.length / ROWS_PER_PAGE));
    currentPageSubscriptions = Math.min(currentPageSubscriptions, totalPages - 1);
    const start = currentPageSubscriptions * ROWS_PER_PAGE;
    const pageData = filtered.slice(start, start + ROWS_PER_PAGE);

    let html = '<div class="table-wrapper" style="overflow-x: scroll !important;"><table class="data-table" style="min-width: 100%;"><thead><tr>';
    html += '<th>Numéro</th><th>Utilisateur</th><th>Prix</th><th>Statut</th><th>Date</th><th>Actions</th>';
    html += '</tr></thead><tbody>';

    pageData.forEach(sub => {
        const statusClass = sub.statut === 'active' ? 'status-active' :
            sub.statut === 'en_attente' ? 'status-pending' : 'status-inactive';
        const date = new Date(sub.created_at).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
        const userDisplay = getUserDisplayName(sub);
        html += `
            <tr>
                <td>${sub.numero_souscription}</td>
                <td>${escapeHtml(userDisplay)}</td>
                <td>${parseFloat(sub.prix_applique).toFixed(2)} FCFA</td>
                <td><span class="status-badge ${statusClass}">${sub.statut}</span></td>
                <td>${date}</td>
                <td class="table-actions">
                    <select class="action-select" data-subscription-id="${sub.id}">
                        <option value="">Actions</option>
                        <option value="view">Voir</option>
                    </select>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';
    if (filtered.length > ROWS_PER_PAGE) {
        const end = Math.min(start + ROWS_PER_PAGE, filtered.length);
        html += `
            <div class="table-pagination-wrapper" style="margin-top: 1rem;">
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${filtered.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="subPrev" ${currentPageSubscriptions <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageSubscriptions + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="subNext" ${currentPageSubscriptions >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            </div>
        `;
    }
    container.innerHTML = html;
    setupSubscriptionsTableActions();
    if (filtered.length > ROWS_PER_PAGE) {
        document.getElementById('subPrev')?.addEventListener('click', () => { currentPageSubscriptions--; renderSubscriptionsTable(); });
        document.getElementById('subNext')?.addEventListener('click', () => { currentPageSubscriptions++; renderSubscriptionsTable(); });
    }

    setTimeout(() => {
        const wrapper = container.querySelector('.table-wrapper');
        if (wrapper) {
            wrapper.style.overflowX = 'scroll';
            const table = wrapper.querySelector('.data-table');
            if (table && table.offsetWidth <= wrapper.clientWidth) {
                table.style.minWidth = `${wrapper.clientWidth + 2}px`;
            }
        }
    }, 100);
}

// ==================== Modal dossier de souscription ====================

/// Rôles habilités à trancher chaque étape du pipeline de validation
/// (aligné sur admin_subscriptions.py : validate_medical / approve_final).
const _REVIEW_ROLES_BY_STEP = {
    medecin: ['admin', 'doctor', 'medical_reviewer', 'medecin_referent_mh',
              'agent_medical_mhc', 'superviseur_affaires_medicales'],
    production: ['admin', 'production_agent'],
};
const _VALIDATE_API_BY_STEP = {
    medecin: (id, data) => adminSubscriptionsAPI.validateMedical(id, data),
    production: (id, data) => adminSubscriptionsAPI.approveFinal(id, data),
};
const _STEP_LABELS = {
    medecin: 'Validation médicale (médecin référent MH)',
    technique: 'Validation technique',
    production: 'Validation finale (agent de production MHC)',
};

function _currentRole() {
    return (localStorage.getItem('user_role') || '').toLowerCase().trim();
}

function _fmtDossierDate(value) {
    if (!value) return '—';
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString('fr-FR');
}

function _dossierRow(label, value) {
    if (value === null || value === undefined || value === '') return '';
    return `<div class="dossier-field">
        <span>${label}</span>
        <strong>${escapeHtml(String(value))}</strong>
    </div>`;
}

function _dossierCard(title, inner) {
    if (!inner || !inner.trim()) return '';
    return `<div class="dossier-card"><h4>${title}</h4>${inner}</div>`;
}

function _dossierBlock(title, inner) {
    if (!inner || !inner.trim()) return '';
    return `<h4 class="dossier-block-title">${title}</h4>${inner}`;
}

/// Libellés lisibles pour les clés du questionnaire médical simplifié.
const _QUESTION_LABELS = {
    declaration_sante: 'Déclaration santé acceptée',
    malade_souscription: 'Malade au moment de la souscription',
    malade_12_mois: 'Maladie / hospitalisation (12 derniers mois)',
    maladie_chronique: 'Maladie chronique déclarée',
    enceinte: 'Grossesse en cours',
    pregnancy: 'Grossesse en cours',
    voyage_medical: 'Voyage entrepris à but médical',
    activite_sportive_pro: 'Activité sportive professionnelle',
    photo_medicale: 'Photo du souscripteur',
    date_soumission: 'Soumis le',
    version: null, // champ technique masqué
};

function _formatReponseValue(v) {
    if (v === null || v === undefined || v === '') return null;
    if (typeof v === 'boolean') return v ? 'Oui' : 'Non';
    if (typeof v === 'string' && (v === 'oui' || v === 'non')) return v === 'oui' ? 'Oui' : 'Non';
    if (Array.isArray(v)) return v.map(_formatReponseValue).filter(Boolean).join(', ') || null;
    if (typeof v === 'object') {
        return Object.entries(v)
            .map(([k, val]) => `${k}: ${_formatReponseValue(val) ?? '—'}`)
            .join(' ; ');
    }
    return String(v);
}

function _dossierRowData(label, v) {
    // Photo encodée en base64 dans les réponses → vignette cliquable.
    if (typeof v === 'string' && v.startsWith('data:image/')) {
        return `<div class="dossier-field" style="align-items:center;">
            <span>${label}</span>
            <a href="${v}" target="_blank" rel="noopener" title="Ouvrir en plein écran">
                <img src="${v}" alt="${escapeHtml(label)}" class="dossier-photo">
            </a>
        </div>`;
    }
    return _dossierRow(label, _formatReponseValue(v));
}

function _renderQuestionnaires(questionnaires) {
    if (!questionnaires) return '';
    // Le backend renvoie un dict {medical: {...}, ...} — accepter aussi une liste.
    const list = Array.isArray(questionnaires)
        ? questionnaires
        : Object.values(questionnaires);
    if (!list.length) return '';
    return list.map(q => {
        const reponses = q.reponses || {};
        // Dédupliquer les doublons snake_case / camelCase renvoyés ensemble.
        const seen = new Set();
        const rows = Object.entries(reponses).map(([k, v]) => {
            const snake = k.replace(/[A-Z]/g, c => '_' + c.toLowerCase());
            if (seen.has(snake)) return '';
            seen.add(snake);
            const label = _QUESTION_LABELS[snake];
            if (label === null) return '';
            if (snake === 'date_soumission') {
                return _dossierRow(label, _fmtDossierDate(v));
            }
            return _dossierRowData(label || k.replace(/_/g, ' '), v);
        }).join('');
        return `<div class="dossier-questionnaire">
            <strong>${escapeHtml((q.type_questionnaire || 'Questionnaire').replace(/_/g, ' '))}</strong>
            ${rows || '<p style="font-size:.8rem;color:#94a3b8;margin:0;">Aucune réponse enregistrée.</p>'}
        </div>`;
    }).join('');
}

function _renderDocuments(docs) {
    if (!docs || !docs.length) return '';
    return docs.map(d => {
        const name = escapeHtml(d.display_name || `Document #${d.id}`);
        const isImage = (d.content_type || '').startsWith('image/');
        const thumb = isImage && d.download_url
            ? `<a href="${escapeHtml(d.download_url)}" target="_blank" rel="noopener"><img src="${escapeHtml(d.download_url)}" alt="${name}" class="dossier-photo"></a>`
            : '';
        return `<div class="dossier-doc">${thumb}${d.download_url
            ? `<a href="${escapeHtml(d.download_url)}" target="_blank" rel="noopener">${name}</a>`
            : `<span>${name}</span>`}</div>`;
    }).join('');
}

/// Première étape du pipeline encore « pending » — c'est celle que
/// l'utilisateur courant peut trancher si son rôle l'y autorise.
function _pendingValidationStep(dossier) {
    const v = dossier.validations || {};
    if ((v.medecin?.status || 'pending') === 'pending') return 'medecin';
    if ((v.production?.status || 'pending') === 'pending' ||
        (v.technique?.status || 'pending') === 'pending') return 'production';
    return null;
}

function _renderDossierHtml(dossier) {
    let html = '';

    const grid = [];
    grid.push(_dossierCard('Souscription',
        _dossierRow('Statut', dossier.souscription_status) +
        _dossierRow('Produit', dossier.produit_nom) +
        _dossierRow('Montant', dossier.prix_applique != null ? `${Number(dossier.prix_applique).toFixed(2)} ${dossier.currency || 'XAF'}` : null) +
        _dossierRow('Période', dossier.date_debut || dossier.date_fin
            ? `du ${_fmtDossierDate(dossier.date_debut)} au ${_fmtDossierDate(dossier.date_fin)}` : null) +
        _dossierRow('Destination', [dossier.travel_destination_city, dossier.travel_destination_country].filter(Boolean).join(', '))));

    grid.push(_dossierCard('Souscripteur',
        _dossierRow('Nom', dossier.client_name) +
        _dossierRow('E-mail', dossier.client_email) +
        _dossierRow('Téléphone', dossier.client_telephone) +
        _dossierRow('Naissance', _fmtDossierDate(dossier.client_date_naissance)) +
        _dossierRow('Sexe', dossier.client_sexe) +
        _dossierRow('Nationalité', dossier.client_nationalite) +
        _dossierRow('Passeport', dossier.client_numero_passeport) +
        _dossierRow('Validité passeport', _fmtDossierDate(dossier.client_validite_passeport)) +
        _dossierRow('Pays de résidence', dossier.client_pays_residence)));

    if (dossier.is_tier_subscription) {
        grid.push(_dossierCard('Bénéficiaire (tiers)',
            _dossierRow('Nom', dossier.tier_full_name) +
            _dossierRow('Naissance', _fmtDossierDate(dossier.tier_birth_date)) +
            _dossierRow('Sexe', dossier.tier_gender) +
            _dossierRow('Nationalité', dossier.tier_nationality) +
            _dossierRow('Passeport', dossier.tier_passport_number) +
            _dossierRow('Validité passeport', _fmtDossierDate(dossier.tier_passport_expiry_date)) +
            _dossierRow('Téléphone', dossier.tier_phone) +
            _dossierRow('E-mail', dossier.tier_email)));
    }

    if (dossier.minors_info && dossier.minors_info.length) {
        grid.push(_dossierCard('Enfants / mineurs',
            dossier.minors_info.map(m =>
                _dossierRow('Mineur', [m.nom_complet, m.date_naissance].filter(Boolean).join(' — '))
            ).join('')));
    }
    html += `<div class="dossier-grid">${grid.join('')}</div>`;

    // Pipeline en stepper horizontal : médecin → production.
    const v = dossier.validations || {};
    const stepIcon = { approved: '✓', rejected: '✕', pending: '…' };
    const stepHtml = ['medecin', 'technique', 'production'].map(step => {
        const st = v[step] || {};
        const status = (st.status || 'pending').toLowerCase();
        if (status === 'not_required') {
            return `<div class="dossier-step skipped">
                <div class="step-dot">—</div>
                <div class="step-label">${_STEP_LABELS[step]}</div>
                <div class="step-meta">Non requise</div>
            </div>`;
        }
        if (step === 'technique' && status === 'pending' && !st.decided_at) return '';
        const statusCls = status === 'approved' ? 'approved' : status === 'rejected' ? 'rejected' : 'pending';
        return `<div class="dossier-step ${statusCls}">
            <div class="step-dot">${stepIcon[statusCls] || '…'}</div>
            <div class="step-label">${_STEP_LABELS[step]}</div>
            ${st.decided_at ? `<div class="step-meta">${_fmtDossierDate(st.decided_at)}</div>` : ''}
            ${st.notes ? `<div class="step-meta">${escapeHtml(st.notes)}</div>` : ''}
        </div>`;
    }).join('');
    html += _dossierBlock('Pipeline de validation', `<div class="dossier-steps">${stepHtml}</div>`);

    html += _dossierBlock('Questionnaires médicaux', _renderQuestionnaires(dossier.questionnaires));
    html += _dossierBlock('Documents du voyage', _renderDocuments(dossier.documents_projet_voyage));

    // Actions de validation selon l'étape en attente et le rôle courant.
    const step = _pendingValidationStep(dossier);
    if (step && dossier.souscription_status === 'en_attente_validation') {
        const role = _currentRole();
        if (_REVIEW_ROLES_BY_STEP[step].includes(role)) {
            html += `<div class="dossier-decision" id="dossierActions" data-step="${step}">
                <h4>Votre décision — ${_STEP_LABELS[step]}</h4>
                <textarea id="dossierNotes" class="form-input" rows="3" placeholder="Notes / motif (recommandé en cas de refus)"></textarea>
                <div class="decision-btns">
                    <button type="button" class="btn btn-primary" id="dossierApprove">✓ Approuver</button>
                    <button type="button" class="btn btn-outline" id="dossierReject" style="color:#b91c1c;border-color:#fca5a5;">✕ Refuser</button>
                </div>
            </div>`;
        } else {
            html += `<div class="dossier-readonly-note">
                Votre rôle permet la consultation. ${_STEP_LABELS[step]} est réservée
                ${step === 'medecin' ? 'au personnel médical MHC (médecin référent, agent médical).' : "à l'agent de production MHC."}
            </div>`;
        }
    }

    return html || '<p>Aucune information disponible pour ce dossier.</p>';
}

async function _submitDossierDecision(dossierId, approved) {
    const actionsEl = document.getElementById('dossierActions');
    const step = actionsEl?.dataset.step;
    if (!step) return;
    const notes = (document.getElementById('dossierNotes')?.value || '').trim() || null;
    if (!approved && !notes && !confirm('Refuser sans indiquer de motif ?')) return;
    try {
        await _VALIDATE_API_BY_STEP[step](dossierId, { approved, notes });
        showAlert(approved ? 'Dossier approuvé.' : 'Dossier refusé.', 'success');
        _closeDossierModal();
        loadSubscriptions();
    } catch (e) {
        showAlert(e.message || 'La décision n\'a pas pu être enregistrée.', 'error');
    }
}

function _bindDossierActions(body, dossier) {
    body.querySelector('#dossierApprove')?.addEventListener('click', () =>
        _submitDossierDecision(dossier.souscription_id, true));
    body.querySelector('#dossierReject')?.addEventListener('click', () =>
        _submitDossierDecision(dossier.souscription_id, false));
}

function _closeDossierModal() {
    const overlay = document.getElementById('subscriptionDossierModal');
    if (overlay) overlay.hidden = true;
}

function _ensureDossierModal() {
    let overlay = document.getElementById('subscriptionDossierModal');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'subscriptionDossierModal';
    overlay.className = 'mh-modal-overlay';
    overlay.hidden = true;
    overlay.innerHTML = `
        <div class="reception-dossier-modal" style="max-width:860px;">
            <div class="mh-modal-header">
                <h3 id="subDossierTitle">Dossier de souscription</h3>
                <div class="mh-modal-header-actions">
                    <span id="subDossierStatus"></span>
                    <button type="button" class="btn btn-outline btn-sm" id="subDossierClose">Fermer</button>
                </div>
            </div>
            <div class="mh-modal-scroll" id="subDossierBody"></div>
        </div>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) _closeDossierModal();
    });
    overlay.querySelector('#subDossierClose').addEventListener('click', _closeDossierModal);
    return overlay;
}

async function viewSubscription(id) {
    const overlay = _ensureDossierModal();
    const body = document.getElementById('subDossierBody');
    const title = document.getElementById('subDossierTitle');
    overlay.hidden = false;
    title.textContent = `Dossier — souscription #${id}`;
    document.getElementById('subDossierStatus').innerHTML = '';
    body.innerHTML = '<div class="mh-modal-loading"><div class="spinner"></div><p>Chargement du dossier…</p></div>';
    try {
        const dossier = await adminSubscriptionsAPI.getDossier(id);
        title.textContent = `Dossier ${dossier.numero_souscription || '#' + id}`;
        const st = (dossier.souscription_status || '').toLowerCase();
        const stCls = st === 'active' ? 'status-active'
            : st === 'en_attente_validation' || st === 'en_attente_paiement' || st === 'en_attente' ? 'status-pending'
            : 'status-inactive';
        document.getElementById('subDossierStatus').innerHTML =
            `<span class="status-badge ${stCls}">${escapeHtml(dossier.souscription_status || '—')}</span>`;
        body.innerHTML = _renderDossierHtml(dossier);
        _bindDossierActions(body, dossier);
    } catch (e) {
        body.innerHTML = `<div class="alert alert-error" style="margin:1rem 0;"><p>${escapeHtml(e.message || 'Chargement du dossier impossible.')}</p></div>`;
    }
}

function setupSubscriptionsTableActions() {
    const container = document.getElementById('subscriptionsTableContainer');
    if (!container) {
        return;
    }
    
    container.addEventListener('change', (event) => {
        const select = event.target.closest('.action-select');
        if (!select) {
            return;
        }
        
        const action = select.value;
        if (!action) {
            return;
        }
        
        const subscriptionId = parseInt(select.dataset.subscriptionId, 10);
        if (Number.isNaN(subscriptionId)) {
            return;
        }
        
        switch (action) {
            case 'view':
                viewSubscription(subscriptionId);
                break;
        }
        
        // Réinitialiser le select
        select.value = '';
    });
}

// Charger les souscriptions au chargement de la page
document.addEventListener('DOMContentLoaded', loadSubscriptions);

