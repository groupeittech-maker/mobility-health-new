// Garantir l'accès admin
(async function () {
    const allowed = await requireRole('admin', 'index.html');
    if (!allowed) {
        throw new Error('Accès refusé');
    }
})();

const adminAssureursAPI = {
    list: async () => apiCall('/admin/assureurs'),
    create: async (payload) =>
        apiCall('/admin/assureurs', {
            method: 'POST',
            body: JSON.stringify(payload),
        }),
    update: async (id, payload) =>
        apiCall(`/admin/assureurs/${id}`, {
            method: 'PUT',
            body: JSON.stringify(payload),
        }),
    uploadLogo: async (assureurId, file) => {
        const formData = new FormData();
        formData.append('file', file);
        const token = localStorage.getItem('access_token') || localStorage.getItem('access_token'.replace(/"/g, ''));
        const url = `${window.API_BASE_URL || '/api/v1'}/admin/assureurs/${assureurId}/logo`;
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                Authorization: token ? `Bearer ${token}` : '',
            },
            body: formData,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || 'Erreur upload logo');
        }
        return res.json();
    },
};

const agentsAPI = {
    getAvailable: async (role, excludeAssureurId = null) => {
        const url = `/admin/assureurs/agents/available?role=${role}${excludeAssureurId ? `&exclude_assureur_id=${excludeAssureurId}` : ''}`;
        return apiCall(url);
    },
};

let assureursCache = [];
let agentsComptablesCache = [];
let agentsProductionCache = [];
let agentsSinistreCache = [];
let selectedAssureurId = null;

const elements = {};

function cacheDom() {
    elements.assureursList = document.getElementById('assureursList');
    elements.assureurSearchInput = document.getElementById('assureurSearchInput');
    elements.form = document.getElementById('assureurForm');
    elements.formTitle = document.getElementById('formTitle');
    elements.formModeLabel = document.getElementById('formModeLabel');
    elements.assureurId = document.getElementById('assureurId');
    elements.assureurNom = document.getElementById('assureurNom');
    elements.assureurPays = document.getElementById('assureurPays');
    elements.assureurTelephone = document.getElementById('assureurTelephone');
    elements.assureurLogoFile = document.getElementById('assureurLogoFile');
    elements.assureurAdresse = document.getElementById('assureurAdresse');
    elements.agentsComptablesSelect = document.getElementById('agentsComptablesSelect');
    elements.agentsProductionSelect = document.getElementById('agentsProductionSelect');
    elements.agentsSinistreSelect = document.getElementById('agentsSinistreSelect');
    elements.assureurPreview = document.getElementById('assureurPreview');
    elements.saveAssureurBtn = document.getElementById('saveAssureurBtn');
    elements.refreshBtn = document.getElementById('refreshAssureursBtn');
    elements.newBtn = document.getElementById('newAssureurBtn');
    elements.resetBtn = document.getElementById('resetAssureurFormBtn');
}

function attachEvents() {
    if (elements.assureurSearchInput) {
        elements.assureurSearchInput.addEventListener('input', handleSearchInput);
    }
    if (elements.form) {
        elements.form.addEventListener('submit', handleAssureurFormSubmit);
    }
    if (elements.refreshBtn) {
        elements.refreshBtn.addEventListener('click', () => refreshAssureurs(true));
    }
    if (elements.newBtn) {
        elements.newBtn.addEventListener('click', resetAssureurForm);
    }
    if (elements.resetBtn) {
        elements.resetBtn.addEventListener('click', resetAssureurForm);
    }
    elements.assureurLogoFile?.addEventListener('change', updatePreviewCard);
    elements.assureurNom?.addEventListener('input', updatePreviewCard);
    elements.assureurPays?.addEventListener('input', updatePreviewCard);
    
    // Recharger les agents disponibles quand on change d'assureur
    elements.agentsComptablesSelect?.addEventListener('change', () => updatePreviewCard());
    elements.agentsProductionSelect?.addEventListener('change', () => updatePreviewCard());
    elements.agentsSinistreSelect?.addEventListener('change', () => updatePreviewCard());
}

