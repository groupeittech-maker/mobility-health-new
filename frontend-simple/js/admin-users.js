// Vérifier l'authentification et le rôle admin
(async function() {
    const isValid = await requireRole('admin', 'index.html');
    if (!isValid) {
        return; // requireRole() a déjà redirigé
    }
})();

// API pour les utilisateurs
const usersAPI = {
    getAll: async () => {
        // Le backend attend une barre oblique finale, sinon le navigateur suit une redirection 307 qui échoue en CORS.
        return apiCall('/users/?limit=1000');
    },
    
    create: async (data) => {
        return apiCall('/users/', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    
    getById: async (id) => {
        return apiCall(`/users/${id}`);
    },
    
    update: async (id, data) => {
        return apiCall(`/users/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },
    
    delete: async (id) => {
        return apiCall(`/users/${id}`, {
            method: 'DELETE',
        });
    },
    
    resetPassword: async (id, data) => {
        return apiCall(`/users/${id}/reset-password`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
};

const ROLE_OPTIONS = [
    { value: 'admin', label: 'Administrateur' },
    { value: 'user', label: 'Utilisateur' },
    { value: 'doctor', label: 'Médecin' },
    { value: 'hospital_admin', label: 'Admin hôpital' },
    { value: 'finance_manager', label: 'Responsable finance' },
    { value: 'sos_operator', label: 'Opérateur SOS' },
    { value: 'medical_reviewer', label: 'Validateur médical' },
    { value: 'technical_reviewer', label: 'Validateur technique' },
    { value: 'production_agent', label: 'Agent production' },
    { value: 'agent_comptable_mh', label: 'Agent comptable MH' },
    { value: 'agent_comptable_assureur', label: 'Agent comptable assureur' },
    { value: 'agent_comptable_hopital', label: 'Agent comptable hôpital' },
    { value: 'agent_sinistre_mh', label: 'Agent sinistre MH' },
    { value: 'agent_sinistre_assureur', label: 'Agent sinistre assureur' },
    { value: 'agent_reception_hopital', label: "Agent réception hôpital" },
    { value: 'medecin_referent_mh', label: 'Médecin référent MH' },
    { value: 'medecin_hopital', label: 'Médecin hôpital' },
];

const resetPasswordContext = {
    userId: null,
    label: '',
};

function getRoleLabel(roleValue) {
    const match = ROLE_OPTIONS.find(option => option.value === roleValue);
    return match ? match.label : roleValue;
}

function populateRoleSelect(selectElement, selectedValue = 'user') {
    if (!selectElement) {
        return;
    }
    
    selectElement.innerHTML = '';
    ROLE_OPTIONS.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option.value;
        opt.textContent = option.label;
        if (option.value === selectedValue) {
            opt.selected = true;
        }
        selectElement.appendChild(opt);
    });
}

function resetStatusSelect(selectElement, value = 'true') {
    if (selectElement) {
        selectElement.value = value;
    }
}

const ROWS_PER_PAGE = 6;
let currentPageUsers = 0;

// Stocker tous les utilisateurs pour la recherche
let allUsers = [];

// Charger les utilisateurs
async function loadUsers() {
    const container = document.getElementById('usersTableContainer');
    showLoading(container);
    
    try {
        allUsers = await usersAPI.getAll();
        
        if (allUsers.length === 0) {
            container.innerHTML = '<p>Aucun utilisateur trouvé.</p>';
            return;
        }
        
        renderUsersTable(allUsers);
        setupSearchFilter();
    } catch (error) {
        container.innerHTML = `<div class="alert alert-error">Erreur: ${error.message}</div>`;
    }
}

// Rendre le tableau des utilisateurs
function renderUsersTable(users) {
    const container = document.getElementById('usersTableContainer');
    
    if (users.length === 0) {
        container.innerHTML = '<p class="empty-state">Aucun utilisateur ne correspond à votre recherche.</p>';
        return;
    }
    
    const totalPages = Math.max(1, Math.ceil(users.length / ROWS_PER_PAGE));
    currentPageUsers = Math.min(currentPageUsers, totalPages - 1);
    const start = currentPageUsers * ROWS_PER_PAGE;
    const pageData = users.slice(start, start + ROWS_PER_PAGE);
    
    let html = '<div class="table-wrapper" style="overflow-x: scroll !important;"><table class="data-table" style="min-width: 100%;"><thead><tr>';
    html += '<th>Email</th><th>Username</th><th>Rôle</th><th>Statut</th><th>Actions</th>';
    html += '</tr></thead><tbody>';
    
    pageData.forEach(user => {
        const statusClass = user.is_active ? 'status-active' : 'status-inactive';
        const statusText = user.is_active ? 'Actif' : 'Inactif';
        const roleLabel = getRoleLabel(user.role);
        const encodedName = encodeURIComponent(user.full_name || user.email || `Utilisateur #${user.id}`);
        
        html += `
            <tr>
                <td>${user.email}</td>
                <td>${user.username}</td>
                <td>${roleLabel}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td class="table-actions">
                    <select class="action-select" data-user-id="${user.id}" data-user-name="${encodedName}">
                        <option value="">Actions</option>
                        <option value="edit-user">Modifier</option>
                        <option value="reset-password">Réinitialiser</option>
                        <option value="delete-user">Supprimer</option>
                    </select>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    if (users.length > ROWS_PER_PAGE) {
        const end = Math.min(start + ROWS_PER_PAGE, users.length);
        html += `<div class="table-pagination-wrapper"><div class="table-pagination" role="navigation">
            <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${users.length}</span>
            <div class="table-pagination-buttons">
                <button type="button" class="btn btn-outline btn-sm" id="userPrev" ${currentPageUsers <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                <span>Page ${currentPageUsers + 1} / ${totalPages}</span>
                <button type="button" class="btn btn-outline btn-sm" id="userNext" ${currentPageUsers >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
            </div>
        </div></div>`;
    }
    container.innerHTML = html;
    setupUsersTableActions();
    if (users.length > ROWS_PER_PAGE) {
        document.getElementById('userPrev')?.addEventListener('click', () => { currentPageUsers--; renderUsersTable(users); });
        document.getElementById('userNext')?.addEventListener('click', () => { currentPageUsers++; renderUsersTable(users); });
    }
    
    // Forcer l'affichage de la scrollbar après le rendu
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

// Configurer le filtre de recherche
function setupSearchFilter() {
    const searchInput = document.getElementById('userSearchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        
        if (!searchTerm) {
            renderUsersTable(allUsers);
            return;
        }
        
        const filteredUsers = allUsers.filter(user => {
            const email = (user.email || '').toLowerCase();
            const username = (user.username || '').toLowerCase();
            const role = getRoleLabel(user.role).toLowerCase();
            const fullName = (user.full_name || '').toLowerCase();
            
            return email.includes(searchTerm) ||
                   username.includes(searchTerm) ||
                   role.includes(searchTerm) ||
                   fullName.includes(searchTerm);
        });
        
        renderUsersTable(filteredUsers);
    });
}

function setupUsersTableActions() {
    const container = document.getElementById('usersTableContainer');
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
        
        const userId = parseInt(select.dataset.userId, 10);
        if (Number.isNaN(userId)) {
            return;
        }
        
        const encodedName = select.dataset.userName || '';
        const label = encodedName ? decodeURIComponent(encodedName) : `utilisateur #${userId}`;
        
        switch (action) {
            case 'edit-user':
                openEditUserModal(userId);
                break;
            case 'reset-password':
                openResetPasswordModal(userId, label);
                break;
            case 'delete-user':
                confirmDeleteUser(userId, label);
                break;
        }
        
        // Réinitialiser le select
        select.value = '';
    });
}

function openEditModal() {
    const modal = document.getElementById('editUserModal');
    if (!modal) {
        return;
    }
    modal.style.display = 'block';
    modal.setAttribute('aria-hidden', 'false');
}

function closeEditModal() {
    const modal = document.getElementById('editUserModal');
    if (!modal) {
        return;
    }
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
    resetEditForm();
}

function resetEditForm() {
    const form = document.getElementById('editUserForm');
    if (!form) {
        return;
    }
    form.reset();
    populateRoleSelect(document.getElementById('editUserRole'));
    resetStatusSelect(document.getElementById('editUserStatus'));
}

function fillEditForm(user) {
    const idInput = document.getElementById('editUserId');
    const fullNameInput = document.getElementById('editFullName');
    const emailInput = document.getElementById('editEmail');
    const usernameInput = document.getElementById('editUsername');
    const roleSelect = document.getElementById('editUserRole');
    const statusSelect = document.getElementById('editUserStatus');
    
    if (idInput) {
        idInput.value = user.id;
    }
    if (fullNameInput) {
        fullNameInput.value = user.full_name || '';
    }
    if (emailInput) {
        emailInput.value = user.email || '';
    }
    if (usernameInput) {
        usernameInput.value = user.username || '';
    }
    if (roleSelect) {
        populateRoleSelect(roleSelect, user.role);
    }
    if (statusSelect) {
        statusSelect.value = user.is_active ? 'true' : 'false';
    }
}

async function openEditUserModal(userId) {
    const form = document.getElementById('editUserForm');
    if (!form) {
        return;
    }
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.textContent : '';
    
    try {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Chargement...';
        }
        
        const user = await usersAPI.getById(userId);
        fillEditForm(user);
        openEditModal();
    } catch (error) {
        console.error('Erreur lors du chargement du profil utilisateur:', error);
        showAlert(error.message || 'Impossible de charger ce profil utilisateur.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText || 'Enregistrer les modifications';
        }
    }
}

async function confirmDeleteUser(userId, label = '') {
    const displayName = label || `l'utilisateur #${userId}`;
    const confirmed = window.confirm(`Voulez-vous vraiment supprimer ${displayName} ?`);
    if (!confirmed) {
        return;
    }
    
    try {
        await usersAPI.delete(userId);
        showAlert('Utilisateur supprimé avec succès.', 'success');
        await loadUsers();
    } catch (error) {
        console.error('Erreur lors de la suppression utilisateur:', error);
        showAlert(error.message || 'Impossible de supprimer cet utilisateur.', 'error');
    }
}

function setupEditUserForm() {
    const form = document.getElementById('editUserForm');
    const roleSelect = document.getElementById('editUserRole');
    const statusSelect = document.getElementById('editUserStatus');
    const closeBtn = document.getElementById('closeEditModal');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const modal = document.getElementById('editUserModal');
    
    populateRoleSelect(roleSelect);
    resetStatusSelect(statusSelect);
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeEditModal);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (event) => {
            event.preventDefault();
            closeEditModal();
        });
    }
    
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeEditModal();
            }
        });
    }
    
    if (!form) {
        return;
    }
    
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const userId = parseInt(document.getElementById('editUserId')?.value, 10);
        if (!userId) {
            showAlert('Utilisateur introuvable.', 'error');
            return;
        }
        
        const emailInput = document.getElementById('editEmail');
        const fullNameInput = document.getElementById('editFullName');
        
        const email = emailInput?.value?.trim();
        if (!email) {
            showAlert("L'email est obligatoire.", 'error');
            return;
        }
        
        const payload = {
            email,
            full_name: fullNameInput?.value?.trim() || null,
            role: roleSelect?.value || 'user',
            is_active: statusSelect?.value === 'true',
        };
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        
        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Enregistrement...';
            }
            
            await usersAPI.update(userId, payload);
            showAlert('Profil mis à jour avec succès.', 'success');
            closeEditModal();
            await loadUsers();
        } catch (error) {
            console.error('Erreur lors de la mise à jour du profil:', error);
            showAlert(error.message || 'Impossible de mettre à jour ce profil.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText || 'Enregistrer les modifications';
            }
        }
    });
}

