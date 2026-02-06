// Gestion de l'inscription
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    const registerBtn = document.getElementById('registerBtn');
    const passwordInput = document.getElementById('password');
    const passwordConfirmInput = document.getElementById('password_confirm');
    const passwordStrength = document.getElementById('passwordStrength');
    const passwordMatch = document.getElementById('passwordMatch');
    const paysResidenceInput = document.getElementById('pays_residence');
    const nationaliteInput = document.getElementById('nationalite');
    const validitePasseportInput = document.getElementById('validite_passeport');
    const paysResidenceDropdown = document.getElementById('pays_residence_dropdown');
    const nationaliteDropdown = document.getElementById('nationalite_dropdown');

    if (validitePasseportInput) {
        validitePasseportInput.min = new Date().toISOString().split('T')[0];
    }

    // Fonction pour convertir le nom du pays en code lors de la soumission
    function getCountryCode(countryName) {
        if (!countryName || typeof COUNTRIES === 'undefined') return null;
        const country = COUNTRIES.find(c => c.name.toLowerCase() === countryName.toLowerCase());
        return country ? country.code : null;
    }

    // Fonction pour filtrer les pays selon la recherche
    function filterCountries(searchTerm) {
        if (!searchTerm || typeof COUNTRIES === 'undefined') return [];
        const term = searchTerm.toLowerCase().trim();
        if (term === '') return COUNTRIES;
        return COUNTRIES.filter(country => 
            country.name.toLowerCase().includes(term)
        );
    }

    // Fonction pour afficher les résultats dans le dropdown
    function showCountryDropdown(input, dropdown, filteredCountries) {
        dropdown.innerHTML = '';
        
        if (filteredCountries.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'country-option no-results';
            noResults.textContent = 'Aucun pays trouvé';
            dropdown.appendChild(noResults);
            dropdown.classList.add('show');
            return;
        }

        filteredCountries.forEach((country, index) => {
            const option = document.createElement('div');
            option.className = 'country-option';
            option.textContent = country.name;
            option.setAttribute('data-code', country.code);
            option.setAttribute('data-name', country.name);
            
            // Gestion du clic et du touch pour mobile
            option.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                input.value = country.name;
                input.setAttribute('data-country-code', country.code);
                dropdown.classList.remove('show');
                input.blur();
            });
            
            // Gestion tactile pour mobile
            option.addEventListener('touchend', function(e) {
                e.preventDefault();
                e.stopPropagation();
                input.value = country.name;
                input.setAttribute('data-country-code', country.code);
                dropdown.classList.remove('show');
                input.blur();
            });
            
            dropdown.appendChild(option);
        });
        
        dropdown.classList.add('show');
        
        // Sur mobile, s'assurer que le dropdown est visible
        if (window.innerWidth <= 768) {
            setTimeout(() => {
                const rect = input.getBoundingClientRect();
                const dropdownRect = dropdown.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
                
                // Si le dropdown dépasse de l'écran, le positionner au-dessus
                if (dropdownRect.bottom > viewportHeight) {
                    dropdown.style.top = 'auto';
                    dropdown.style.bottom = '100%';
                    dropdown.style.marginTop = '0';
                    dropdown.style.marginBottom = '4px';
                } else {
                    dropdown.style.top = '100%';
                    dropdown.style.bottom = 'auto';
                    dropdown.style.marginTop = '4px';
                    dropdown.style.marginBottom = '0';
                }
            }, 10);
        }
    }

    // Fonction pour gérer la navigation au clavier dans le dropdown
    function handleKeyboardNavigation(input, dropdown, event) {
        const options = dropdown.querySelectorAll('.country-option:not(.no-results)');
        const highlighted = dropdown.querySelector('.country-option.highlighted');
        let currentIndex = highlighted ? Array.from(options).indexOf(highlighted) : -1;

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            currentIndex = (currentIndex + 1) % options.length;
            options.forEach(opt => opt.classList.remove('highlighted'));
            options[currentIndex].classList.add('highlighted');
            options[currentIndex].scrollIntoView({ block: 'nearest' });
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            currentIndex = currentIndex <= 0 ? options.length - 1 : currentIndex - 1;
            options.forEach(opt => opt.classList.remove('highlighted'));
            options[currentIndex].classList.add('highlighted');
            options[currentIndex].scrollIntoView({ block: 'nearest' });
        } else if (event.key === 'Enter' && highlighted) {
            event.preventDefault();
            highlighted.click();
        } else if (event.key === 'Escape') {
            dropdown.classList.remove('show');
            input.blur();
        }
    }

    // Configuration de la recherche pour le pays de résidence
    if (paysResidenceInput && paysResidenceDropdown) {
        let currentHighlightIndex = -1;

        paysResidenceInput.addEventListener('input', function() {
            const searchTerm = this.value;
            const filtered = filterCountries(searchTerm);
            showCountryDropdown(this, paysResidenceDropdown, filtered);
            currentHighlightIndex = -1;
        });

        paysResidenceInput.addEventListener('focus', function() {
            if (this.value.trim() === '') {
                const filtered = filterCountries('');
                showCountryDropdown(this, paysResidenceDropdown, filtered);
            } else {
                const filtered = filterCountries(this.value);
                showCountryDropdown(this, paysResidenceDropdown, filtered);
            }
        });

        paysResidenceInput.addEventListener('keydown', function(e) {
            handleKeyboardNavigation(this, paysResidenceDropdown, e);
        });

        // Gestion tactile pour mobile
        paysResidenceInput.addEventListener('touchstart', function() {
            if (this.value.trim() === '') {
                const filtered = filterCountries('');
                showCountryDropdown(this, paysResidenceDropdown, filtered);
            }
        });

        // Fermer le dropdown quand on clique ailleurs
        document.addEventListener('click', function(e) {
            if (!paysResidenceInput.contains(e.target) && !paysResidenceDropdown.contains(e.target)) {
                paysResidenceDropdown.classList.remove('show');
            }
        });

        // Fermer le dropdown au scroll sur mobile
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(function() {
                paysResidenceDropdown.classList.remove('show');
            }, 100);
        }, true);
    }

    // Configuration de la recherche pour la nationalité
    if (nationaliteInput && nationaliteDropdown) {
        let currentHighlightIndex = -1;

        nationaliteInput.addEventListener('input', function() {
            const searchTerm = this.value;
            const filtered = filterCountries(searchTerm);
            showCountryDropdown(this, nationaliteDropdown, filtered);
            currentHighlightIndex = -1;
        });

        nationaliteInput.addEventListener('focus', function() {
            if (this.value.trim() === '') {
                const filtered = filterCountries('');
                showCountryDropdown(this, nationaliteDropdown, filtered);
            } else {
                const filtered = filterCountries(this.value);
                showCountryDropdown(this, nationaliteDropdown, filtered);
            }
        });

        nationaliteInput.addEventListener('keydown', function(e) {
            handleKeyboardNavigation(this, nationaliteDropdown, e);
        });

        // Gestion tactile pour mobile
        nationaliteInput.addEventListener('touchstart', function() {
            if (this.value.trim() === '') {
                const filtered = filterCountries('');
                showCountryDropdown(this, nationaliteDropdown, filtered);
            }
        });

        // Fermer le dropdown quand on clique ailleurs
        document.addEventListener('click', function(e) {
            if (!nationaliteInput.contains(e.target) && !nationaliteDropdown.contains(e.target)) {
                nationaliteDropdown.classList.remove('show');
            }
        });

        // Fermer le dropdown au scroll sur mobile
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(function() {
                nationaliteDropdown.classList.remove('show');
            }, 100);
        }, true);
    }
    
    // Affichage conditionnel des champs "Si oui, précisez"
    function bindYesNoToggle(radioName, detailId) {
        const radios = form.querySelectorAll(`input[name="${radioName}"]`);
        const detail = document.getElementById(detailId);
        if (!detail) return;
        function update() {
            const checked = form.querySelector(`input[name="${radioName}"]:checked`);
            detail.classList.toggle('show', checked && checked.value === 'oui');
        }
        radios.forEach(r => r.addEventListener('change', update));
        update();
    }
    bindYesNoToggle('traitement_regulier', 'traitement_regulier_detail');
    bindYesNoToggle('hospitalise_12_mois', 'hospitalise_12_mois_detail');
    bindYesNoToggle('fumeur', 'fumeur_detail');
    bindYesNoToggle('alcool', 'alcool_detail');
    bindYesNoToggle('activite_physique', 'activite_physique_detail');
    bindYesNoToggle('allergies', 'allergies_detail');
    bindYesNoToggle('sante_mentale', 'sante_mentale_detail');

    // Vérifier si déjà connecté
    const existingToken = window.MobilityAuth?.getAccessToken
        ? window.MobilityAuth.getAccessToken()
        : localStorage.getItem('access_token');
    if (existingToken) {
        // Rediriger vers le dashboard approprié
        window.location.href = 'index.html';
        return;
    }
    
    // Vérification de la force du mot de passe
    passwordInput.addEventListener('input', function() {
        const password = passwordInput.value;
        const strength = checkPasswordStrength(password);
        passwordStrength.textContent = strength.text;
        passwordStrength.className = 'password-strength ' + strength.class;
    });
    
    // Vérification de la correspondance des mots de passe
    passwordConfirmInput.addEventListener('input', function() {
        const password = passwordInput.value;
        const confirmPassword = passwordConfirmInput.value;
        
        if (confirmPassword.length === 0) {
            passwordMatch.textContent = '';
            return;
        }
        
        if (password === confirmPassword) {
            passwordMatch.textContent = '✓ Les mots de passe correspondent';
            passwordMatch.style.color = 'var(--success-color)';
        } else {
            passwordMatch.textContent = '✗ Les mots de passe ne correspondent pas';
            passwordMatch.style.color = 'var(--danger-color)';
        }
    });
    
    // Fonction pour vérifier la force du mot de passe
    function checkPasswordStrength(password) {
        if (password.length === 0) {
            return { text: '', class: '' };
        }
        
        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^A-Za-z0-9]/.test(password)) strength++;
        
        if (strength <= 2) {
            return { text: 'Faible', class: 'weak' };
        } else if (strength <= 4) {
            return { text: 'Moyen', class: 'medium' };
        } else {
            return { text: 'Fort', class: 'strong' };
        }
    }
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validation côté client
        const password = passwordInput.value;
        const confirmPassword = passwordConfirmInput.value;
        
        if (password !== confirmPassword) {
            showAlert('Les mots de passe ne correspondent pas', 'error');
            return;
        }
        
        if (password.length < 8) {
            showAlert('Le mot de passe doit contenir au moins 8 caractères', 'error');
            return;
        }
        
        registerBtn.disabled = true;
        registerBtn.textContent = 'Inscription en cours...';
        
        const formData = new FormData(form);
        const maladiesChecked = Array.from(form.querySelectorAll('input[name="maladie"]:checked')).map(el => el.value);
        const maladiesAutre = (formData.get('maladies_chroniques_autre') || '').trim();
        const maladies_chroniques = maladiesChecked.length || maladiesAutre
            ? [...maladiesChecked, maladiesAutre ? 'Autre: ' + maladiesAutre : ''].filter(Boolean).join(', ')
            : null;

        // Traitement médical régulier -> traitements_en_cours
        const traitementRegulier = form.querySelector('input[name="traitement_regulier"]:checked')?.value;
        const traitementPrecision = (formData.get('traitement_regulier_precision') || '').trim();
        const traitements_en_cours = traitementRegulier === 'oui'
            ? 'Traitement médical régulier: Oui. ' + (traitementPrecision ? 'Type: ' + traitementPrecision : '')
            : traitementRegulier === 'non'
                ? 'Traitement médical régulier: Non'
                : null;

        // Hospitalisation 12 mois + mode de vie + allergies + santé mentale -> antecedents_recents
        const parts = [];
        const hosp12 = form.querySelector('input[name="hospitalise_12_mois"]:checked')?.value;
        const hospRaison = (formData.get('hospitalise_12_mois_raison') || '').trim();
        if (hosp12 === 'oui') parts.push('Hospitalisation (12 derniers mois): Oui. Raison: ' + (hospRaison || '—'));
        else if (hosp12 === 'non') parts.push('Hospitalisation (12 derniers mois): Non');

        const fumeur = form.querySelector('input[name="fumeur"]:checked')?.value;
        const fumeurCig = (formData.get('fumeur_cigarettes') || '').trim();
        if (fumeur === 'oui') parts.push('Fumeur: Oui' + (fumeurCig ? ' (' + fumeurCig + ' cigarettes/jour)' : ''));
        else if (fumeur === 'non') parts.push('Fumeur: Non');

        const alcool = form.querySelector('input[name="alcool"]:checked')?.value;
        const alcoolFreq = formData.get('alcool_frequence') || '';
        if (alcool === 'oui') parts.push('Alcool: Oui. Fréquence: ' + (alcoolFreq ? { occasionnellement: 'Occasionnellement', regulierement: 'Régulièrement (1 à 2 fois/semaine)', quotidiennement: 'Quotidiennement' }[alcoolFreq] || alcoolFreq : '—'));
        else if (alcool === 'non') parts.push('Alcool: Non');

        const activite = form.querySelector('input[name="activite_physique"]:checked')?.value;
        const activitePrecision = (formData.get('activite_physique_precision') || '').trim();
        if (activite === 'oui') parts.push('Activité physique régulière: Oui. ' + (activitePrecision ? activitePrecision : ''));
        else if (activite === 'non') parts.push('Activité physique régulière: Non');

        const allergies = form.querySelector('input[name="allergies"]:checked')?.value;
        const allergiesPrecision = (formData.get('allergies_precision') || '').trim();
        if (allergies === 'oui') parts.push('Allergies: Oui. ' + (allergiesPrecision || '—'));
        else if (allergies === 'non') parts.push('Allergies: Non');

        const santeMentale = form.querySelector('input[name="sante_mentale"]:checked')?.value;
        const santeMentalePrecision = (formData.get('sante_mentale_precision') || '').trim();
        if (santeMentale === 'oui') parts.push('Santé mentale (trouble diagnostiqué): Oui. ' + (santeMentalePrecision || '—'));
        else if (santeMentale === 'non') parts.push('Santé mentale (trouble diagnostiqué): Non');

        const antecedents_recents = parts.length ? parts.join('\n') : null;

        const data = {
            email: formData.get('email'),
            username: formData.get('username'),
            password: formData.get('password'),
            full_name: formData.get('full_name'),
            date_naissance: formData.get('date_naissance') || null,
            telephone: formData.get('phone') || null,
            sexe: formData.get('sexe') || null,
            pays_residence: paysResidenceInput?.getAttribute('data-country-code') || getCountryCode(formData.get('pays_residence')) || null,
            nationalite: nationaliteInput?.getAttribute('data-country-code') || getCountryCode(formData.get('nationalite')) || null,
            numero_passeport: (formData.get('numero_passeport') || '').trim() || null,
            validite_passeport: formData.get('validite_passeport') || null,
            contact_urgence: (formData.get('contact_urgence') || '').trim() || null,
            maladies_chroniques: maladies_chroniques || null,
            traitements_en_cours: traitements_en_cours || null,
            antecedents_recents: antecedents_recents || null
        };
        
        try {
<<<<<<< HEAD
            const apiUrl = window.API_BASE_URL || 'https://srv1324425.hstgr.cloud/api/v1';
=======
            const apiUrl = window.API_BASE_URL || 'https://mobility-health.ittechmed.com/api/v1';
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            const response = await fetch(`${apiUrl}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            }).catch(error => {
                console.error('Erreur réseau lors de la requête:', error);
<<<<<<< HEAD
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible sur https://srv1324425.hstgr.cloud. Erreur: ${error.message}`);
=======
                throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible sur https://mobility-health.ittechmed.com. Erreur: ${error.message}`);
>>>>>>> 7bf45370c0f1ce1cc4906e70652fe5d774263241
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
                const errorMessage = errorData.detail || `Erreur HTTP ${response.status}`;
                console.error('Erreur d\'inscription:', errorMessage);
                throw new Error(errorMessage);
            }
            
            const user = await response.json();
            
            console.log('Inscription réussie:', user);
            showAlert(`Inscription enregistrée. Votre compte est en cours de validation par le médecin MH. Vous pourrez vous connecter une fois validé.`, 'success');
            
            // Pas de validation par email pour l'instant : redirection vers la page de connexion
            setTimeout(() => {
                window.location.href = 'login.html?inscription_pending=1';
            }, 2000);
            
        } catch (error) {
            console.error('Erreur d\'inscription:', error);
            showAlert(`Erreur: ${error.message}`, 'error');
            registerBtn.disabled = false;
            registerBtn.textContent = "S'inscrire";
        }
    });
});




