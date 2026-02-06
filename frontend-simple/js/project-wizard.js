document.addEventListener('DOMContentLoaded', async () => {
    const authenticated = await requireAuth();
    if (!authenticated) {
        return;
    }

    const form = document.getElementById('projectForm');
    const submitBtn = document.getElementById('submitBtn');
    const messageBox = document.getElementById('formMessage');
    const destinationSelect = document.getElementById('destinationCountry');
    const destinationCitySelect = document.getElementById('destinationCity');
    const dateDepartInput = document.getElementById('dateDepart');
    const dateRetourInput = document.getElementById('dateRetour');
    const durationDisplay = document.getElementById('durationDisplay');

    const documentInputs = document.querySelectorAll('[data-doc-type]');
    const MAX_DOCUMENT_SIZE = 10 * 1024 * 1024; // 10 Mo

    const userName = localStorage.getItem('user_name');
    if (userName) {
        document.title = `${userName} - Nouvelle souscription`;
    }

    // Charger les pays de destination depuis l'API (pays créés par l'admin)
    let destinationCountriesData = [];
    try {
        const destinationResponse = await apiCall('/destinations/countries?actif_seulement=true');
        destinationCountriesData = destinationResponse;
    } catch (error) {
        console.error('Erreur lors du chargement des pays de destination:', error);
        showMessage('Impossible de charger la liste des pays de destination. Veuillez rafraîchir la page.', 'error');
    }

    populateCountries(destinationSelect, destinationCountriesData);

    destinationSelect?.addEventListener('change', function() {
        // Charger les villes quand un pays de destination est sélectionné
        const selectedCountryName = this.value;
        if (selectedCountryName) {
            loadCitiesForCountry(selectedCountryName, destinationCountriesData, destinationCitySelect);
        }
    });

    // Gérer l'affichage des détails des enfants mineurs
    const withMinorsYes = document.getElementById('withMinorsYes');
    const withMinorsNo = document.getElementById('withMinorsNo');
    const minorsDetailsSection = document.getElementById('minorsDetailsSection');
    const minorsCountInput = document.getElementById('minorsCount');
    const minorsList = document.getElementById('minorsList');

    function toggleMinorsDetails() {
        const showDetails = withMinorsYes?.checked;
        if (minorsDetailsSection) {
            minorsDetailsSection.style.display = showDetails ? 'block' : 'none';
        }
        if (showDetails) {
            updateMinorsList();
        } else {
            if (minorsList) minorsList.innerHTML = '';
        }
    }

    function updateMinorsList() {
        if (!minorsList || !minorsCountInput) return;
        
        const count = parseInt(minorsCountInput.value) || 1;
        if (count < 1) {
            minorsCountInput.value = 1;
            return;
        }
        if (count > 10) {
            minorsCountInput.value = 10;
            return;
        }

        minorsList.innerHTML = '';
        
        for (let i = 1; i <= count; i++) {
            const childDiv = document.createElement('div');
            childDiv.className = 'form-grid two-columns';
            childDiv.style.marginBottom = '1rem';
            childDiv.style.padding = '1rem';
            childDiv.style.border = '1px solid var(--border-color)';
            childDiv.style.borderRadius = '8px';
            childDiv.style.backgroundColor = '#f8f9fa';
            
            childDiv.innerHTML = `
                <div class="form-field">
                    <label>Enfant ${i} - Nom *</label>
                    <input type="text" name="minor_${i}_nom" required placeholder="Nom de famille">
                </div>
                <div class="form-field">
                    <label>Enfant ${i} - Prénom *</label>
                    <input type="text" name="minor_${i}_prenom" required placeholder="Prénom">
                </div>
                <div class="form-field">
                    <label>Enfant ${i} - Date de naissance *</label>
                    <input type="date" name="minor_${i}_date_naissance" required max="${new Date().toISOString().split('T')[0]}">
                </div>
            `;
            
            minorsList.appendChild(childDiv);
        }
    }

    withMinorsYes?.addEventListener('change', toggleMinorsDetails);
    withMinorsNo?.addEventListener('change', toggleMinorsDetails);
    minorsCountInput?.addEventListener('change', updateMinorsList);
    minorsCountInput?.addEventListener('input', updateMinorsList);

    dateDepartInput?.addEventListener('change', updateDuration);
    dateRetourInput?.addEventListener('change', updateDuration);

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const userId = localStorage.getItem('user_id');
        if (!userId) {
            showMessage('Impossible de récupérer votre profil. Merci de vous reconnecter.', 'error');
            return;
        }

        const formData = new FormData(form);
        let documentUploads = [];

        try {
            documentUploads = collectDocumentUploads(documentInputs, MAX_DOCUMENT_SIZE);
        } catch (error) {
            showMessage(error.message || 'Impossible de préparer les pièces jointes.', 'error');
            return;
        }

        const destination = buildDestination(
            formData.get('destination_city'),
            formData.get('destination_country')
        );
        
        // Générer un titre automatique basé sur la destination et la date
        const dateDepart = formData.get('date_depart');
        const dateStr = dateDepart ? new Date(dateDepart).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '';
        const titre = `Voyage vers ${destination}${dateStr ? ' - ' + dateStr : ''}`;

        const payload = {
            user_id: parseInt(userId, 10),
            titre: titre,
            description: null,
            destination: destination,
            date_depart: toIsoString(formData.get('date_depart')),
            date_retour: toIsoString(formData.get('date_retour'), true),
            nombre_participants: parseInt(formData.get('nombre_participants') || '1', 10),
            notes: buildNotesSummary(formData),
            questionnaire_type: 'long',
        };

        if (!payload.date_depart) {
            showMessage('Merci de préciser une date de départ valide.', 'error');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement en cours...';
        showMessage('', 'clear');

        try {
            const projet = await apiCall('/voyages', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            if (documentUploads.length) {
                showMessage('Téléversement des pièces justificatives en cours...', 'info');
                const failures = await uploadDocumentsSequentially(projet.id, documentUploads);
                if (failures.length) {
                    showMessage(
                        `Projet enregistré mais ${failures.length} document(s) n'ont pas pu être téléversés. Vous pourrez les ajouter depuis votre espace.`,
                        'error'
                    );
                } else {
                    showMessage('Projet enregistré ! Redirection vers la sélection de produit...', 'success');
                }
            } else {
                showMessage('Projet enregistré ! Redirection vers la sélection de produit...', 'success');
            }

            sessionStorage.setItem('current_project', JSON.stringify(projet));

            setTimeout(() => {
                window.location.href = `product-selection.html?projectId=${projet.id}`;
            }, 900);
        } catch (error) {
            console.error('Erreur création projet', error);
            showMessage(error.message || 'Erreur lors de la création du projet.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Continuer vers le choix du produit';
        }
    });

    function populateCountries(select, countriesData) {
        if (!select) return;
        const fragment = document.createDocumentFragment();
        fragment.appendChild(new Option('Choisir...', ''));
        countriesData.forEach((country) => {
            // Stocker l'ID dans un attribut data pour pouvoir le récupérer plus tard
            const option = new Option(country.nom, country.nom);
            option.dataset.countryId = country.id;
            fragment.appendChild(option);
        });
        select.appendChild(fragment);
    }

    async function loadCitiesForCountry(countryName, countriesData, citySelect) {
        if (!citySelect || !countryName) {
            // Réinitialiser le select des villes
            if (citySelect) {
                citySelect.innerHTML = '<option value="">Choisir un pays d\'abord...</option>';
            }
            return;
        }

        // Trouver le pays par son nom pour obtenir son ID
        const country = countriesData.find(c => c.nom === countryName);
        let countryId = country?.id;
        
        // Si l'ID n'est pas dans les données, essayer de le récupérer depuis l'option sélectionnée
        if (!countryId && destinationSelect) {
            const selectedOption = destinationSelect.options[destinationSelect.selectedIndex];
            countryId = selectedOption?.dataset?.countryId;
        }
        
        if (!countryId) {
            console.error('ID du pays non trouvé pour:', countryName);
            citySelect.innerHTML = '<option value="">Pays non trouvé</option>';
            return;
        }

        // Afficher un état de chargement
        citySelect.innerHTML = '<option value="">Chargement des villes...</option>';
        citySelect.disabled = true;

        try {
            // Charger les villes depuis l'API
            const cities = await apiCall(`/destinations/countries/${countryId}/cities?actif_seulement=true`);
            
            // Vider et remplir le select
            citySelect.innerHTML = '';
            const fragment = document.createDocumentFragment();
            fragment.appendChild(new Option('Choisir une ville...', ''));
            
            if (cities && cities.length > 0) {
                cities.forEach((city) => {
                    fragment.appendChild(new Option(city.nom, city.nom));
                });
            } else {
                fragment.appendChild(new Option('Aucune ville disponible', ''));
            }
            
            citySelect.appendChild(fragment);
            citySelect.disabled = false;
        } catch (error) {
            console.error('Erreur lors du chargement des villes:', error);
            citySelect.innerHTML = '<option value="">Erreur lors du chargement</option>';
            citySelect.disabled = false;
        }
    }

    function updateDuration() {
        if (!dateDepartInput || !durationDisplay) return;
        const depart = new Date(dateDepartInput.value);
        const retourValue = dateRetourInput?.value;
        if (!depart || Number.isNaN(depart.getTime()) || !retourValue) {
            durationDisplay.value = '';
            return;
        }
        const retour = new Date(retourValue);
        if (Number.isNaN(retour.getTime()) || retour <= depart) {
            durationDisplay.value = '';
            return;
        }
        const diffMs = retour - depart;
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
        durationDisplay.value = `${diffDays} jour(s)`;
    }

    function buildDestination(city, country) {
        const safeCity = city?.trim();
        const safeCountry = country?.trim();
        if (safeCity && safeCountry) {
            return `${safeCity} (${safeCountry})`;
        }
        return safeCity || safeCountry || 'Destination à préciser';
    }

    function toIsoString(value, optional = false) {
        if (!value) {
            return optional ? null : '';
        }
        const date = new Date(value);
        return isNaN(date.getTime()) ? (optional ? null : '') : date.toISOString();
    }

    function buildNotesSummary(formData) {
        const lines = [];
        const destinationCountry = formData.get('destination_country');
        const travelMode = formData.get('travel_mode');
        const withMinors = formData.get('with_minors');

        lines.push('Souscription: Je suis le voyageur');
        if (destinationCountry) lines.push(`Pays de destination: ${destinationCountry}`);
        if (travelMode) lines.push(`Moyen de transport: ${labelForTravelMode(travelMode)}`);
        lines.push(`Voyage avec enfants mineurs: ${withMinors === 'yes' ? 'Oui' : 'Non'}`);
        
        // Ajouter les informations sur les enfants mineurs
        if (withMinors === 'yes') {
            const minorsCount = parseInt(formData.get('minors_count') || '0');
            if (minorsCount > 0) {
                lines.push(`Nombre d'enfants mineurs: ${minorsCount}`);
                for (let i = 1; i <= minorsCount; i++) {
                    const nom = formData.get(`minor_${i}_nom`);
                    const prenom = formData.get(`minor_${i}_prenom`);
                    const dateNaissance = formData.get(`minor_${i}_date_naissance`);
                    if (nom || prenom || dateNaissance) {
                        const dateStr = dateNaissance ? new Date(dateNaissance).toLocaleDateString('fr-FR') : 'Non renseignée';
                        lines.push(`  Enfant ${i}: ${prenom || ''} ${nom || ''} (né(e) le ${dateStr})`);
                    }
                }
            }
        }
        
        return lines.join('\n');
    }

    function labelForTravelMode(value) {
        switch (value) {
            case 'avion':
                return 'Avion';
            case 'route':
                return 'Route';
            case 'mer':
                return 'Mer';
            default:
                return value;
        }
    }

    function showMessage(message, type) {
        if (!messageBox) {
            return;
        }
        if (type === 'clear') {
            messageBox.style.display = 'none';
            messageBox.textContent = '';
            messageBox.className = '';
            return;
        }
        const variant = type === 'success' ? 'alert-success' : (type === 'info' ? 'alert-info' : 'alert-error');
        messageBox.textContent = message;
        messageBox.className = `alert ${variant}`;
        messageBox.style.display = 'block';
    }

    function collectDocumentUploads(inputs, maxSize) {
        const uploads = [];
        inputs.forEach((input) => {
            const file = input?.files?.[0];
            if (!file) {
                return;
            }
            if (file.size > maxSize) {
                throw new Error(`Le fichier ${file.name} dépasse la taille autorisée (10 Mo).`);
            }
            const docType = input.dataset.docType;
            const labelInputId = input.dataset.labelInput;
            const customLabel = labelInputId ? document.getElementById(labelInputId)?.value?.trim() : null;
            const fallbackLabel = input.closest('.document-field')?.querySelector('label')?.textContent?.trim();
            uploads.push({
                type: docType,
                file,
                displayName: customLabel || fallbackLabel || file.name,
            });
        });
        return uploads;
    }

    async function uploadDocumentsSequentially(projectId, documents) {
        const failures = [];
        for (const doc of documents) {
            const formData = new FormData();
            formData.append('doc_type', doc.type);
            if (doc.displayName) {
                formData.append('display_name', doc.displayName);
            }
            formData.append('file', doc.file);
            try {
                await apiCall(`/voyages/${projectId}/documents`, {
                    method: 'POST',
                    body: formData,
                });
            } catch (error) {
                console.error('Erreur upload document', doc.displayName, error);
                failures.push(doc);
            }
        }
        return failures;
    }
});