async function initAdminAssureursPage() {
    cacheDom();
    attachEvents();
    showListLoading('Chargement des assureurs...');
    try {
        await Promise.all([
            refreshAssureurs(),
            loadAgents('agent_comptable_assureur', 'comptables'),
            loadAgents('production_agent', 'production'),
            loadAgents('agent_sinistre_assureur', 'sinistre')
        ]);
    } catch (error) {
        console.error('Erreur initialisation assureurs:', error);
        showAlert(error.message || 'Impossible de charger les assureurs.', 'error');
    }
}

function showListLoading(message) {
    if (elements.assureursList) {
        elements.assureursList.innerHTML = `<div class="empty-state">${message}</div>`;
    }
}

async function refreshAssureurs(force = false) {
    if (!force && assureursCache.length) {
        renderAssureurList(assureursCache);
        return;
    }
    showListLoading('Chargement des assureurs...');
    try {
        assureursCache = await adminAssureursAPI.list();
        renderAssureurList(assureursCache);
        if (!assureursCache.length) {
            showAlert('Aucun assureur enregistré. Créez-en un pour activer la sélection côté produits.', 'info');
        }
    } catch (error) {
        console.error('Erreur chargement assureurs:', error);
        showListLoading(error.message || 'Impossible de charger les assureurs.');
    }
}

async function loadAgents(role, type) {
    try {
        const excludeAssureurId = selectedAssureurId || null;
        const agents = await agentsAPI.getAvailable(role, excludeAssureurId);
        
        if (type === 'comptables') {
            agentsComptablesCache = agents;
            populateAgentsSelect(elements.agentsComptablesSelect, agents, 'comptables');
        } else if (type === 'production') {
            agentsProductionCache = agents;
            populateAgentsSelect(elements.agentsProductionSelect, agents, 'production');
        } else if (type === 'sinistre') {
            agentsSinistreCache = agents;
            populateAgentsSelect(elements.agentsSinistreSelect, agents, 'sinistre');
        }
    } catch (error) {
        console.error(`Erreur chargement agents ${type}:`, error);
        showAlert(`Impossible de charger les agents ${type}.`, 'error');
    }
}

function populateAgentsSelect(selectElement, agents, type) {
    if (!selectElement) {
        return;
    }
    
    // Sauvegarder les valeurs sélectionnées
    const selectedValues = Array.from(selectElement.selectedOptions).map(opt => opt.value);
    
    selectElement.innerHTML = '';
    
    if (agents.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Aucun agent disponible';
        selectElement.appendChild(option);
        return;
    }
    
    agents.forEach((agent) => {
        const label = agent.full_name || agent.username || agent.email;
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = label;
        if (agent.is_assigned) {
            option.disabled = true;
            option.textContent += ' (déjà affecté)';
        }
        selectElement.appendChild(option);
    });
    
    // Restaurer les sélections
    if (selectedValues.length > 0) {
        Array.from(selectElement.options).forEach(option => {
            if (selectedValues.includes(option.value)) {
                option.selected = true;
            }
        });
    }
}

function renderAssureurList(list) {
    if (!elements.assureursList) {
        return;
    }
    if (!list.length) {
        elements.assureursList.innerHTML = '<div class="empty-state">Aucun assureur ne correspond à la recherche.</div>';
        return;
    }

    const fragment = document.createDocumentFragment();
    list.forEach((assureur) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `assureur-card${assureur.id === selectedAssureurId ? ' selected' : ''}`;
        button.innerHTML = `
            <div>
                <strong>${assureur.nom}</strong>
                <span>${assureur.pays}</span>
            </div>
            <div class="assureur-meta">
                ${assureur.agents && assureur.agents.length > 0
                    ? `<span>${assureur.agents.length} agent(s) assigné(s)</span>`
                    : assureur.agent_comptable
                        ? `<span>${assureur.agent_comptable.full_name || assureur.agent_comptable.username}</span>`
                        : '<span class="text-muted">Aucun agent assigné</span>'}
            </div>
        `;
        button.addEventListener('click', () => selectAssureur(assureur.id));
        fragment.appendChild(button);
    });
    elements.assureursList.innerHTML = '';
    elements.assureursList.appendChild(fragment);
}

