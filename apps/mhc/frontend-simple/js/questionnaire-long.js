document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionnaireLongForm');
    const submitBtn = document.getElementById('submitBtn');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';
        
        const formData = new FormData(form);
        const subscriptionId = parseInt(formData.get('subscription_id'));
        
        const reponses = {
            informations_personnelles: {
                date_naissance: formData.get('date_naissance'),
                lieu_naissance: formData.get('lieu_naissance'),
                nationalite: formData.get('nationalite'),
                profession: formData.get('profession'),
            },
            historique_medical: {
                hospitalisations: formData.get('hospitalisations') || '',
                chirurgies: formData.get('chirurgies') || '',
                accidents: formData.get('accidents') || '',
                maladies_chroniques: formData.get('maladies_chroniques') || '',
            },
            mode_de_vie: {
                activite_physique: formData.get('activite_physique'),
                tabagisme: formData.get('tabagisme'),
                consommation_alcool: formData.get('consommation_alcool'),
                voyages_frequents: formData.get('voyages_frequents'),
            },
            antecedents_familiaux: formData.get('antecedents_familiaux') || '',
            informations_voyage: {
                destinations_frequentes: formData.get('destinations_frequentes') || '',
                duree_sejours: formData.get('duree_sejours') || '',
                activites_risque: formData.get('activites_risque') || '',
            },
        };
        
        try {
            const result = await questionnairesAPI.createLong(subscriptionId, reponses);
            showAlert('Questionnaire long enregistré avec succès!', 'success');
            
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } catch (error) {
            showAlert(`Erreur: ${error.message}`, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enregistrer';
        }
    });
});

