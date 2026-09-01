/**
 * Ajoute une scrollbar en haut des tableaux pour éviter de défiler jusqu'en bas
 */

function initTopScrollbar() {
    const tableWrappers = document.querySelectorAll('.table-wrapper, [id$="TableContainer"], #ledgerWrapper');
    
    tableWrappers.forEach(wrapper => {
        // Vérifier si la scrollbar en haut existe déjà
        if (wrapper.querySelector('.top-scrollbar')) {
            return;
        }
        
        // Créer la scrollbar en haut
        const topScrollbar = document.createElement('div');
        topScrollbar.className = 'top-scrollbar';
        
        // Créer un conteneur pour le contenu de la scrollbar
        const scrollbarContent = document.createElement('div');
        scrollbarContent.style.cssText = `
            height: 1px;
            pointer-events: none;
        `;
        
        // Fonction pour mettre à jour la largeur
        const updateScrollbarWidth = () => {
            const scrollWidth = wrapper.scrollWidth || wrapper.offsetWidth;
            scrollbarContent.style.width = `${scrollWidth}px`;
        };
        
        updateScrollbarWidth();
        topScrollbar.appendChild(scrollbarContent);
        
        // Insérer la scrollbar en haut du wrapper
        if (getComputedStyle(wrapper).position === 'static') {
            wrapper.style.position = 'relative';
        }
        wrapper.insertBefore(topScrollbar, wrapper.firstChild);
        
        // Masquer la scrollbar en bas du wrapper (sauf #ledgerWrapper : on garde les deux)
        const isLedgerWrapper = wrapper.id === 'ledgerWrapper';
        if (!isLedgerWrapper) {
            wrapper.style.scrollbarWidth = 'none';
        }
        const style = wrapper.style;
        if (!wrapper.dataset.originalOverflow) {
            wrapper.dataset.originalOverflow = getComputedStyle(wrapper).overflowX;
        }
        
        wrapper.classList.add('has-top-scrollbar');
        if (isLedgerWrapper) {
            wrapper.classList.add('has-both-scrollbars');
        }
        
        // Synchroniser les scrolls
        let isScrolling = false;
        topScrollbar.addEventListener('scroll', () => {
            if (!isScrolling) {
                isScrolling = true;
                wrapper.scrollLeft = topScrollbar.scrollLeft;
                requestAnimationFrame(() => {
                    isScrolling = false;
                });
            }
        });
        
        wrapper.addEventListener('scroll', () => {
            if (!isScrolling) {
                isScrolling = true;
                topScrollbar.scrollLeft = wrapper.scrollLeft;
                requestAnimationFrame(() => {
                    isScrolling = false;
                });
            }
        });
        
        // Les styles sont déjà dans admin.css, pas besoin de les ajouter ici
        
        // Mettre à jour la largeur du contenu de la scrollbar quand le tableau change
        const observer = new MutationObserver(() => {
            updateScrollbarWidth();
        });
        observer.observe(wrapper, { childList: true, subtree: true, attributes: true });
        
        // Mettre à jour au redimensionnement
        const resizeHandler = () => {
            updateScrollbarWidth();
        };
        window.addEventListener('resize', resizeHandler);
        
        // Observer aussi le tableau pour détecter les changements de largeur
        const table = wrapper.querySelector('.data-table');
        if (table) {
            const tableObserver = new MutationObserver(() => {
                updateScrollbarWidth();
            });
            tableObserver.observe(table, { childList: true, subtree: true, attributes: true });
        }
    });
}

// Exécuter au chargement
document.addEventListener('DOMContentLoaded', () => {
    initTopScrollbar();
    
    // Réexécuter après un délai pour les tableaux chargés dynamiquement
    setTimeout(initTopScrollbar, 500);
    setTimeout(initTopScrollbar, 1500);
});

// Observer les changements dans les conteneurs de tableaux
const tableObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
            setTimeout(initTopScrollbar, 100);
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const containers = document.querySelectorAll('#usersTableContainer, #productsTableContainer, #subscriptionsTableContainer, #hospitalsTableContainer, #ledgerWrapper, .table-wrapper');
    containers.forEach(container => {
        tableObserver.observe(container, { childList: true, subtree: true });
    });
});