function openResetPasswordModal(userId, label) {
    const modal = document.getElementById('resetPasswordModal');
    const labelElement = document.getElementById('resetUserLabel');
    const form = document.getElementById('resetPasswordForm');
    
    if (!modal || !form) {
        return;
    }
    
    resetPasswordContext.userId = userId;
    resetPasswordContext.label = label;
    
    if (labelElement) {
        labelElement.textContent = label;
    }
    
    form.reset();
    modal.style.display = 'block';
    modal.setAttribute('aria-hidden', 'false');
}

function closeResetPasswordModal() {
    const modal = document.getElementById('resetPasswordModal');
    const form = document.getElementById('resetPasswordForm');
    
    if (form) {
        form.reset();
    }
    
    resetPasswordContext.userId = null;
    resetPasswordContext.label = '';
    
    if (modal) {
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }
}

function setupResetPasswordForm() {
    const form = document.getElementById('resetPasswordForm');
    const modal = document.getElementById('resetPasswordModal');
    const closeBtn = document.getElementById('closeResetModal');
    const cancelBtn = document.getElementById('cancelResetBtn');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeResetPasswordModal);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (event) => {
            event.preventDefault();
            closeResetPasswordModal();
        });
    }
    
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeResetPasswordModal();
            }
        });
    }
    
    if (!form) {
        return;
    }
    
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (!resetPasswordContext.userId) {
            showAlert('Utilisateur introuvable pour cette opération.', 'error');
            return;
        }
        
        const newPasswordInput = document.getElementById('newPassword');
        const confirmPasswordInput = document.getElementById('confirmPassword');
        const newPassword = newPasswordInput?.value || '';
        const confirmPassword = confirmPasswordInput?.value || '';
        
        if (newPassword.length < 8) {
            showAlert('Le mot de passe doit contenir au moins 8 caractères.', 'error');
            return;
        }
        
        if (newPassword !== confirmPassword) {
            showAlert('Les deux mots de passe doivent être identiques.', 'error');
            return;
        }
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        
        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Mise à jour...';
            }
            
            await usersAPI.resetPassword(resetPasswordContext.userId, { new_password: newPassword });
            showAlert('Mot de passe réinitialisé avec succès.', 'success');
            closeResetPasswordModal();
        } catch (error) {
            console.error('Erreur lors de la réinitialisation du mot de passe:', error);
            showAlert(error.message || 'Impossible de réinitialiser ce mot de passe.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText || 'Mettre à jour le mot de passe';
            }
        }
    });
}

