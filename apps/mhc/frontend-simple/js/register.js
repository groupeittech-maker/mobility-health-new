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
    const paysResidenceDropdown = document.getElementById('pays_residence_dropdown');
    const nationaliteDropdown = document.getElementById('nationalite_dropdown');
    let referenceCountries = typeof COUNTRIES !== 'undefined'
        ? COUNTRIES.map(country => ({ code: country.code, name: country.name }))
        : [];

    function getCountryCode(countryName) {
        if (!countryName) return null;
        const country = referenceCountries.find(c => c.name.toLowerCase() === countryName.toLowerCase());
        return country ? country.code : null;
    }

    function filterCountries(searchTerm) {
        if (!searchTerm || !referenceCountries.length) return [];
        const term = searchTerm.toLowerCase().trim();
        if (term === '') return referenceCountries;
        return referenceCountries.filter(country =>
            country.name.toLowerCase().includes(term)
        );
    }

    async function loadReferenceCountries() {
        try {
            const apiUrl = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
            const response = await fetch(`${apiUrl}/destinations/reference-countries?actif_seulement=true`);
            if (!response.ok) {
                throw new Error(`Erreur HTTP ${response.status}`);
            }
            const payload = await response.json();
            if (Array.isArray(payload) && payload.length > 0) {
                referenceCountries = payload
                    .map((country) => ({
                        code: String(country.code || '').trim().toUpperCase(),
                        name: String(country.nom || '').trim(),
                    }))
                    .filter((country) => country.code && country.name);
            }
        } catch (error) {
            console.warn('Impossible de charger les pays de référence depuis l’API, fallback local utilisé.', error);
        }
    }

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

        filteredCountries.forEach((country) => {
            const option = document.createElement('div');
            option.className = 'country-option';
            option.textContent = country.name;
            option.setAttribute('data-code', country.code);
            option.setAttribute('data-name', country.name);

            option.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                input.value = country.name;
                input.setAttribute('data-country-code', country.code);
                dropdown.classList.remove('show');
                input.blur();
            });

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

        if (window.innerWidth <= 768) {
            setTimeout(() => {
                const dropdownRect = dropdown.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
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

    function setupCountrySearch(input, dropdown) {
        if (!input || !dropdown) return;

        input.addEventListener('input', function() {
            const filtered = filterCountries(this.value);
            showCountryDropdown(this, dropdown, filtered);
        });

        input.addEventListener('focus', function() {
            const filtered = filterCountries(this.value.trim() === '' ? '' : this.value);
            showCountryDropdown(this, dropdown, filtered);
        });

        input.addEventListener('keydown', function(e) {
            handleKeyboardNavigation(this, dropdown, e);
        });

        input.addEventListener('touchstart', function() {
            if (this.value.trim() === '') {
                showCountryDropdown(this, dropdown, filterCountries(''));
            }
        });

        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });

        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(function() {
                dropdown.classList.remove('show');
            }, 100);
        }, true);
    }

    setupCountrySearch(paysResidenceInput, paysResidenceDropdown);
    setupCountrySearch(nationaliteInput, nationaliteDropdown);

    async function initRegistrationPage() {
        await loadReferenceCountries();

        const existingToken = window.MobilityAuth?.getAccessToken
            ? window.MobilityAuth.getAccessToken()
            : localStorage.getItem('access_token');
        if (existingToken) {
            window.location.href = 'index.html';
            return;
        }

        passwordInput.addEventListener('input', function() {
            const strength = checkPasswordStrength(passwordInput.value);
            passwordStrength.textContent = strength.text;
            passwordStrength.className = 'password-strength ' + strength.class;
        });

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

        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const password = passwordInput.value;
            const confirmPassword = passwordConfirmInput.value;
            const email = (form.querySelector('#email')?.value || '').trim();

            if (!email) {
                showAlert('Veuillez saisir votre adresse e-mail', 'error');
                return;
            }

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
            const data = {
                email: email,
                username: email,
                password: password,
                full_name: formData.get('full_name'),
                date_naissance: formData.get('date_naissance') || null,
                telephone: formData.get('phone') || null,
                sexe: formData.get('sexe') || null,
                pays_residence: paysResidenceInput?.getAttribute('data-country-code') || getCountryCode(formData.get('pays_residence')) || null,
                nationalite: nationaliteInput?.getAttribute('data-country-code') || getCountryCode(formData.get('nationalite')) || null,
                contact_urgence: (formData.get('contact_urgence') || '').trim() || null,
            };

            try {
                const apiUrl = window.API_BASE_URL || 'https://api.srv1324425.hstgr.cloud/api/v1';
                const response = await fetch(`${apiUrl}/auth/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                }).catch(error => {
                    console.error('Erreur réseau lors de la requête:', error);
                    throw new Error(`Impossible de se connecter au serveur. Vérifiez que l'API est accessible. Erreur: ${error.message}`);
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: `Erreur HTTP ${response.status}` }));
                    const errorMessage = errorData.detail || `Erreur HTTP ${response.status}`;
                    console.error('Erreur d\'inscription:', errorMessage);
                    throw new Error(errorMessage);
                }

                const user = await response.json();

                console.log('Inscription réussie:', user);
                showAlert(
                    'Inscription enregistrée. Un code de vérification a été envoyé à votre adresse e-mail. Saisissez-le pour activer votre compte et vous connecter.',
                    'success'
                );
                setTimeout(() => {
                    const em = encodeURIComponent(user.email || email);
                    window.location.href = `verify-email.html?email=${em}`;
                }, 2000);

            } catch (error) {
                console.error('Erreur d\'inscription:', error);
                showAlert(`Erreur: ${error.message}`, 'error');
                registerBtn.disabled = false;
                registerBtn.textContent = "S'inscrire";
            }
        });
    }

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
        }
        return { text: 'Fort', class: 'strong' };
    }

    initRegistrationPage();
});