async function selectAssureur(assureurId) {
    const assureur = assureursCache.find((item) => item.id === assureurId);
    if (!assureur) {
        return;
    }
    selectedAssureurId = assureur.id;
    elements.assureurId.value = assureur.id;
    elements.assureurNom.value = assureur.nom;
    elements.assureurPays.value = assureur.pays;
    elements.assureurTelephone.value = assureur.telephone || '';
    elements.assureurAdresse.value = assureur.adresse || '';
    if (elements.assureurLogoFile) elements.assureurLogoFile.value = '';
    
    // Charger les agents disponibles pour cet assureur (pour permettre la modification)
    await Promise.all([
        loadAgents('agent_comptable_assureur', 'comptables'),
        loadAgents('production_agent', 'production'),
        loadAgents('agent_sinistre_assureur', 'sinistre')
    ]);
    
    // Sélectionner les agents existants
    if (assureur.agents && assureur.agents.length > 0) {
        const agentsComptables = assureur.agents.filter(a => a.type_agent === 'comptable').map(a => String(a.id));
        const agentsProduction = assureur.agents.filter(a => a.type_agent === 'production').map(a => String(a.id));
        const agentsSinistre = assureur.agents.filter(a => a.type_agent === 'sinistre').map(a => String(a.id));
        
        Array.from(elements.agentsComptablesSelect.options).forEach(opt => {
            opt.selected = agentsComptables.includes(opt.value);
        });
        Array.from(elements.agentsProductionSelect.options).forEach(opt => {
            opt.selected = agentsProduction.includes(opt.value);
        });
        Array.from(elements.agentsSinistreSelect.options).forEach(opt => {
            opt.selected = agentsSinistre.includes(opt.value);
        });
    } else if (assureur.agent_comptable_id) {
        // Rétrocompatibilité avec l'ancien champ
        elements.agentsComptablesSelect.value = String(assureur.agent_comptable_id);
    }
    
    elements.formTitle.textContent = `Modifier ${assureur.nom}`;
    elements.formModeLabel.textContent = 'Modification';
    renderAssureurList(assureursCache);
    updatePreviewCard();
}

async function resetAssureurForm() {
    selectedAssureurId = null;
    elements.assureurId.value = '';
    elements.assureurNom.value = '';
    elements.assureurPays.value = "Côte d'Ivoire";
    elements.assureurTelephone.value = '';
    elements.assureurAdresse.value = '';
    if (elements.assureurLogoFile) elements.assureurLogoFile.value = '';
    
    // Réinitialiser les selects multiples
    Array.from(elements.agentsComptablesSelect.options).forEach(opt => opt.selected = false);
    Array.from(elements.agentsProductionSelect.options).forEach(opt => opt.selected = false);
    Array.from(elements.agentsSinistreSelect.options).forEach(opt => opt.selected = false);
    
    // Recharger les agents disponibles (sans exclusion)
    await Promise.all([
        loadAgents('agent_comptable_assureur', 'comptables'),
        loadAgents('production_agent', 'production'),
        loadAgents('agent_sinistre_assureur', 'sinistre')
    ]);
    
    elements.formTitle.textContent = 'Nouvel assureur';
    elements.formModeLabel.textContent = 'Création';
    updatePreviewCard();
    renderAssureurList(assureursCache);
}

function getAssureurLogoSrc(assureur) {
    if (!assureur || !assureur.logo_url) return null;
    const url = assureur.logo_url.trim();
    if (url.startsWith('http')) return url;
    const base = window.API_BASE_URL || '/api/v1';
    return base + '/assureurs/' + assureur.id + '/logo';
}

function updatePreviewCard() {
    if (!elements.assureurPreview) {
        return;
    }
    const nom = elements.assureurNom.value.trim() || 'Assureur sans nom';
    const pays = elements.assureurPays.value.trim() || 'Pays non défini';
    const telephone = elements.assureurTelephone.value.trim();
    const adresse = elements.assureurAdresse.value.trim();
    let logoImg = '';
    const fileInput = elements.assureurLogoFile;
    if (fileInput && fileInput.files && fileInput.files[0]) {
        logoImg = `<img src="${URL.createObjectURL(fileInput.files[0])}" alt="Logo de ${nom}" onerror="this.style.display='none'">`;
    } else if (selectedAssureurId) {
        const assureur = assureursCache.find((a) => a.id === selectedAssureurId);
        const logoSrc = getAssureurLogoSrc(assureur);
        if (logoSrc) logoImg = `<img src="${logoSrc}" alt="Logo de ${nom}" onerror="this.style.display='none'">`;
    }
    const agentsComptables = Array.from(elements.agentsComptablesSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => getAgentLabel(id, agentsComptablesCache));
    const agentsProduction = Array.from(elements.agentsProductionSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => getAgentLabel(id, agentsProductionCache));
    const agentsSinistre = Array.from(elements.agentsSinistreSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => getAgentLabel(id, agentsSinistreCache));

    elements.assureurPreview.innerHTML = `
        ${logoImg}
        <div>
            <strong>${nom}</strong>
            <p class="text-muted">${pays}</p>
            ${telephone ? `<p>📞 ${telephone}</p>` : ''}
            ${adresse ? `<p>📍 ${adresse}</p>` : ''}
            ${agentsComptables.length > 0 ? `<p>👤 Agents comptables: ${agentsComptables.join(', ')}</p>` : ''}
            ${agentsProduction.length > 0 ? `<p>🏭 Agents production: ${agentsProduction.join(', ')}</p>` : ''}
            ${agentsSinistre.length > 0 ? `<p>🚨 Agents sinistre: ${agentsSinistre.join(', ')}</p>` : ''}
        </div>
    `;
}

