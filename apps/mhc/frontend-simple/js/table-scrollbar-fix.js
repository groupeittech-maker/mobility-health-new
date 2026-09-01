/**
 * Force l'affichage de la scrollbar horizontale sur tous les tableaux
 * pour qu'elle soit visible dès l'ouverture de la page
 */

function forceTableScrollbar() {
    // Trouver tous les conteneurs de tableaux
    const tableWrappers = document.querySelectorAll('.table-wrapper, [id$="TableContainer"]');
    
    tableWrappers.forEach(wrapper => {
        // Forcer overflow-x: scroll avec !important via style inline
        wrapper.style.setProperty('overflow-x', 'scroll', 'important');
        wrapper.style.setProperty('overflow-y', 'visible', 'important');
        
        // S'assurer que le wrapper a une position relative
        if (getComputedStyle(wrapper).position === 'static') {
            wrapper.style.position = 'relative';
        }
        
        // Forcer le recalcul de la scrollbar
        const scrollWidth = wrapper.scrollWidth;
        const clientWidth = wrapper.clientWidth;
        
        // Toujours forcer un dépassement minimal pour garantir la scrollbar
        const table = wrapper.querySelector('.data-table');
        if (table) {
            // Forcer une largeur minimale qui dépasse toujours le conteneur
            const wrapperWidth = wrapper.clientWidth || wrapper.offsetWidth;
            
            // Toujours forcer un dépassement de 2px minimum
            const currentTableWidth = table.offsetWidth || table.scrollWidth;
            const minRequiredWidth = wrapperWidth + 2;
            
            if (currentTableWidth < minRequiredWidth) {
                table.style.minWidth = `${minRequiredWidth}px`;
                table.style.width = `${minRequiredWidth}px`;
            }
            
            // Ajouter un padding invisible à droite pour garantir le dépassement
            table.style.paddingRight = '2px';
            
            // Forcer le recalcul
            void wrapper.offsetHeight;
        }
        
        // Forcer l'affichage de la scrollbar en ajoutant un élément invisible
        let scrollbarForcer = wrapper.querySelector('.scrollbar-forcer');
        if (!scrollbarForcer) {
            scrollbarForcer = document.createElement('div');
            scrollbarForcer.className = 'scrollbar-forcer';
            scrollbarForcer.style.cssText = `
                position: absolute;
                bottom: 0;
                left: 0;
                width: calc(100% + 1px);
                height: 1px;
                pointer-events: none;
                opacity: 0;
                z-index: -1;
            `;
            wrapper.appendChild(scrollbarForcer);
        }
    });
}

// Exécuter au chargement de la page
document.addEventListener('DOMContentLoaded', forceTableScrollbar);

// Exécuter après chaque chargement de tableau (MutationObserver)
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.addedNodes.length > 0) {
            // Attendre un peu pour que le DOM soit complètement rendu
            setTimeout(forceTableScrollbar, 100);
        }
    });
});

// Observer les changements dans les conteneurs de tableaux
document.addEventListener('DOMContentLoaded', () => {
    const containers = document.querySelectorAll('#usersTableContainer, #productsTableContainer, #subscriptionsTableContainer, #hospitalsTableContainer');
    containers.forEach(container => {
        observer.observe(container, { childList: true, subtree: true });
    });
    
    // Exécuter immédiatement
    forceTableScrollbar();
    
    // Réexécuter après un court délai pour s'assurer que tout est chargé
    setTimeout(forceTableScrollbar, 500);
});

// Réexécuter lors du redimensionnement de la fenêtre
window.addEventListener('resize', () => {
    setTimeout(forceTableScrollbar, 100);
});
