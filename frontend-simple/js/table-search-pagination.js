/**
 * Système générique de recherche et pagination pour les tableaux
 * Utilisation:
 *   const tableManager = new TableSearchPagination('tableContainerId', {
 *     searchPlaceholder: 'Rechercher...',
 *     pageSize: 10,
 *     searchFields: ['nom', 'email'] // Champs à rechercher
 *   });
 *   tableManager.setData(dataArray);
 */

class TableSearchPagination {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`Container ${containerId} not found`);
            return;
        }

        this.options = {
            searchPlaceholder: options.searchPlaceholder || 'Rechercher...',
            pageSize: options.pageSize || 10,
            searchFields: options.searchFields || [],
            searchDebounce: options.searchDebounce || 300,
            emptyMessage: options.emptyMessage || 'Aucun résultat trouvé.',
            ...options
        };

        this.allData = [];
        this.filteredData = [];
        this.currentPage = 0;
        this.searchTerm = '';

        this.init();
    }

    init() {
        // Créer les éléments de recherche et pagination
        this.createSearchBar();
        this.createPagination();
        
        // Trouver le tbody dans le conteneur
        this.tbody = this.container.querySelector('tbody');
        if (!this.tbody) {
            // Si pas de tbody, chercher une table dans le conteneur
            const table = this.container.querySelector('table');
            if (table) {
                this.tbody = table.querySelector('tbody');
            }
        }
    }

    createSearchBar() {
        // Vérifier si une barre de recherche existe déjà
        let searchBar = this.container.querySelector('.table-search-bar');
        if (searchBar) {
            this.searchInput = searchBar.querySelector('input');
            return;
        }

        // Créer la barre de recherche
        searchBar = document.createElement('div');
        searchBar.className = 'table-search-bar';
        searchBar.innerHTML = `
            <div class="table-search-wrapper">
                <input 
                    type="text" 
                    class="table-search-input" 
                    placeholder="${this.options.searchPlaceholder}"
                    aria-label="Rechercher dans le tableau"
                />
                <span class="table-search-icon">🔍</span>
            </div>
        `;

        // Insérer avant le tableau ou au début du conteneur
        const table = this.container.querySelector('table');
        const tableWrapper = this.container.querySelector('.table-wrapper');
        
        if (tableWrapper && tableWrapper.parentNode === this.container) {
            // Si le tableau est dans un wrapper qui est un enfant direct, insérer avant le wrapper
            this.container.insertBefore(searchBar, tableWrapper);
        } else if (table && table.parentNode === this.container) {
            // Si le tableau est un enfant direct, insérer avant le tableau
            this.container.insertBefore(searchBar, table);
        } else if (this.container.firstChild) {
            // Sinon, insérer au début
            this.container.insertBefore(searchBar, this.container.firstChild);
        } else {
            // Si le conteneur est vide, ajouter simplement
            this.container.appendChild(searchBar);
        }

        this.searchInput = searchBar.querySelector('input');
        
        // Ajouter l'événement de recherche avec debounce
        let searchTimeout;
        this.searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.search(e.target.value);
            }, this.options.searchDebounce);
        });
    }

    createPagination() {
        // Vérifier si la pagination existe déjà
        let pagination = this.container.querySelector('.table-pagination');
        if (pagination) {
            this.paginationEl = pagination;
            this.updatePaginationButtons();
            return;
        }

        // Créer la pagination
        pagination = document.createElement('div');
        pagination.className = 'table-pagination';
        pagination.innerHTML = `
            <div class="table-pagination-info">
                <span class="table-pagination-text">Affichage de <span class="table-pagination-range">0-0</span> sur <span class="table-pagination-total">0</span> résultats</span>
            </div>
            <div class="table-pagination-controls">
                <button class="table-pagination-btn table-pagination-prev" aria-label="Page précédente" disabled>
                    ◀ Précédent
                </button>
                <span class="table-pagination-pages">
                    <span class="table-pagination-current">1</span> / <span class="table-pagination-total-pages">1</span>
                </span>
                <button class="table-pagination-btn table-pagination-next" aria-label="Page suivante" disabled>
                    Suivant ▶
                </button>
            </div>
        `;

        // Ajouter après le tableau ou le wrapper
        const tableWrapper = this.container.querySelector('.table-wrapper');
        const table = this.container.querySelector('table');
        
        if (tableWrapper && tableWrapper.parentNode === this.container) {
            // Si le wrapper est un enfant direct, ajouter après le wrapper
            if (tableWrapper.nextSibling) {
                this.container.insertBefore(pagination, tableWrapper.nextSibling);
            } else {
                this.container.appendChild(pagination);
            }
        } else if (table && table.parentNode === this.container) {
            // Si le tableau est un enfant direct, ajouter après le tableau
            if (table.nextSibling) {
                this.container.insertBefore(pagination, table.nextSibling);
            } else {
                this.container.appendChild(pagination);
            }
        } else if (table && table.parentNode) {
            // Si le tableau a un parent, ajouter après le parent
            if (table.nextSibling) {
                table.parentNode.insertBefore(pagination, table.nextSibling);
            } else {
                table.parentNode.appendChild(pagination);
            }
        } else {
            // Sinon, ajouter à la fin du conteneur
            this.container.appendChild(pagination);
        }

        this.paginationEl = pagination;

        // Ajouter les événements
        const prevBtn = pagination.querySelector('.table-pagination-prev');
        const nextBtn = pagination.querySelector('.table-pagination-next');

        prevBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        nextBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
    }

    setData(data) {
        this.allData = Array.isArray(data) ? data : [];
        this.filteredData = [...this.allData];
        this.currentPage = 0;
        this.render();
    }

    search(term) {
        this.searchTerm = term.toLowerCase().trim();
        this.currentPage = 0;

        if (!this.searchTerm) {
            this.filteredData = [...this.allData];
        } else {
            this.filteredData = this.allData.filter(item => {
                // Si des champs spécifiques sont définis, chercher uniquement dans ces champs
                if (this.options.searchFields.length > 0) {
                    return this.options.searchFields.some(field => {
                        const value = this.getNestedValue(item, field);
                        return value && value.toString().toLowerCase().includes(this.searchTerm);
                    });
                }
                
                // Sinon, chercher dans tous les champs de l'objet
                return Object.values(item).some(value => {
                    if (value === null || value === undefined) return false;
                    return value.toString().toLowerCase().includes(this.searchTerm);
                });
            });
        }

        this.render();
    }

    getNestedValue(obj, path) {
        return path.split('.').reduce((current, prop) => current?.[prop], obj);
    }

    goToPage(page) {
        const totalPages = Math.ceil(this.filteredData.length / this.options.pageSize);
        this.currentPage = Math.max(0, Math.min(totalPages - 1, page));
        this.render();
    }

    render() {
        if (!this.tbody) {
            console.warn('No tbody found for rendering');
            return;
        }

        const totalPages = Math.max(1, Math.ceil(this.filteredData.length / this.options.pageSize));
        const start = this.currentPage * this.options.pageSize;
        const end = Math.min(start + this.options.pageSize, this.filteredData.length);
        const pageData = this.filteredData.slice(start, end);

        // Si on a une fonction de rendu personnalisée, l'utiliser
        if (this.options.renderRow) {
            this.tbody.innerHTML = pageData.map(item => this.options.renderRow(item)).join('');
        } else {
            // Sinon, essayer de trouver les lignes existantes et les filtrer
            const allRows = Array.from(this.tbody.querySelectorAll('tr'));
            if (allRows.length > 0) {
                // Si on a des lignes, on doit les filtrer selon les données
                // Cette approche nécessite que les lignes aient des data-attributes
                const visibleRows = allRows.filter((row, index) => {
                    const dataIndex = start + index;
                    return dataIndex < end;
                });
                this.tbody.innerHTML = '';
                visibleRows.forEach(row => this.tbody.appendChild(row));
            }
        }

        // Mettre à jour la pagination
        this.updatePagination();
    }

    updatePagination() {
        if (!this.paginationEl) return;

        const total = this.filteredData.length;
        const totalPages = Math.max(1, Math.ceil(total / this.options.pageSize));
        const start = this.currentPage * this.options.pageSize;
        const end = Math.min(start + this.options.pageSize, total);

        // Mettre à jour les informations
        const rangeEl = this.paginationEl.querySelector('.table-pagination-range');
        const totalEl = this.paginationEl.querySelector('.table-pagination-total');
        const currentEl = this.paginationEl.querySelector('.table-pagination-current');
        const totalPagesEl = this.paginationEl.querySelector('.table-pagination-total-pages');

        if (rangeEl) rangeEl.textContent = total > 0 ? `${start + 1}-${end}` : '0-0';
        if (totalEl) totalEl.textContent = total;
        if (currentEl) currentEl.textContent = this.currentPage + 1;
        if (totalPagesEl) totalPagesEl.textContent = totalPages;

        // Mettre à jour les boutons
        this.updatePaginationButtons();

        // Afficher/masquer le message vide
        this.updateEmptyState();
    }

    updatePaginationButtons() {
        if (!this.paginationEl) return;

        const totalPages = Math.max(1, Math.ceil(this.filteredData.length / this.options.pageSize));
        const prevBtn = this.paginationEl.querySelector('.table-pagination-prev');
        const nextBtn = this.paginationEl.querySelector('.table-pagination-next');

        if (prevBtn) {
            prevBtn.disabled = this.currentPage === 0;
        }
        if (nextBtn) {
            nextBtn.disabled = this.currentPage >= totalPages - 1;
        }
    }

    updateEmptyState() {
        const table = this.container.querySelector('table');
        const tableWrapper = this.container.querySelector('.table-wrapper');
        const emptyState = this.container.querySelector('.table-empty-state');
        
        if (this.filteredData.length === 0) {
            if (!emptyState) {
                const emptyEl = document.createElement('div');
                emptyEl.className = 'table-empty-state';
                emptyEl.innerHTML = `
                    <div class="empty-state-icon">📭</div>
                    <p>${this.searchTerm ? 'Aucun résultat ne correspond à votre recherche.' : this.options.emptyMessage}</p>
                `;
                // Insérer après le wrapper ou le tableau
                if (tableWrapper && tableWrapper.parentNode === this.container) {
                    this.container.insertBefore(emptyEl, tableWrapper.nextSibling);
                } else if (table && table.parentNode === this.container) {
                    this.container.insertBefore(emptyEl, table.nextSibling);
                } else if (table && table.parentNode) {
                    table.parentNode.insertBefore(emptyEl, table.nextSibling);
                } else {
                    this.container.appendChild(emptyEl);
                }
            }
            if (table) table.style.display = 'none';
        } else {
            if (emptyState) emptyState.remove();
            if (table) table.style.display = '';
        }
    }

    // Méthode pour mettre à jour les données sans réinitialiser
    updateData(newData) {
        this.allData = Array.isArray(newData) ? newData : [];
        // Réappliquer la recherche actuelle
        this.search(this.searchTerm);
    }

    // Méthode pour réinitialiser la recherche
    reset() {
        this.searchInput.value = '';
        this.search('');
    }
}

// Exporter pour utilisation globale
window.TableSearchPagination = TableSearchPagination;

