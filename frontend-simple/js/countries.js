// Liste des pays pour les sélections
const COUNTRIES = [
    { code: 'FR', name: 'France' },
    { code: 'BE', name: 'Belgique' },
    { code: 'CH', name: 'Suisse' },
    { code: 'LU', name: 'Luxembourg' },
    { code: 'MC', name: 'Monaco' },
    { code: 'AD', name: 'Andorre' },
    { code: 'CA', name: 'Canada' },
    { code: 'US', name: 'États-Unis' },
    { code: 'GB', name: 'Royaume-Uni' },
    { code: 'DE', name: 'Allemagne' },
    { code: 'ES', name: 'Espagne' },
    { code: 'IT', name: 'Italie' },
    { code: 'PT', name: 'Portugal' },
    { code: 'NL', name: 'Pays-Bas' },
    { code: 'AT', name: 'Autriche' },
    { code: 'SE', name: 'Suède' },
    { code: 'NO', name: 'Norvège' },
    { code: 'DK', name: 'Danemark' },
    { code: 'FI', name: 'Finlande' },
    { code: 'IE', name: 'Irlande' },
    { code: 'PL', name: 'Pologne' },
    { code: 'CZ', name: 'République tchèque' },
    { code: 'GR', name: 'Grèce' },
    { code: 'TR', name: 'Turquie' },
    { code: 'MA', name: 'Maroc' },
    { code: 'TN', name: 'Tunisie' },
    { code: 'DZ', name: 'Algérie' },
    { code: 'SN', name: 'Sénégal' },
    { code: 'CI', name: 'Côte d\'Ivoire' },
    { code: 'CM', name: 'Cameroun' },
    { code: 'CN', name: 'Chine' },
    { code: 'JP', name: 'Japon' },
    { code: 'KR', name: 'Corée du Sud' },
    { code: 'IN', name: 'Inde' },
    { code: 'TH', name: 'Thaïlande' },
    { code: 'VN', name: 'Viêt Nam' },
    { code: 'SG', name: 'Singapour' },
    { code: 'MY', name: 'Malaisie' },
    { code: 'ID', name: 'Indonésie' },
    { code: 'PH', name: 'Philippines' },
    { code: 'AU', name: 'Australie' },
    { code: 'NZ', name: 'Nouvelle-Zélande' },
    { code: 'BR', name: 'Brésil' },
    { code: 'AR', name: 'Argentine' },
    { code: 'MX', name: 'Mexique' },
    { code: 'ZA', name: 'Afrique du Sud' },
    { code: 'EG', name: 'Égypte' },
    { code: 'AE', name: 'Émirats arabes unis' },
    { code: 'SA', name: 'Arabie saoudite' },
    { code: 'IL', name: 'Israël' },
    { code: 'RU', name: 'Russie' },
    { code: 'OTHER', name: 'Autre' }
];

// Fonction pour remplir un select avec les pays
function populateCountrySelect(selectId, includeOther = true) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Garder la première option si elle existe
    const firstOption = select.options[0];
    select.innerHTML = '';
    if (firstOption) {
        select.appendChild(firstOption);
    }
    
    COUNTRIES.forEach(country => {
        if (!includeOther && country.code === 'OTHER') return;
        
        const option = document.createElement('option');
        option.value = country.code;
        option.textContent = country.name;
        select.appendChild(option);
    });
}


















