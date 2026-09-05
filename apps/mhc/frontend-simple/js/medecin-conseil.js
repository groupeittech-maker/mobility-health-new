const MEDECIN_CONSEIL_CACHE_KEY = 'mhc_medecin_conseil_assignments_v1';

function escapeMedecinConseilHtml(value) {
    if (value === null || value === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(value);
    return div.innerHTML;
}

function readMedecinConseilCache() {
    try {
        const raw = localStorage.getItem(MEDECIN_CONSEIL_CACHE_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed : [];
    } catch (_) {
        return [];
    }
}

function writeMedecinConseilCache(items) {
    try {
        localStorage.setItem(MEDECIN_CONSEIL_CACHE_KEY, JSON.stringify(items || []));
    } catch (_) {
        // Quota ou navigation privée : l'affichage en ligne reste disponible.
    }
}

async function fetchMedecinConseilAssignments(souscriptionId) {
    const query = souscriptionId ? `?souscription_id=${encodeURIComponent(souscriptionId)}` : '';
    const items = await apiCall(`/sos/medecin-conseil${query}`);
    const list = Array.isArray(items) ? items : [];
    if (!souscriptionId) {
        writeMedecinConseilCache(list);
    }
    return list;
}

async function loadMedecinConseilAssignments({ souscriptionId = null, preferCache = true } = {}) {
    const cached = readMedecinConseilCache();
    const cachedForContext = souscriptionId
        ? cached.filter((item) => String(item.souscription_id) === String(souscriptionId))
        : cached;
    try {
        const fresh = await fetchMedecinConseilAssignments(souscriptionId);
        return { items: fresh, fromCache: false };
    } catch (_) {
        return { items: preferCache ? cachedForContext : [], fromCache: cachedForContext.length > 0 };
    }
}

function renderMedecinConseilCard(assignment) {
    const contact = assignment?.medecin_conseil || null;
    const destination = assignment?.destination || assignment?.destination_country_name || 'Destination non renseignée';
    const nom = contact?.nom || 'Médecin-conseil non renseigné';
    const telephone = contact?.telephone || '';
    const email = contact?.email || '';
    const phoneHtml = telephone
        ? `<a class="medecin-conseil-link" href="tel:${encodeURIComponent(telephone)}">${escapeMedecinConseilHtml(telephone)}</a>`
        : '';
    const emailHtml = email
        ? `<a class="medecin-conseil-link" href="mailto:${encodeURIComponent(email)}">${escapeMedecinConseilHtml(email)}</a>`
        : '';
    const contactsHtml = (phoneHtml || emailHtml)
        ? `<div class="medecin-conseil-contacts">${phoneHtml}${emailHtml}</div>`
        : '<p class="muted">Aucun contact n’est encore associé à cette destination.</p>';

    return `
        <article class="medecin-conseil-card">
            <div class="medecin-conseil-card__title">${escapeMedecinConseilHtml(nom)}</div>
            <div class="medecin-conseil-card__destination">${escapeMedecinConseilHtml(destination)}</div>
            ${contactsHtml}
        </article>
    `;
}

function renderMedecinConseilSection(items, { fromCache = false, emptyMessage = null } = {}) {
    const hint = fromCache
        ? 'Disponible hors ligne — coordonnées de la destination choisie à la souscription.'
        : 'Coordonnées du médecin-conseil associé à votre destination de voyage.';
    if (!items || items.length === 0) {
        return `
            <section class="medecin-conseil-section">
                <h3>Médecin-conseil</h3>
                <p class="muted">${escapeMedecinConseilHtml(emptyMessage || 'Aucun médecin-conseil n’est encore associé à une destination de vos souscriptions.')}</p>
            </section>
        `;
    }
    return `
        <section class="medecin-conseil-section">
            <h3>Médecin-conseil</h3>
            <p class="muted">${escapeMedecinConseilHtml(hint)}</p>
            ${items.map(renderMedecinConseilCard).join('')}
        </section>
    `;
}