function setupCreateUserForm() {
    const form = document.getElementById('createUserForm');
    const roleSelect = document.getElementById('userRole');
    const statusSelect = document.getElementById('userStatus');
    if (!form) {
        return;
    }
    
    populateRoleSelect(roleSelect);
    resetStatusSelect(statusSelect);
    
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn ? submitBtn.textContent : '';
        
        const payload = {
            full_name: formData.get('full_name')?.trim() || null,
            email: formData.get('email')?.trim(),
            username: formData.get('username')?.trim(),
            password: formData.get('password') || '',
            role: formData.get('role'),
            is_active: formData.get('is_active') === 'true',
        };
        
        if (!payload.password || payload.password.length < 8) {
            showAlert('Le mot de passe doit contenir au moins 8 caractères.', 'error');
            return;
        }
        
        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Création...';
            }
            
            await usersAPI.create(payload);
            showAlert('Utilisateur créé avec succès.', 'success');
            form.reset();
            populateRoleSelect(roleSelect);
            resetStatusSelect(statusSelect);
            
            await loadUsers();
        } catch (error) {
            console.error('Erreur lors de la création de l’utilisateur:', error);
            showAlert(error.message || 'Impossible de créer l’utilisateur.', 'error');
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalText || 'Créer l’utilisateur';
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupCreateUserForm();
    setupEditUserForm();
    setupResetPasswordForm();
    loadUsers();
    // La recherche sera initialisée après le chargement des utilisateurs
});

