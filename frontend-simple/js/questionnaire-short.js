document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionnaireShortForm');
    const submitBtn = document.getElementById('submitBtn');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Désactiver le bouton pendant l'envoi
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';
        
        // Récupérer les données du formulaire
        const formData = new FormData(form);
        const subscriptionId = parseInt(formData.get('subscription_id'));
        
        const reponses = {
            sante_generale: formData.get('sante_generale'),
            allergies: formData.get('allergies') || '',
            medicaments_actuels: formData.get('medicaments_actuels') || '',
            conditions_medicales: formData.get('conditions_medicales') || '',
            assurance_actuelle: formData.get('assurance_actuelle') || '',
        };
        
        try {
            const result = await questionnairesAPI.createShort(subscriptionId, reponses);
            showAlert('Questionnaire court enregistré avec succès!', 'success');
            
            // Rediriger après 2 secondes
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } catch (error) {
            showAlert(`Erreur: ${error.message}`, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enregistrer';
        }
    });
    
    // Validation en temps réel
    const santeGenerale = document.getElementById('sante_generale');
    const errorMessage = document.getElementById('sante_generale_error');
    
    santeGenerale.addEventListener('change', function() {
        if (this.value === '') {
            errorMessage.textContent = 'Ce champ est requis';
        } else {
            errorMessage.textContent = '';
        }
    });
});