function getAgentLabel(id, cache) {
    if (!id) {
        return '';
    }
    const agent = cache.find((user) => String(user.id) === String(id));
    return agent ? agent.full_name || agent.username || agent.email : '';
}

function handleSearchInput(event) {
    const term = event.target.value?.toLowerCase() || '';
    if (!term) {
        renderAssureurList(assureursCache);
        return;
    }
    const filtered = assureursCache.filter((assureur) => {
        return (
            assureur.nom.toLowerCase().includes(term) ||
            (assureur.pays || '').toLowerCase().includes(term)
        );
    });
    renderAssureurList(filtered);
}

async function handleAssureurFormSubmit(event) {
    event.preventDefault();
    const payload = collectAssureurPayload();
    if (!payload) {
        return;
    }
    const logoFile = elements.assureurLogoFile?.files?.[0];
    elements.saveAssureurBtn.disabled = true;
    elements.saveAssureurBtn.textContent = 'Enregistrement...';
    try {
        let assureurId = selectedAssureurId;
        if (selectedAssureurId) {
            await adminAssureursAPI.update(selectedAssureurId, payload);
            showAlert('Assureur mis à jour avec succès.', 'success');
        } else {
            const created = await adminAssureursAPI.create(payload);
            assureurId = created.id;
            showAlert('Assureur créé avec succès.', 'success');
        }
        if (logoFile && assureurId) {
            elements.saveAssureurBtn.textContent = 'Upload du logo...';
            await adminAssureursAPI.uploadLogo(assureurId, logoFile);
            showAlert('Logo enregistré.', 'success');
        }
        await refreshAssureurs(true);
        resetAssureurForm();
    } catch (error) {
        console.error('Erreur enregistrement assureur:', error);
        showAlert(error.message || 'Impossible d’enregistrer cet assureur.', 'error');
    } finally {
        elements.saveAssureurBtn.disabled = false;
        elements.saveAssureurBtn.textContent = 'Enregistrer';
    }
}

function collectAssureurPayload() {
    const nom = elements.assureurNom.value.trim();
    const pays = elements.assureurPays.value.trim();
    if (!nom || !pays) {
        showAlert('Le nom et le pays sont obligatoires.', 'error');
        return null;
    }
    const telephone = elements.assureurTelephone.value.trim();
    const adresse = elements.assureurAdresse.value.trim();
    
    // Récupérer les IDs des agents sélectionnés
    const agentsComptablesIds = Array.from(elements.agentsComptablesSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => Number(id));
    const agentsProductionIds = Array.from(elements.agentsProductionSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => Number(id));
    const agentsSinistreIds = Array.from(elements.agentsSinistreSelect.selectedOptions)
        .map(opt => opt.value)
        .filter(v => v)
        .map(id => Number(id));

    return {
        nom,
        pays,
        telephone: telephone || undefined,
        adresse: adresse || undefined,
        agents_comptables_ids: agentsComptablesIds.length > 0 ? agentsComptablesIds : null,
        agents_production_ids: agentsProductionIds.length > 0 ? agentsProductionIds : null,
        agents_sinistre_ids: agentsSinistreIds.length > 0 ? agentsSinistreIds : null,
    };
}

document.addEventListener('DOMContentLoaded', initAdminAssureursPage);



