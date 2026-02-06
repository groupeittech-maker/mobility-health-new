// Validation des dossiers médicaux de la souscription (optionnel) : réservée au doctor. Le médecin MH valide l'inscription, pas la souscription.
const SUBSCRIPTION_MEDICAL_VALIDATION_ROLES = ['doctor'];

const REVIEW_CONFIG = {
    medecin: {
        // Accès page : doctor (validation souscription optionnelle), medical_reviewer (alertes), medecin_referent_mh (alertes SOS uniquement)
        allowedRoles: ['doctor', 'medical_reviewer', 'medecin_referent_mh'],
        title: 'Gestion des dossiers sinistres',
        description: 'Consultez les questionnaires médicaux associés aux souscriptions et émettez votre avis.',
        emptyState: 'Aucune attestation n\'est actuellement en attente de validation médicale.',
        questionnaireKeys: ['medical', 'long'],
        pillLabel: 'Avis médical',
    },
    technique: {
        allowedRoles: ['technical_reviewer', 'finance_manager', 'hospital_admin', 'admin'],
        title: 'Validation technique',
        description: 'Vérifiez la complétude administrative et technique avant de valider la souscription.',
        emptyState: 'Aucune attestation n’attend de validation technique.',
        questionnaireKeys: ['administratif', 'long'],
        pillLabel: 'Avis technique',
    },
    production: {
        allowedRoles: ['production_agent', 'admin'],
        title: 'Documents de validation',
        description: 'Dossiers en attente de validation technique et définitive. Après validation, les attestations définitives et cartes santé seront générées.',
        emptyState: 'Aucun document de validation pour le moment. Les dossiers prêts pour la validation définitive apparaîtront ici.',
        questionnaireKeys: ['medical', 'administratif', 'long'],
        pillLabel: 'Production',
    },
};

const QUESTIONNAIRE_LABELS = {
    short: 'Questionnaire court',
    long: 'Questionnaire long',
    administratif: 'Questionnaire administratif',
    medical: 'Questionnaire médical',
};
const QUESTIONNAIRE_ORDER = ['medical', 'long', 'administratif', 'short'];

const QUESTION_FIELD_LABELS = {
    administratif: {
        personal: {
            label: 'Informations personnelles',
            fields: {
                fullName: 'Nom complet',
                birthDate: 'Date de naissance',
                gender: 'Genre',
                nationality: 'Nationalité',
                passportNumber: 'Numéro de passeport',
                address: 'Adresse',
                phone: 'Téléphone',
                email: 'Email',
                emergencyContact: 'Contact d’urgence',
                emergencyPhone: 'Téléphone du contact d’urgence',
            },
        },
        technical: {
            label: 'Informations techniques et engagement',
            fields: {
                recentSubscription: 'Souscription récente auprès d’un assureur',
                refusedInsurance: 'Assurance refusée par le passé',
                deliveryMode: 'Mode de livraison des documents',
                acceptCG: 'Conditions générales acceptées',
                acceptExclusions: 'Clauses d’exclusion acceptées',
                acceptData: 'Consentement aux traitements de données',
                honesty1: 'Déclaration sur l’honneur (exactitude)',
                honesty2: 'Déclaration sur l’honneur (documents fournis)',
            },
        },
    },
    medical: {
        symptoms: { label: 'Maladies ou symptômes observés récemment' },
        symptomOther: { label: 'Autre (précisez)' },
        pregnancy: { label: 'Êtes-vous enceinte ? (si concerné)' },
        surgeryLast6Months: { label: 'Opération chirurgicale dans les 6 derniers mois' },
        surgeryLast6MonthsDetails: { label: 'Précisions opération' },
        photoMedicale: { label: 'Photo médicale' },
        // Anciens champs (compatibilité avec données existantes)
        chronicDiseases: { label: 'Maladies chroniques connues' },
        regularTreatment: { label: 'Traitement régulier' },
        treatmentDetails: { label: 'Détails du traitement' },
        recentHospitalization: { label: 'Hospitalisation récente' },
        hospitalizationDetails: { label: 'Détails de l\'hospitalisation' },
        recentSurgery: { label: 'Chirurgie récente' },
        surgeryDetails: { label: 'Détails de la chirurgie' },
        infectiousDiseases: { label: 'Maladies infectieuses' },
        contactRisk: { label: 'Contact à risque' },
        // Clés alternatives possibles
        maladies_chroniques: { label: 'Maladies chroniques' },
        traitement_medical: { label: 'Traitement médical' },
        traitement_medical_details: { label: 'Détails du traitement médical' },
        hospitalisation_12mois: { label: 'Hospitalisation dans les 12 derniers mois' },
        hospitalisation_12mois_details: { label: 'Détails de l\'hospitalisation' },
        operation_5ans: { label: 'Opération dans les 5 dernières années' },
        operation_5ans_details: { label: 'Détails de l\'opération' },
        maladies_contagieuses: { label: 'Maladies contagieuses' },
        contact_personne_malade: { label: 'Contact avec personne malade' },
        honourDeclaration: {
            label: 'Déclaration sur l’honneur',
            fields: {
                medicalHonesty1: 'Je déclare n\'avoir rien omis dans ce questionnaire.',
                medicalHonesty2: 'Je reconnais qu\'une fausse déclaration entraîne la nullité des garanties.',
            },
        },
    },
    long: {
        informations_personnelles: {
            label: 'Informations personnelles',
            fields: {
                date_naissance: 'Date de naissance',
                lieu_naissance: 'Lieu de naissance',
                nationalite: 'Nationalité',
                profession: 'Profession',
            },
        },
        historique_medical: {
            label: 'Historique médical',
            fields: {
                hospitalisations: 'Hospitalisations',
                chirurgies: 'Chirurgies',
                accidents: 'Accidents',
                maladies_chroniques: 'Maladies chroniques',
            },
        },
        mode_de_vie: {
            label: 'Mode de vie',
            fields: {
                activite_physique: 'Activité physique',
                tabagisme: 'Tabagisme',
                consommation_alcool: 'Consommation d’alcool',
                voyages_frequents: 'Voyages fréquents',
            },
        },
        antecedents_familiaux: { label: 'Antécédents familiaux' },
        informations_voyage: {
            label: 'Informations voyage',
            fields: {
                destinations_frequentes: 'Destinations fréquentes',
                duree_sejours: 'Durée moyenne des séjours',
                activites_risque: 'Activités à risque prévues',
            },
        },
    },
    short: {
        sante_generale: { label: 'État de santé général' },
        allergies: { label: 'Allergies' },
        medicaments_actuels: { label: 'Médicaments actuels' },
        conditions_medicales: { label: 'Conditions médicales' },
        assurance_actuelle: { label: 'Assurance actuelle' },
    },
};

const MEDICAL_SECTIONS = [
    {
        key: 'symptoms',
        label: 'Maladies et symptômes récents',
        description: 'Maladies ou symptômes observés récemment, grossesse, opération chirurgicale.',
        fields: ['symptoms', 'symptomOther', 'pregnancy', 'surgeryLast6Months', 'surgeryLast6MonthsDetails', 'photoMedicale'],
    },
    {
        key: 'honour',
        label: 'Déclaration sur l\'honneur',
        fields: ['honourDeclaration'],
    },
];

const VALIDATION_LABELS = {
    medecin: 'Médical',
    technique: 'Technique',
    production: 'Production',
};

const STATUS_META = {
    pending: { label: 'En attente', className: 'status-pending' },
    approved: { label: 'Approuvé', className: 'status-active' },
    rejected: { label: 'Refusé', className: 'status-inactive' },
};

const ALERT_VALIDATION_ALLOWED_ROLES = new Set(['medecin_referent_mh']);
const ALERT_ACTIVE_STATUSES = new Set(['en_attente', 'en_cours']);
const ALERT_STATUS_LABELS = {
    en_attente: 'En attente',
    en_cours: 'En cours',
    resolue: 'Résolue',
    annulee: 'Annulée',
};
const ALERT_STATUS_CLASSES = {
    en_attente: 'status-pending',
    en_cours: 'status-active',
    resolue: 'status-active',
    annulee: 'status-inactive',
};
const ALERT_PRIORITY_LABELS = {
    critique: 'Critique',
    urgente: 'Urgente',
    elevee: 'Élevée',
    normale: 'Normale',
    faible: 'Faible',
};
const ALERT_PRIORITY_CLASSES = {
    critique: 'priority-critique',
    urgente: 'priority-urgente',
    elevee: 'priority-elevee',
    normale: 'priority-normale',
    faible: 'priority-faible',
};

const MEDICAL_NOTIFICATION_TYPES = {
    sos_alert: {
        label: 'Alerte déclenchée',
        icon: '🚨',
        defaultMessage: 'Une alerte SOS vient d’être déclenchée pour un assuré.',
    },
    ambulance_dispatched: {
        label: 'Ambulance envoyée',
        icon: '🚑',
        defaultMessage: 'L’ambulance d’un hôpital partenaire est en route.',
    },
    medical_report_submitted: {
        label: 'Rapport médical reçu',
        icon: '📄',
        defaultMessage: 'Un médecin hospitalier vient de transmettre son rapport.',
    },
    invoice_medical_review: {
        label: 'Facture à valider',
        icon: '💼',
        defaultMessage: 'Une facture nécessite votre validation médicale.',
    },
};

const MEDICAL_NOTIFICATION_ORDER = [
    'sos_alert',
    'ambulance_dispatched',
    'medical_report_submitted',
    'invoice_medical_review',
];

/** Étapes de validation du médecin référent (onglets). Un dossier est classé dans la première étape qui correspond. */
const REFERENT_STEP_KEYS = Object.freeze([
    'sinistre', 'sinistre_valide', 'rapport', 'rapport_valide', 'facture', 'facture_valide', 'resolu'
]);

const ROWS_PER_PAGE = 6;
let currentPageAlertValidation = 0;
let currentPageReview = 0;

const alertValidationState = {
    enabled: false,
    elements: {},
    data: [],
    currentTab: 'sinistre',
    tabCounts: {
        sinistre: 0, sinistre_valide: 0, rapport: 0, rapport_valide: 0,
        facture: 0, facture_valide: 0, resolu: 0,
    },
    tabFromUrl: null,
};

const medicalNotificationsState = {
    enabled: false,
    items: [],
    elements: {},
    caches: {
        sinistres: {},
    },
};

let reviewContext = {
    type: null,
    config: null,
};

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const reviewType = document.body.dataset.reviewType;
        if (!reviewType || !REVIEW_CONFIG[reviewType]) {
            console.error('Type de revue inconnu ou non configuré.');
            return;
        }

        reviewContext = {
            type: reviewType,
            config: REVIEW_CONFIG[reviewType],
        };

        if (typeof requireAnyRole === 'undefined') {
            console.error('requireAnyRole n\'est pas défini. Vérifiez que auth.js est chargé.');
            return;
        }

        const hasAccess = await requireAnyRole(reviewContext.config.allowedRoles, 'index.html');
        if (!hasAccess) {
            return;
        }
    } catch (error) {
        console.error('Erreur lors de l\'initialisation de la page:', error);
        const container = document.getElementById('reviewContainer');
        if (container) {
            container.innerHTML = `<div class="alert alert-error">Erreur d'initialisation: ${error.message || 'Erreur inconnue'}</div>`;
        }
        return;
    }

    if (document.getElementById('reviewTitle')) {
        document.getElementById('reviewTitle').textContent = reviewContext.config.title;
    }
    if (document.getElementById('reviewIntro')) {
        document.getElementById('reviewIntro').textContent = reviewContext.config.description;
    }

    const currentRole = (localStorage.getItem('user_role') || '').toLowerCase();
    const canValidateSubscription = SUBSCRIPTION_MEDICAL_VALIDATION_ROLES.includes(currentRole);
    const canLoadReviewItems = (reviewContext.config.allowedRoles || []).some(
        (r) => String(r).toLowerCase() === currentRole
    );

    setupMedecinReferentUI();

    if (canLoadReviewItems) {
        try {
            await loadReviewItems();
        } catch (error) {
            console.error('Erreur lors du chargement des éléments de revue:', error);
            const container = document.getElementById('reviewContainer');
            if (container) {
                container.innerHTML = `<div class="alert alert-error">Erreur lors du chargement: ${error.message || 'Erreur inconnue'}</div>`;
            }
        }
    }

    try {
        initAlertValidationModule();
    } catch (error) {
        console.error('Erreur lors de l\'initialisation du module de validation d\'alertes:', error);
    }

    initSectionNavigation();
});

function setupMedecinReferentUI() {
    const role = (localStorage.getItem('user_role') || '').toLowerCase();
    const isMedecinReferent = role === 'medecin_referent_mh';

    const separator = document.getElementById('validationBlockSeparator');
    const roleBadge = document.getElementById('reviewRoleBadge');
    const avisMedicauxSection = document.getElementById('avisMedicauxSection');
    const navAvisMedicaux = document.querySelector('.nav-section-links a[data-section="avisMedicauxSection"]')?.closest('li');
    const navAlertesSos = document.getElementById('navAlertesSos');

    // Médecin référent : masquer la validation des dossiers médicaux de la souscription (réservée au médecin MH / medical_reviewer)
    if (isMedecinReferent) {
        if (avisMedicauxSection) avisMedicauxSection.style.display = 'none';
        if (navAvisMedicaux) navAvisMedicaux.style.display = 'none';
    }
    if (roleBadge && isMedecinReferent) {
        roleBadge.textContent = 'En qualité de médecin référent MH';
        roleBadge.style.display = 'block';
    }
    if (separator && isMedecinReferent) {
        separator.style.display = 'block';
    }
    if (navAlertesSos && isMedecinReferent) {
        navAlertesSos.style.display = 'list-item';
    }
}

function initSectionNavigation() {
    const navLinks = document.querySelectorAll('.nav-section-link');
    const sectionIds = ['avisMedicauxSection', 'alertValidationSection'];
    const sections = sectionIds
        .map(id => document.getElementById(id))
        .filter(section => section !== null);
    const navbar = document.querySelector('.navbar');
    const navbarHeight = navbar ? navbar.offsetHeight : 80;

    if (navLinks.length === 0 || sections.length === 0) {
        return;
    }

    // Gérer le clic sur les liens
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                const targetPosition = targetSection.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
                
                // Mettre à jour l'état actif immédiatement
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }
        });
    });

    // Mettre en évidence la section active lors du scroll
    function updateActiveSection() {
        const scrollPosition = window.pageYOffset + navbarHeight + 100;
        let activeSectionId = null;
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.id;
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                activeSectionId = sectionId;
            }
        });
        
        // Si aucune section n'est visible, utiliser la première visible
        if (!activeSectionId) {
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                if (window.pageYOffset + navbarHeight >= sectionTop - 50) {
                    activeSectionId = section.id;
                }
            });
        }
        
        // Mettre à jour les liens
        navLinks.forEach(link => {
            if (link.getAttribute('data-section') === activeSectionId) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    // Mettre à jour au scroll
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(updateActiveSection, 50);
    });

    // Mettre à jour au chargement et après un délai pour laisser le temps au contenu de se charger
    setTimeout(updateActiveSection, 100);
    updateActiveSection();
}

function initMedicalNotificationsModule() {
    const section = document.getElementById('medicalNotificationsSection');
    if (!section) {
        return;
    }

    const role = (localStorage.getItem('user_role') || '').toLowerCase();
    if (role !== 'medecin_referent_mh') {
        section.style.display = 'none';
        return;
    }

    medicalNotificationsState.enabled = true;
    medicalNotificationsState.elements = {
        section,
        list: document.getElementById('medicalNotificationsList'),
        empty: document.getElementById('medicalNotificationsEmpty'),
        loading: document.getElementById('medicalNotificationsLoading'),
        error: document.getElementById('medicalNotificationsError'),
        count: document.getElementById('medicalNotificationsCount'),
        refreshButton: document.getElementById('refreshMedicalNotificationsBtn'),
    };

    if (medicalNotificationsState.elements.refreshButton) {
        medicalNotificationsState.elements.refreshButton.addEventListener('click', () =>
            loadMedicalNotifications(true)
        );
    }
    if (medicalNotificationsState.elements.list) {
        medicalNotificationsState.elements.list.addEventListener('click', handleNotificationCardClick);
        medicalNotificationsState.elements.list.addEventListener('keydown', handleNotificationCardKeyDown);
    }

    loadMedicalNotifications().catch((error) => {
        console.error('Erreur lors du chargement initial des notifications:', error);
    });
}

async function loadMedicalNotifications(showToast = false) {
    if (!medicalNotificationsState.enabled) {
        return;
    }

    const { error, loading } = medicalNotificationsState.elements;
    if (error) {
        error.hidden = true;
        error.textContent = '';
    }
    if (loading) {
        setHidden(loading, false);
    }

    try {
        const response = await apiCall('/notifications?limit=50');
        const notifications = Array.isArray(response) ? response : [];
        const filtered = notifications.filter(
            (item) => MEDICAL_NOTIFICATION_TYPES[item.type_notification] && !item.is_read
        );
        medicalNotificationsState.items = sortMedicalNotifications(filtered);
        renderMedicalNotifications();
        if (showToast) {
            showAlert('Notifications mises à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des notifications médicales:', error);
        if (medicalNotificationsState.elements.error) {
            medicalNotificationsState.elements.error.hidden = false;
            medicalNotificationsState.elements.error.textContent =
                error.message || 'Impossible de charger les notifications médicales.';
        }
        medicalNotificationsState.items = [];
        renderMedicalNotifications();
    } finally {
        if (loading) {
            setHidden(loading, true);
        }
    }
}

function sortMedicalNotifications(notifications) {
    return notifications
        .slice()
        .sort((a, b) => {
            const typeIndexA = MEDICAL_NOTIFICATION_ORDER.indexOf(a.type_notification);
            const typeIndexB = MEDICAL_NOTIFICATION_ORDER.indexOf(b.type_notification);
            if (typeIndexA !== typeIndexB) {
                const safeA = typeIndexA === -1 ? Number.MAX_SAFE_INTEGER : typeIndexA;
                const safeB = typeIndexB === -1 ? Number.MAX_SAFE_INTEGER : typeIndexB;
                return safeA - safeB;
            }
            return new Date(b.created_at || 0) - new Date(a.created_at || 0);
        });
}

function renderMedicalNotifications() {
    const { list, empty } = medicalNotificationsState.elements;
    if (!list || !empty) {
        return;
    }

    const notifications = medicalNotificationsState.items || [];
    updateMedicalNotificationCount(notifications.length);

    if (!notifications.length) {
        list.innerHTML = '';
        setHidden(list, true);
        setHidden(empty, false);
        return;
    }

    list.innerHTML = notifications.map((notification, index) => buildMedicalNotificationCard(notification, index)).join('');
    setHidden(empty, true);
    setHidden(list, false);
}

function buildMedicalNotificationCard(notification, index) {
    try {
        const config = MEDICAL_NOTIFICATION_TYPES[notification.type_notification];
        if (!config) {
            return '';
        }
        const timestamp = notification.created_at && typeof formatDateTime === 'function' 
            ? formatDateTime(notification.created_at) 
            : (notification.created_at ? new Date(notification.created_at).toLocaleString('fr-FR') : '—');
        const relativeTime = getRelativeTime(notification.created_at);
        const title = notification.titre || config.label;
        const body = notification.message || config.defaultMessage;
        const reference = getNotificationReference(notification);
        
        // Extraire la priorité du message si disponible
        const priority = extractPriorityFromMessage(body);
        const priorityClass = priority ? `notification-priority--${priority}` : '';
        
        // Formater le message pour améliorer la lisibilité
        const formattedBody = formatMedicalNotificationMessage(body);
        
        // Déterminer la couleur de bordure selon le type
        const borderColorClass = getNotificationBorderColorClass(notification.type_notification);

    return `
        <div class="card notification-card ${borderColorClass} ${priorityClass}" data-notification-type="${notification.type_notification}">
            <div
                class="notification-card__body"
                role="button"
                tabindex="0"
                data-notification-index="${index}"
                aria-label="Ouvrir le dossier lié à cette notification"
            >
            <div class="notification-card__header">
                <span class="notification-pill notification-pill--${notification.type_notification}">
                    <span aria-hidden="true" class="notification-icon">${config.icon}</span>
                    <span>${typeof escapeHtml === 'function' ? escapeHtml(config.label) : config.label}</span>
                </span>
                <div class="notification-time-group">
                    <span class="notification-time" title="${timestamp}">${relativeTime}</span>
                    ${priority ? `<span class="notification-priority-badge priority-${priority}">${getPriorityLabel(priority)}</span>` : ''}
                </div>
            </div>
            <h4 class="notification-title">${typeof escapeHtml === 'function' ? escapeHtml(title) : title}</h4>
            <div class="notification-body">${formattedBody}</div>
            ${reference ? `<div class="notification-meta">
                <span class="notification-meta-icon">📎</span>
                <span>${typeof escapeHtml === 'function' ? escapeHtml(reference) : reference}</span>
            </div>` : ''}
            <div class="notification-footer">
                <span class="notification-link">
                    <span class="notification-link-icon">→</span>
                    <span>Cliquer pour ouvrir le dossier</span>
                </span>
            </div>
            </div>
        </div>
    `;
    } catch (error) {
        console.error('Erreur lors de la construction de la carte de notification:', error);
        return '';
    }
}

function getRelativeTime(dateString) {
    if (!dateString) return '—';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSecs < 60) {
            return 'À l\'instant';
        } else if (diffMins < 60) {
            return `Il y a ${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'}`;
        } else if (diffHours < 24) {
            return `Il y a ${diffHours} ${diffHours === 1 ? 'heure' : 'heures'}`;
        } else if (diffDays < 7) {
            return `Il y a ${diffDays} ${diffDays === 1 ? 'jour' : 'jours'}`;
        } else {
            return typeof formatDateTime === 'function' 
                ? formatDateTime(dateString) 
                : date.toLocaleDateString('fr-FR');
        }
    } catch (error) {
        return '—';
    }
}

function extractPriorityFromMessage(message) {
    if (!message || typeof message !== 'string') return null;
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('priorité: critique') || lowerMessage.includes('critique')) {
        return 'critique';
    } else if (lowerMessage.includes('priorité: urgente') || lowerMessage.includes('urgente')) {
        return 'urgente';
    } else if (lowerMessage.includes('priorité: élevée') || lowerMessage.includes('élevée')) {
        return 'elevee';
    } else if (lowerMessage.includes('priorité: normale') || lowerMessage.includes('normale')) {
        return 'normale';
    } else if (lowerMessage.includes('priorité: faible') || lowerMessage.includes('faible')) {
        return 'faible';
    }
    return null;
}

function getPriorityLabel(priority) {
    const labels = {
        critique: 'Critique',
        urgente: 'Urgente',
        elevee: 'Élevée',
        normale: 'Normale',
        faible: 'Faible'
    };
    return labels[priority] || priority;
}

function getNotificationBorderColorClass(type) {
    const colorMap = {
        'sos_alert': 'notification-border--alert',
        'ambulance_dispatched': 'notification-border--ambulance',
        'medical_report_submitted': 'notification-border--report',
        'invoice_medical_review': 'notification-border--invoice'
    };
    return colorMap[type] || '';
}

function getNotificationReference(notification) {
    if (!notification) {
        return '';
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return `Sinistre #${notification.lien_relation_id}`;
    }
    if (notification.lien_relation_type === 'invoice' && notification.lien_relation_id) {
        return `Facture #${notification.lien_relation_id}`;
    }
    return '';
}

function updateMedicalNotificationCount(value) {
    if (!medicalNotificationsState.elements.count) {
        return;
    }
    const suffix = value > 1 ? 'NOTIFICATIONS' : 'NOTIFICATION';
    medicalNotificationsState.elements.count.textContent = `${value} ${suffix}`;
    
    // Ajouter une classe pour les notifications importantes
    if (value > 0) {
        medicalNotificationsState.elements.count.classList.add('badge--active');
    } else {
        medicalNotificationsState.elements.count.classList.remove('badge--active');
    }
}

async function handleNotificationCardClick(event) {
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    const index = Number(card.dataset.notificationIndex);
    await openNotificationTargetByIndex(index, card);
}

async function handleNotificationCardKeyDown(event) {
    if (!['Enter', ' '].includes(event.key)) {
        return;
    }
    const card = event.target.closest('[data-notification-index]');
    if (!card) {
        return;
    }
    event.preventDefault();
    const index = Number(card.dataset.notificationIndex);
    await openNotificationTargetByIndex(index, card);
}

async function openNotificationTargetByIndex(index, cardElement) {
    if (!Number.isFinite(index) || index < 0) {
        return;
    }
    const notifications = medicalNotificationsState.items || [];
    const notification = notifications[index];
    if (!notification) {
        return;
    }
    cardElement?.classList.add('notification-card--loading');
    try {
        const targetUrl = await resolveNotificationLink(notification);
        if (targetUrl) {
            await markNotificationAsRead(notification.id);
            medicalNotificationsState.items = medicalNotificationsState.items.filter(
                (item) => item.id !== notification.id
            );
            renderMedicalNotifications();
            window.location.href = targetUrl;
        } else {
            showAlert('Impossible de trouver le dossier associé à cette notification.', 'error');
        }
    } catch (error) {
        console.error('Erreur lors de l\'ouverture du dossier notification:', error);
        showAlert(error.message || 'Ouverture du dossier impossible.', 'error');
    } finally {
        cardElement?.classList.remove('notification-card--loading');
    }
}

async function markNotificationAsRead(notificationId) {
    if (!notificationId) {
        return;
    }
    try {
        await apiCall(`/notifications/${notificationId}/read`, {
            method: 'PATCH',
        });
    } catch (error) {
        console.error(`Erreur lors du marquage de la notification ${notificationId} comme lue:`, error);
    }
}

async function resolveNotificationLink(notification) {
    if (!notification) {
        return null;
    }
    if (notification.lien_relation_type === 'sinistre' && notification.lien_relation_id) {
        return resolveSinistreNotificationLink(notification.lien_relation_id);
    }
    if (notification.lien_relation_type === 'invoice' && notification.lien_relation_id) {
        return `mh-invoices.html?invoice_id=${notification.lien_relation_id}`;
    }
    return null;
}

async function resolveSinistreNotificationLink(rawId) {
    const sinistreId = Number(rawId);
    if (!Number.isFinite(sinistreId)) {
        return null;
    }
    if (!medicalNotificationsState.caches) {
        medicalNotificationsState.caches = { sinistres: {} };
    }
    const cache = medicalNotificationsState.caches.sinistres || {};
    if (cache[sinistreId]) {
        return cache[sinistreId];
    }
    try {
        const sinistre = await apiCall(`/hospital-sinistres/sinistres/${sinistreId}`);
        const alertId = sinistre?.alerte_id;
        const url = alertId ? `hospital-alert-details.html?alert_id=${alertId}` : null;
        cache[sinistreId] = url;
        medicalNotificationsState.caches.sinistres = cache;
        return url;
    } catch (error) {
        console.error(`Impossible de résoudre le sinistre ${sinistreId}:`, error);
        return null;
    }
}

async function loadReviewItems() {
    const container = document.getElementById('reviewContainer');
    if (!container) {
        console.warn('reviewContainer non trouvé');
        return;
    }

    if (typeof showLoading !== 'undefined') {
        showLoading(container);
    } else {
        container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
    }
    
    try {
        if (!reviewContext || !reviewContext.type) {
            throw new Error('Contexte de revue non défini');
        }
        
        if (typeof attestationsAPI === 'undefined' || !attestationsAPI.getReviews) {
            throw new Error('API attestations non disponible');
        }
        
        const items = await attestationsAPI.getReviews(reviewContext.type);
        const count = items && items.length ? items.length : 0;
        updateNavAvisCount(count);
        if (reviewContext.type === 'production') {
            window._productionReviewItems = items || [];
        }
        if (!items || !items.length) {
            container.innerHTML = `<div class="alert alert-info">${reviewContext.config.emptyState}</div>`;
            document.getElementById('reviewPagination') && (document.getElementById('reviewPagination').innerHTML = '');
            return;
        }
        const totalPages = Math.max(1, Math.ceil(items.length / ROWS_PER_PAGE));
        currentPageReview = Math.min(currentPageReview, totalPages - 1);
        const start = currentPageReview * ROWS_PER_PAGE;
        const pageData = items.slice(start, start + ROWS_PER_PAGE);
        if (reviewContext.type === 'production') {
            container.innerHTML = pageData.map(renderProductionCompactCard).join('');
            container.querySelectorAll('[data-production-detail]').forEach((el) => {
                el.addEventListener('click', () => openProductionDetailModal(Number(el.dataset.attestationId)));
            });
        } else {
            container.innerHTML = pageData.map(renderReviewCard).join('');
        }
        const pagEl = document.getElementById('reviewPagination');
        if (pagEl && items.length > ROWS_PER_PAGE) {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, items.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${items.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="reviewPrev" ${currentPageReview <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageReview + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="reviewNext" ${currentPageReview >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('reviewPrev')?.addEventListener('click', () => { currentPageReview--; loadReviewItems(); });
            document.getElementById('reviewNext')?.addEventListener('click', () => { currentPageReview++; loadReviewItems(); });
        } else if (pagEl) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        }
    } catch (error) {
        console.error('Erreur dans loadReviewItems:', error);
        updateNavAvisCount(0);
        const errorMessage = error.message || 'Erreur lors du chargement des données';
        container.innerHTML = `<div class="alert alert-error">Erreur: ${errorMessage}</div>`;
        throw error; // Re-throw pour que l'appelant puisse gérer l'erreur
    }
}

function updateNavAvisCount(value) {
    const el = document.getElementById('navAvisCount');
    if (el) el.textContent = String(value);
    
    // Mettre à jour le compteur dans l'onglet de validation pour les agents de production
    const validationsCountEl = document.getElementById('validationsCount');
    if (validationsCountEl) {
        validationsCountEl.textContent = `(${value})`;
        // Masquer si 0, sinon afficher
        if (value === 0) {
            validationsCountEl.style.display = 'none';
        } else {
            validationsCountEl.style.display = 'inline';
        }
    }
}

function updateNavAlertesCount(value) {
    const el = document.getElementById('navAlertesCount');
    if (el) el.textContent = String(value);
}

function renderReviewCard(item) {
    const questionnairesSection = renderQuestionnairesSection(item);
    // Profil production : pas de statut des validations, pas de rapport IA, pas d'information personnel (déjà dans questionnaire administratif)
    const validationsSection = reviewContext.type === 'production' ? '' : renderValidationSection(item);
    const iaAnalysisSection = ''; // Retiré pour le profil agent de production
    const personalInfoSection = reviewContext.type === 'production' ? '' : renderPersonalInfoSection(item);
    const medicalDataSection = reviewContext.type === 'production' ? renderProductionMedicalSection(item) : '';
    // Afficher les informations du tiers pour les validations médicale et production
    const tierInfoSection = (reviewContext.type === 'medecin' || reviewContext.type === 'production') && item.is_tier_subscription 
        ? renderTierInfoSection(item) 
        : '';
    const createdAt = formatDateTime(item.attestation_created_at);

    const clientLabel = formatClient(item);
    const productLabel = item.produit_nom || 'Non renseigné';
    const priceLabel = typeof item.prix_applique === 'number'
        ? `${item.prix_applique.toFixed(2)} €`
        : 'Non communiqué';
    const travelWindow = `${formatDate(item.date_debut)} → ${formatDate(item.date_fin)}`;

    // Pour la production, on affiche aussi les dossiers déjà validés : masquer le formulaire si pas "pending"
    const validationStatus = (item.validation_status || item.validations?.[reviewContext.type]?.status || 'pending').toLowerCase();
    const isPending = validationStatus === 'pending';
    const actionsHtml = isPending
        ? `
            <div class="review-actions">
                <div class="decision-group">
                    <label>
                        <input type="radio" name="decision-${item.attestation_id}" value="approve">
                        Approuver
                    </label>
                    <label>
                        <input type="radio" name="decision-${item.attestation_id}" value="reject">
                        Refuser
                    </label>
                </div>
                <textarea
                    id="comment-${item.attestation_id}"
                    rows="3"
                    placeholder="Commentaire (obligatoire en cas de refus)"
                ></textarea>
                <div class="review-action-buttons">
                    <button
                        class="btn btn-success"
                        id="submit-${item.attestation_id}"
                        onclick="submitReviewDecision(${item.attestation_id})"
                    >
                        Enregistrer l'avis
                    </button>
                    <button
                        class="btn btn-secondary"
                        onclick="openAttestationPdf(${item.attestation_id})"
                        type="button"
                    >
                        Voir l'attestation
                    </button>
                </div>
            </div>`
        : `
            <div class="review-actions">
                <p class="validation-done"><strong>${validationStatus === 'approved' ? 'Déjà validé' : 'Refusé'}</strong></p>
                <div class="review-action-buttons">
                    <button
                        class="btn btn-secondary"
                        onclick="openAttestationPdf(${item.attestation_id})"
                        type="button"
                    >
                        Voir l'attestation
                    </button>
                </div>
            </div>`;

    return `
        <article class="review-card" id="review-${item.attestation_id}">
            <header class="review-card__header">
                <div>
                    <h3>Souscription ${item.numero_souscription}</h3>
                    <p class="muted">Attestation ${item.numero_attestation} • créée le ${createdAt}</p>
                </div>
                <span class="pill">${reviewContext.config.pillLabel}</span>
            </header>

            <div class="review-meta">
                <p><strong>Client:</strong> ${clientLabel}</p>
                <p><strong>Produit:</strong> ${productLabel}</p>
                <p><strong>Prix appliqué:</strong> ${priceLabel}</p>
                <p><strong>Période:</strong> ${travelWindow}</p>
            </div>

            ${tierInfoSection}
            ${medicalDataSection}
            ${questionnairesSection}
            ${personalInfoSection}
            ${validationsSection}
            ${iaAnalysisSection}

            ${actionsHtml}
        </article>
    `;
}

function renderPersonalInfoSection(item) {
    const personalFields = QUESTION_FIELD_LABELS.administratif?.personal?.fields || {};

    // Fonction helper pour récupérer une valeur avec priorité sur les données utilisateur, puis questionnaire
    const getValue = (userField, camelKey, snakeKey, fallback = '—') => {
        // Priorité 1: Données utilisateur depuis l'inscription
        if (item[userField] !== null && item[userField] !== undefined && item[userField] !== '') {
            return item[userField];
        }
        
        // Priorité 2: Questionnaire administratif
        const adminQuestionnaire = item.questionnaires?.administratif;
        if (adminQuestionnaire && adminQuestionnaire.reponses) {
            const personalInfo = adminQuestionnaire.reponses.personal || {};
            const value = personalInfo[camelKey] || personalInfo[snakeKey];
            if (value !== null && value !== undefined && value !== '') {
                return value;
            }
        }
        
        // Fallback
        return fallback;
    };

    // Extraire les valeurs avec priorité sur les données utilisateur
    const fullName = item.client_name || getValue('client_name', 'fullName', 'full_name', '—');
    const birthDate = getValue('client_date_naissance', 'birthDate', 'birth_date');
    const formattedBirthDate = birthDate !== '—' && birthDate ? formatDate(birthDate) : '—';
    const gender = getValue('client_sexe', 'gender', 'genre');
    const nationality = getValue('client_nationalite', 'nationality', 'nationalite');
    const passportNumber = getValue('client_numero_passeport', 'passportNumber', 'passport_number');
    const passportExpiryDate = getValue('client_validite_passeport', 'passportExpiryDate', 'passport_expiry_date');
    const formattedPassportExpiry = passportExpiryDate !== '—' && passportExpiryDate ? formatDate(passportExpiryDate) : '—';
    
    // Pour l'adresse, on utilise uniquement le questionnaire (pas stocké dans User)
    const adminQuestionnaire = item.questionnaires?.administratif;
    const personalInfo = adminQuestionnaire?.reponses?.personal || {};
    const address = personalInfo.address || personalInfo.adresse || '—';
    
    const phone = getValue('client_telephone', 'phone', 'telephone', '—');
    const email = item.client_email || getValue('client_email', 'email', 'email', '—');
    const paysResidence = getValue('client_pays_residence', 'paysResidence', 'pays_residence');
    const emergencyContact = getValue('client_contact_urgence', 'emergencyContact', 'emergency_contact');
    
    // Pour le téléphone d'urgence, on utilise uniquement le questionnaire
    const emergencyPhone = personalInfo.emergencyPhone || personalInfo.emergency_phone || '—';

    return `
        <section class="review-section review-section--personal-info">
            <h4>Informations personnelles de l'assuré</h4>
            <div class="personal-info-grid">
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.fullName || 'Nom complet')}</span>
                    <strong class="personal-info-value">${escapeHtml(fullName)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.birthDate || 'Date de naissance')}</span>
                    <strong class="personal-info-value">${escapeHtml(formattedBirthDate)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.gender || 'Genre')}</span>
                    <strong class="personal-info-value">${escapeHtml(gender)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.nationality || 'Nationalité')}</span>
                    <strong class="personal-info-value">${escapeHtml(nationality)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.passportNumber || 'Numéro de passeport')}</span>
                    <strong class="personal-info-value">${escapeHtml(passportNumber)}</strong>
                </div>
                ${formattedPassportExpiry !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">Date d'expiration du passeport</span>
                    <strong class="personal-info-value">${escapeHtml(formattedPassportExpiry)}</strong>
                </div>
                ` : ''}
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.address || 'Adresse')}</span>
                    <strong class="personal-info-value">${escapeHtml(address)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.phone || 'Téléphone')}</span>
                    <strong class="personal-info-value">${escapeHtml(phone)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.email || 'Email')}</span>
                    <strong class="personal-info-value">${escapeHtml(email)}</strong>
                </div>
                ${paysResidence !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">Pays de résidence</span>
                    <strong class="personal-info-value">${escapeHtml(paysResidence)}</strong>
                </div>
                ` : ''}
                ${emergencyContact !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.emergencyContact || "Contact d'urgence")}</span>
                    <strong class="personal-info-value">${escapeHtml(emergencyContact)}</strong>
                </div>
                ` : ''}
                ${emergencyPhone !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.emergencyPhone || "Téléphone du contact d'urgence")}</span>
                    <strong class="personal-info-value">${escapeHtml(emergencyPhone)}</strong>
                </div>
                ` : ''}
            </div>
        </section>
        <style>
            .review-section--personal-info {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                border: 1px solid #dee2e6;
            }
            .review-section--personal-info h4 {
                margin-top: 0;
                margin-bottom: 1rem;
                color: #212529;
                font-size: 1.1rem;
                font-weight: 600;
            }
            .personal-info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1rem;
            }
            .personal-info-item {
                display: flex;
                flex-direction: column;
                gap: 0.25rem;
            }
            .personal-info-label {
                font-size: 0.875rem;
                color: #6c757d;
                font-weight: 500;
            }
            .personal-info-value {
                font-size: 1rem;
                color: #212529;
                font-weight: 600;
            }
        </style>
    `;
}

function renderTierInfoSection(item) {
    // Vérifier si c'est une souscription pour un tiers et si les informations sont disponibles
    if (!item.is_tier_subscription || !item.tier_full_name) {
        return '';
    }

    const personalFields = QUESTION_FIELD_LABELS.administratif?.personal?.fields || {};
    
    const tierFullName = item.tier_full_name || '—';
    const tierBirthDate = item.tier_birth_date ? formatDate(item.tier_birth_date) : '—';
    const tierGender = item.tier_gender || '—';
    const tierNationality = item.tier_nationality || '—';
    const tierPassportNumber = item.tier_passport_number || '—';
    const tierPassportExpiry = item.tier_passport_expiry_date ? formatDate(item.tier_passport_expiry_date) : '—';
    const tierPhone = item.tier_phone || '—';
    const tierEmail = item.tier_email || '—';
    const tierAddress = item.tier_address || '—';

    return `
        <section class="review-section review-section--tier-info">
            <h4>Informations du tiers (bénéficiaire)</h4>
            <div class="tier-info-notice" style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 0.75rem; margin-bottom: 1rem; border-radius: 4px;">
                <strong>⚠️ Souscription pour un tiers</strong>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Cette souscription concerne un bénéficiaire (tiers) et non le client souscripteur. Les documents produits (attestation, carte santé) concerneront le tiers.</p>
            </div>
            <div class="personal-info-grid">
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.fullName || 'Nom complet')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierFullName)}</strong>
                </div>
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.birthDate || 'Date de naissance')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierBirthDate)}</strong>
                </div>
                ${tierGender !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.gender || 'Genre')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierGender)}</strong>
                </div>
                ` : ''}
                ${tierNationality !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.nationality || 'Nationalité')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierNationality)}</strong>
                </div>
                ` : ''}
                ${tierPassportNumber !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.passportNumber || 'Numéro de passeport')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierPassportNumber)}</strong>
                </div>
                ` : ''}
                ${tierPassportExpiry !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">Date d'expiration du passeport</span>
                    <strong class="personal-info-value">${escapeHtml(tierPassportExpiry)}</strong>
                </div>
                ` : ''}
                ${tierAddress !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.address || 'Adresse')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierAddress)}</strong>
                </div>
                ` : ''}
                ${tierPhone !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.phone || 'Téléphone')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierPhone)}</strong>
                </div>
                ` : ''}
                ${tierEmail !== '—' ? `
                <div class="personal-info-item">
                    <span class="personal-info-label">${escapeHtml(personalFields.email || 'Email')}</span>
                    <strong class="personal-info-value">${escapeHtml(tierEmail)}</strong>
                </div>
                ` : ''}
            </div>
        </section>
        <style>
            .review-section--tier-info {
                background: #fff9e6;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                border: 1px solid #ffc107;
            }
            .review-section--tier-info h4 {
                margin-top: 0;
                margin-bottom: 1rem;
                color: #856404;
                font-size: 1.1rem;
                font-weight: 600;
            }
        </style>
    `;
}

function renderQuestionnairesSection(item) {
    if (reviewContext.type === 'production') {
        return renderProductionQuestionnairesSection(item);
    }
    const keys = reviewContext.config.questionnaireKeys || QUESTIONNAIRE_ORDER;
    const blocks = keys
        .map((key) => renderQuestionnaireBlock(key, item.questionnaires?.[key]))
        .filter(Boolean)
        .join('');

    if (!blocks) {
        return '';
    }

    return `
        <section class="review-section">
            <h4>Questionnaires</h4>
            <div class="questionnaire-grid">
                ${blocks}
            </div>
        </section>
    `;
}

/** Profil agent de production : données médicales = inscription + questionnaire médical */
function renderProductionMedicalSection(item) {
    const maladies = item.client_maladies_chroniques || '';
    const traitements = item.client_traitements_en_cours || '';
    const antecedents = item.client_antecedents_recents || '';
    const grossesse = item.client_grossesse;
    const hasInscription = maladies || traitements || antecedents || (grossesse !== undefined && grossesse !== null);
    const medicalQuest = item.questionnaires?.medical;
    const hasQuest = medicalQuest && hasAnswer(medicalQuest.reponses);

    const inscriptionHtml = hasInscription
        ? `
            <div class="questionnaire-subsection">
                <div class="questionnaire-subsection__header">
                    <h6>Données de l'inscription</h6>
                    <p class="muted">Maladies chroniques, traitements, antécédents et grossesse renseignés à l'inscription.</p>
                </div>
                <div class="question-row"><span class="question-label">Maladies chroniques</span><strong class="question-answer">${escapeHtml(maladies || '—')}</strong></div>
                <div class="question-row"><span class="question-label">Traitements en cours</span><strong class="question-answer">${escapeHtml(traitements || '—')}</strong></div>
                <div class="question-row"><span class="question-label">Antécédents récents (&lt; 6 mois)</span><strong class="question-answer">${escapeHtml(antecedents || '—')}</strong></div>
                <div class="question-row"><span class="question-label">Grossesse (si concernée)</span><strong class="question-answer">${grossesse === true ? 'Oui' : grossesse === false ? 'Non' : '—'}</strong></div>
            </div>`
        : '';
    const questHtml = hasQuest ? renderMedicalQuestionnaire(medicalQuest) : '';

    if (!inscriptionHtml && !questHtml) {
        return '';
    }
    return `
        <section class="review-section">
            <h4>Données médicales</h4>
            <p class="muted" style="margin-bottom: 1rem;">Données de l'inscription complétées par le questionnaire médical.</p>
            <div class="questionnaire-content">
                ${inscriptionHtml}
                ${questHtml ? `<div class="questionnaire-subsection" style="margin-top: 1rem;"><div class="questionnaire-subsection__header"><h6>Questionnaire médical</h6></div>${questHtml}</div>` : ''}
            </div>
        </section>
    `;
}

/** Profil agent de production : questionnaire administratif = Informations civiles puis Informations techniques et engagement */
function renderProductionQuestionnairesSection(item) {
    const adminQuest = item.questionnaires?.administratif;
    const reponses = adminQuest?.reponses || {};
    const personal = reponses.personal || {};
    const technical = reponses.technical || {};

    const civilFields = QUESTION_FIELD_LABELS.administratif?.personal?.fields || {};
    const civilRows = [
        { label: civilFields.fullName || 'Nom complet', value: item.client_name },
        { label: civilFields.birthDate || 'Date de naissance', value: item.client_date_naissance ? formatDate(item.client_date_naissance) : (personal.birthDate != null ? formatAnswer(personal.birthDate) : null) },
        { label: civilFields.gender || 'Genre', value: item.client_sexe || personal.gender },
        { label: civilFields.nationality || 'Nationalité', value: item.client_nationalite || personal.nationality },
        { label: civilFields.passportNumber || 'Numéro de passeport', value: item.client_numero_passeport || personal.passportNumber },
        { label: civilFields.address || 'Adresse', value: personal.address },
        { label: civilFields.phone || 'Téléphone', value: item.client_telephone || personal.phone },
        { label: civilFields.email || 'Email', value: item.client_email || personal.email },
        { label: civilFields.emergencyContact || 'Contact d\'urgence', value: item.client_contact_urgence || personal.emergencyContact },
    ].filter((r) => r.value !== undefined && r.value !== null && r.value !== '');
    const civilHtml = civilRows.length
        ? civilRows.map((r) => `<div class="question-row"><span class="question-label">${escapeHtml(r.label)}</span><strong class="question-answer">${escapeHtml(formatAnswer(r.value))}</strong></div>`).join('')
        : '';

    const techFields = QUESTION_FIELD_LABELS.administratif?.technical?.fields || {};
    const techEntries = Object.entries(technical).filter(([, v]) => hasAnswer(v));
    const techHtml = techEntries.length
        ? techEntries.map(([key, value]) => {
              const label = techFields[key] || key;
              return `<div class="question-row"><span class="question-label">${escapeHtml(label)}</span><strong class="question-answer">${escapeHtml(formatAnswer(value))}</strong></div>`;
          }).join('')
        : '';

    if (!civilHtml && !techHtml) {
        return '';
    }
    const version = adminQuest?.version ? `v${adminQuest.version}` : '';
    return `
        <section class="review-section">
            <h4>Questionnaire administratif</h4>
            <div class="questionnaire-block">
                <div class="questionnaire-header">
                    <h5>Informations civiles</h5>
                    ${version ? `<span class="badge">${version}</span>` : ''}
                </div>
                <div class="questionnaire-content">${civilHtml || '<p class="muted">Aucune donnée.</p>'}</div>
            </div>
            <div class="questionnaire-block" style="margin-top: 1rem;">
                <div class="questionnaire-header">
                    <h5>Informations techniques et engagement</h5>
                </div>
                <div class="questionnaire-content">${techHtml || '<p class="muted">Aucune donnée.</p>'}</div>
            </div>
        </section>
    `;
}

/** Carte compacte pour la liste production (comme validation des inscriptions) */
function renderProductionCompactCard(item) {
    const clientLabel = formatClient(item);
    const productLabel = item.produit_nom || 'Non renseigné';
    const priceLabel = typeof item.prix_applique === 'number' ? `${item.prix_applique.toFixed(2)} €` : '—';
    const travelWindow = item.date_debut && item.date_fin ? `${formatDate(item.date_debut)} → ${formatDate(item.date_fin)}` : '—';
    const createdAt = formatDateTime(item.attestation_created_at);
    const validationStatus = (item.validation_status || 'pending').toLowerCase();
    const statusLabel = validationStatus === 'approved' ? 'Validé' : validationStatus === 'rejected' ? 'Refusé' : 'En attente';
    const statusClass = validationStatus === 'approved' ? 'status-active' : validationStatus === 'rejected' ? 'status-inactive' : 'status-pending';
    return `
        <div class="card review-card production-compact-card" data-attestation-id="${item.attestation_id}" id="review-${item.attestation_id}">
            <div class="card-body">
                <h4 class="card-title">Souscription ${escapeHtml(item.numero_souscription)}</h4>
                <p class="muted">Attestation ${escapeHtml(item.numero_attestation)} • créée le ${createdAt}</p>
                <div class="review-meta" style="margin: 0.75rem 0;">
                    <p><strong>Client:</strong> ${escapeHtml(clientLabel)}</p>
                    <p><strong>Produit:</strong> ${escapeHtml(productLabel)}</p>
                    <p><strong>Prix:</strong> ${priceLabel} <strong>Période:</strong> ${travelWindow}</p>
                </div>
                <span class="pill ${statusClass}" style="font-size: 0.8rem;">${statusLabel}</span>
                <div class="review-card-actions" style="margin-top: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
                    <button type="button" class="btn btn-outline btn-sm" data-production-detail data-attestation-id="${item.attestation_id}">Voir le détail</button>
                    <button type="button" class="btn btn-secondary btn-sm" onclick="openAttestationPdf(${item.attestation_id})">Voir l'attestation</button>
                </div>
            </div>
        </div>
    `;
}

/** Valeur affichable dans le modal (évite JSON brut, base64, etc.) — retourne du HTML échappé. */
function formatModalValue(value) {
    if (value === undefined || value === null) return '—';
    if (typeof value === 'boolean') return value ? 'Oui' : 'Non';
    if (Array.isArray(value)) return escapeHtml(value.map((v) => (typeof v === 'string' ? v : String(v))).join(', '));
    if (typeof value === 'string') {
        const s = value.trim();
        if (!s) return '—';
        if (s.startsWith('data:image') || (s.length > 100 && /^[A-Za-z0-9+/=]+$/.test(s))) return 'Pièce jointe image disponible';
        if (s.length > 300) return escapeHtml(s.slice(0, 300)) + '…';
        return escapeHtml(s);
    }
    if (typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length === 0) return '—';
        if (keys.every((k) => typeof value[k] === 'boolean')) {
            return keys.map((k) => escapeHtml(k) + ': ' + (value[k] ? 'Oui' : 'Non')).join(' ; ');
        }
    }
    return escapeHtml(String(value));
}

/** Retourne true si la valeur est une URL image (data:image ou http(s) vers image) consultable */
function isViewableImageValue(value) {
    if (typeof value === 'string' && value.trim().startsWith('data:image')) return true;
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        const u = value.url || value.src || value.data;
        return typeof u === 'string' && u.trim().startsWith('data:image');
    }
    return false;
}

/** Extrait l'URL image d'une valeur (string data:image ou objet avec url/src/data) */
function getImageDataUrl(value) {
    if (typeof value === 'string' && value.trim().startsWith('data:image')) return value.trim();
    if (typeof value === 'object' && value !== null) {
        const u = value.url || value.src || value.data;
        if (typeof u === 'string' && u.trim().startsWith('data:image')) return u.trim();
    }
    return null;
}

/** HTML pour afficher une pièce jointe image dans le modal (photo affichée, sans lien) */
function renderModalAttachmentHtml(value) {
    const dataUrl = getImageDataUrl(value);
    if (!dataUrl) return escapeHtml('Pièce jointe image disponible');
    const safe = dataUrl.replace(/"/g, '&quot;');
    return `<img src="${safe}" alt="Photo médicale" class="modal-pj-thumbnail" loading="lazy" style="max-width: 100%; border-radius: 8px; display: block;" />`;
}

/** Déplie un objet de type déclaration/consentement en lignes lisibles */
function expandDeclarationRows(obj, fieldLabels) {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) return [];
    return Object.entries(obj)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([key, value]) => {
            const label = (fieldLabels && fieldLabels[key]) || key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase());
            const display = typeof value === 'boolean' ? (value ? 'Oui' : 'Non') : formatModalValue(value);
            return { label, display };
        });
    }

/** Lignes antécédents : une ligne libellé / valeur par entrée (même présentation que première image). */
function productionParseAntecedentsRows(raw) {
    if (!raw || typeof raw !== 'string') return [];
    const lines = raw.trim().split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
    return lines.map((line) => {
        const idx = line.indexOf(': ');
        const label = idx >= 0 ? line.slice(0, idx).trim() : line;
        const value = idx >= 0 ? line.slice(idx + 2).trim() : '—';
        return { label, value };
    });
}

/** Une ligne "Traitement en cours régulier" depuis client_traitements_en_cours. */
function productionParseTraitementRow(value) {
    if (!value || typeof value !== 'string') return null;
    const s = value.trim();
    if (!s) return null;
    const match = s.match(/Traitement médical régulier\s*:\s*(Oui|Non)(.*)/i);
    const val = match ? match[1] + (match[2].trim() ? ' ' + match[2].trim() : '') : s;
    return { label: 'Traitement en cours régulier', value: val };
}

/** Contenu du modal détail (même présentation que validation des inscriptions) */
function renderProductionDetailContent(item) {
    const sectionStyle = 'margin-bottom: 1.25rem; padding-bottom: 1rem; border-bottom: 1px solid #e0e0e0;';
    const titleStyle = 'font-size: 0.9rem; font-weight: 600; color: var(--primary-color, #0d9488); margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.02em;';
    const rowStyle = 'display: flex; justify-content: space-between; align-items: flex-start; padding: 0.5rem 0; border-bottom: 1px solid #eee; gap: 1rem;';
    function detailRow(label, valueHtml) {
        return `<div class="detail-row production-detail-row" style="${rowStyle}"><span class="muted" style="flex-shrink: 0;">${escapeHtml(label)}</span><span style="text-align: right; word-break: break-word;">${valueHtml}</span></div>`;
    }

    const grossesseLabel = item.client_grossesse === true ? 'Oui' : item.client_grossesse === false ? 'Non' : '—';
    const traitRow = productionParseTraitementRow(item.client_traitements_en_cours);
    const antecRows = productionParseAntecedentsRows(item.client_antecedents_recents);
    const donneesMedicalesInscriptionParts = [
        detailRow('Maladies chroniques', formatModalValue(item.client_maladies_chroniques)),
        traitRow ? detailRow(traitRow.label, formatModalValue(traitRow.value)) : detailRow('Traitements en cours', formatModalValue(item.client_traitements_en_cours)),
        ...antecRows.map((r) => detailRow(r.label, formatModalValue(r.value))),
        detailRow('Grossesse (si concernée)', grossesseLabel),
    ];
    const donneesMedicalesInscription = donneesMedicalesInscriptionParts.join('');

    const medicalQuest = item.questionnaires?.medical;
    const medicalReponses = (medicalQuest && medicalQuest.reponses) || {};
    const medicalLabels = { symptoms: 'Maladies ou symptômes récents', symptomOther: 'Autre (précisez)', pregnancy: 'Êtes-vous enceinte ? (si concerné)', surgeryLast6Months: 'Opération chirurgicale dans les 6 derniers mois', surgeryLast6MonthsDetails: 'Précisions opération', photoMedicale: 'Photo médicale' };
    const medicalSkipKeys = new Set(['mode', 'version', 'technicalConsents']);
    const honourDeclarationLabels = { medicalHonesty1: 'Déclaration sur l\'honneur (exactitude)', medicalHonesty2: 'Déclaration sur l\'honneur (documents fournis)' };
    const medicalRows = [];
    for (const [key, value] of Object.entries(medicalReponses)) {
        if (!hasAnswer(value) || medicalSkipKeys.has(key)) continue;
        const label = medicalLabels[key] || key;
        if (key === 'photoMedicale' || isViewableImageValue(value)) {
            medicalRows.push(detailRow(label, renderModalAttachmentHtml(value)));
            continue;
        }
        if (key === 'honourDeclaration' && typeof value === 'object' && !Array.isArray(value)) {
            expandDeclarationRows(value, honourDeclarationLabels).forEach(({ label: l, display }) => medicalRows.push(detailRow(l, escapeHtml(display))));
            continue;
        }
        if (typeof value === 'object' && value !== null && !Array.isArray(value) && key !== 'honourDeclaration') {
            const flat = expandDeclarationRows(value);
            if (flat.length) flat.forEach(({ label: l, display }) => medicalRows.push(detailRow(l, escapeHtml(display))));
            else if (isViewableImageValue(value)) medicalRows.push(detailRow(label, renderModalAttachmentHtml(value)));
            else medicalRows.push(detailRow(label, formatModalValue(value)));
            continue;
        }
        if (isViewableImageValue(value)) {
            medicalRows.push(detailRow(label, renderModalAttachmentHtml(value)));
            continue;
        }
        medicalRows.push(detailRow(label, formatModalValue(value)));
    }
    const donneesMedicalesQuest = medicalRows.join('');

    const civilFields = QUESTION_FIELD_LABELS.administratif?.personal?.fields || {};
    const civilRows = [
        { label: civilFields.fullName || 'Nom complet', value: item.client_name },
        { label: civilFields.birthDate || 'Date de naissance', value: item.client_date_naissance ? formatDate(item.client_date_naissance) : null },
        { label: civilFields.gender || 'Genre', value: item.client_sexe === 'M' ? 'Homme' : item.client_sexe === 'F' ? 'Femme' : item.client_sexe },
        { label: civilFields.nationality || 'Nationalité', value: item.client_nationalite },
        { label: civilFields.passportNumber || 'N° passeport', value: item.client_numero_passeport },
        { label: civilFields.phone || 'Téléphone', value: item.client_telephone },
        { label: civilFields.email || 'Email', value: item.client_email },
        { label: civilFields.emergencyContact || 'Contact d\'urgence', value: item.client_contact_urgence },
    ].filter((r) => r.value !== undefined && r.value !== null && String(r.value).trim() !== '').map((r) => detailRow(r.label, formatModalValue(r.value))).join('');

    const adminQuest = item.questionnaires?.administratif;
    const technical = (adminQuest && adminQuest.reponses && adminQuest.reponses.technical) || {};
    const techFields = QUESTION_FIELD_LABELS.administratif?.technical?.fields || {};
    const techRows = [];
    for (const [key, value] of Object.entries(technical)) {
        if (!hasAnswer(value)) continue;
        const label = techFields[key] || key;
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
            const declLabels = { acceptCG: 'Conditions générales acceptées', acceptExclusions: 'Clauses d\'exclusion acceptées', acceptData: 'Consentement aux traitements de données', honesty1: 'Déclaration sur l\'honneur (exactitude)', honesty2: 'Déclaration sur l\'honneur (documents fournis)' };
            expandDeclarationRows(value, declLabels).forEach(({ label: l, display }) => techRows.push(detailRow(l, escapeHtml(display))));
        } else {
            techRows.push(detailRow(label, formatModalValue(value)));
        }
    }
    const donneesTechniques = techRows.join('');

    const documentsProjet = item.documents_projet_voyage || [];
    const piecesJointesHtml = documentsProjet.length > 0
        ? documentsProjet.map((doc) => {
            const name = escapeHtml(doc.display_name || `Document ${doc.id}`);
            const typeLabel = doc.doc_type ? `<span class="badge" style="font-size: 0.75rem;">${escapeHtml(doc.doc_type)}</span>` : '';
            const sizeLabel = doc.file_size ? ` (${(doc.file_size / 1024).toFixed(1)} Ko)` : '';
            const consultLink = doc.download_url
                ? `<a href="${escapeHtml(doc.download_url)}" class="modal-pj-link">Consulter / Télécharger</a>`
                : '<span class="muted">Lien indisponible</span>';
            return `
                <div class="modal-pj-item" style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #eee; gap: 0.5rem;">
                    <span style="flex: 1; word-break: break-word;">${name}${sizeLabel} ${typeLabel}</span>
                    <span style="flex-shrink: 0;">${consultLink}</span>
                </div>`;
        }).join('')
        : '<p class="muted" style="margin: 0.5rem 0;">Aucune pièce jointe</p>';

    const minorsInfo = item.minors_info || [];
    const minorsSectionHtml = minorsInfo.length > 0
        ? `
        <div class="detail-section production-detail-section production-minors-section" style="${sectionStyle}">
            <h4 class="inscription-modal-section-title" style="${titleStyle}">Enfants mineurs (à charge)</h4>
            <div class="inscription-detail-fields">
                ${minorsInfo.map((m, i) => {
                    const valueStr = [m.nom_complet, m.date_naissance ? `né(e) le ${m.date_naissance}` : ''].filter(Boolean).join(', ') || '—';
                    return detailRow(`Enfant ${i + 1}`, formatModalValue(valueStr));
                }).join('')}
            </div>
        </div>`
        : '';

    let html = `
        <div class="detail-section production-detail-section inscription-modal-section-medical" style="${sectionStyle}">
            <h4 class="inscription-modal-section-title" style="${titleStyle}">Données médicales</h4>
            <p class="muted" style="font-size: 0.85rem; margin-bottom: 0.75rem;">Données de l'inscription complétées par le questionnaire médical.</p>
            <div class="inscription-detail-fields inscription-detail-fields-medical">${donneesMedicalesInscription || detailRow('—', 'Aucune donnée')}</div>
            ${donneesMedicalesQuest ? `<div class="production-questionnaire-medical-block" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #ccfbf1;"><h5 class="inscription-medical-block-title" style="font-size: 0.85rem; font-weight: 600; color: #0f766e; margin-bottom: 0.5rem;">Questionnaire médical</h5><div class="inscription-detail-fields">${donneesMedicalesQuest}</div></div>` : ''}
        </div>
        <div class="detail-section production-detail-section" style="${sectionStyle}">
            <h4 class="inscription-modal-section-title" style="${titleStyle}">Questionnaire administratif – Informations civiles</h4>
            <div class="inscription-detail-fields">${civilRows || detailRow('—', 'Aucune donnée')}</div>
        </div>
        ${minorsSectionHtml}
        <div class="detail-section production-detail-section" style="${sectionStyle}">
            <h4 class="inscription-modal-section-title" style="${titleStyle}">Informations techniques et engagement</h4>
            <div class="inscription-detail-fields">${donneesTechniques || detailRow('—', 'Aucune donnée')}</div>
        </div>
        <div class="detail-section production-detail-section" style="${sectionStyle}">
            <h4 class="inscription-modal-section-title" style="${titleStyle}">Pièces jointes</h4>
            <p class="muted" style="font-size: 0.85rem; margin-bottom: 0.5rem;">Documents du projet de voyage. Cliquez sur le lien pour consulter ou télécharger.</p>
            <div class="modal-pj-list">${piecesJointesHtml}</div>
        </div>
    `;
    return html;
}

function openProductionDetailModal(attestationId) {
    const items = window._productionReviewItems;
    if (!items || !items.length) return;
    const item = items.find((i) => i.attestation_id === attestationId);
    if (!item) return;
    const overlay = document.getElementById('productionDetailOverlay');
    const modal = document.getElementById('productionDetailModal');
    const body = document.getElementById('productionDetailBody');
    const actions = document.getElementById('productionDetailActions');
    const titleEl = document.getElementById('productionDetailTitle');
    if (!overlay || !modal || !body || !actions) return;
    titleEl.textContent = `Détail – Souscription ${item.numero_souscription}`;
    body.innerHTML = renderProductionDetailContent(item);
    const validationStatus = (item.validation_status || 'pending').toLowerCase();
    const isPending = validationStatus === 'pending';
    actions.innerHTML = `
        <button type="button" class="btn btn-secondary btn-sm" id="productionDetailCloseBtn">Fermer</button>
        <button type="button" class="btn btn-outline btn-sm" onclick="openAttestationPdf(${item.attestation_id}); window.closeProductionDetailModal && closeProductionDetailModal();">Voir l'attestation</button>
        ${isPending ? `
            <textarea id="productionDetailComment" rows="2" placeholder="Commentaire (obligatoire en cas de refus)" style="width: 100%; margin: 0.5rem 0;"></textarea>
            <button type="button" class="btn btn-danger btn-sm" id="productionDetailRejectBtn" data-attestation-id="${item.attestation_id}">Refuser</button>
            <button type="button" class="btn btn-success btn-sm" id="productionDetailApproveBtn" data-attestation-id="${item.attestation_id}">Approuver</button>
        ` : ''}
    `;
    document.getElementById('productionDetailCloseBtn').onclick = closeProductionDetailModal;
    if (isPending) {
        document.getElementById('productionDetailRejectBtn').onclick = async () => {
            const comment = document.getElementById('productionDetailComment')?.value?.trim();
            if (!comment) {
                if (typeof showAlert === 'function') showAlert('Merci de préciser un commentaire en cas de refus.', 'error');
                return;
            }
            const attId = item.attestation_id;
            closeProductionDetailModal();
            await submitProductionDecisionFromModal(attId, false, comment);
        };
        document.getElementById('productionDetailApproveBtn').onclick = async () => {
            const attId = item.attestation_id;
            closeProductionDetailModal();
            await submitProductionDecisionFromModal(attId, true, null);
        };
    }
    overlay.hidden = false;
    overlay.style.display = 'flex';
    if (modal) {
        modal.hidden = false;
        modal.style.display = '';
    }
}

async function submitProductionDecisionFromModal(attestationId, approved, comment) {
    const submitBtn = approved
        ? document.getElementById('productionDetailApproveBtn')
        : document.getElementById('productionDetailRejectBtn');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';
    }
    try {
        await attestationsAPI.createValidation(attestationId, {
            type_validation: 'production',
            est_valide: approved,
            commentaires: comment || null,
        });
        if (typeof showAlert === 'function') showAlert('Avis enregistré avec succès.', 'success');
        await loadReviewItems();
    } catch (error) {
        if (typeof showAlert === 'function') showAlert(error.message || 'Impossible d\'enregistrer la validation.', 'error');
    } finally {
        closeProductionDetailModal();
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = approved ? 'Approuver' : 'Refuser';
        }
    }
}

function closeProductionDetailModal() {
    const overlay = document.getElementById('productionDetailOverlay');
    const modal = document.getElementById('productionDetailModal');
    if (overlay) {
        overlay.hidden = true;
        overlay.style.display = 'none';
    }
    if (modal) {
        modal.hidden = true;
        modal.style.display = 'none';
    }
}
window.closeProductionDetailModal = closeProductionDetailModal;

function renderQuestionnaireBlock(key, questionnaire) {
    const label = QUESTIONNAIRE_LABELS[key] || `Questionnaire ${key}`;
    if (!questionnaire || !hasAnswer(questionnaire.reponses)) {
        return '';
    }

    const entries = Object.entries(questionnaire.reponses || {});

    const questionnaireContent =
        key === 'medical'
            ? renderMedicalQuestionnaire(questionnaire)
            : entries
                  .slice(0, 6)
                  .map(([question, answer]) => renderQuestionAnswerRow(key, question, answer))
                  .join('');

    return `
        <div class="questionnaire-block">
            <div class="questionnaire-header">
                <h5>${label}</h5>
                <span class="badge">v${questionnaire.version}</span>
            </div>
            <div class="questionnaire-content">
                ${questionnaireContent || '<p class="muted">Aucune réponse renseignée.</p>'}
            </div>
        </div>
    `;
}

function renderValidationSection(item) {
    if (!item.validations) {
        return '';
    }

    const phases = ['medecin', 'production'];
    const chips = phases
        .map((phase) => {
            const state = item.validations[phase];
            const meta = STATUS_META[state?.status] || STATUS_META.pending;
            const notes = state?.notes ? `<small>${escapeHtml(state.notes)}</small>` : '';
            return `
                <div class="validation-chip ${meta.className}">
                    <strong>${VALIDATION_LABELS[phase]}</strong>
                    <span>${meta.label}</span>
                    ${notes}
                </div>
            `;
        })
        .join('');

    return `
        <section class="review-section">
            <h4>Statut des validations</h4>
            <div class="validation-grid">
                ${chips}
            </div>
        </section>
    `;
}

function renderIAAnalysisSection(item) {
    // Afficher uniquement pour l'agent de production
    if (reviewContext.type !== 'production') {
        return '';
    }

    const subscriptionId = item.souscription_id || item.subscription_id;
    if (!subscriptionId) {
        return '';
    }

    // Créer un conteneur avec un ID unique pour charger le rapport IA
    const containerId = `ia-analysis-${item.attestation_id}`;
    
    return `
        <section class="review-section" id="${containerId}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h4>Rapport d'analyse IA</h4>
                <button 
                    class="btn btn-outline btn-sm" 
                    onclick="loadIAAnalysis(${subscriptionId}, '${containerId}')"
                    id="load-ia-btn-${item.attestation_id}"
                >
                    Charger le rapport
                </button>
            </div>
            <div id="ia-content-${item.attestation_id}" class="ia-analysis-content">
                <div class="alert alert-info">
                    <p>Le rapport d'analyse IA sera chargé automatiquement. Cliquez sur "Charger le rapport" pour l'afficher.</p>
                </div>
            </div>
        </section>
    `;
}

// Exposer la fonction globalement pour les onclick
window.loadIAAnalysis = async function loadIAAnalysis(subscriptionId, containerId) {
    const contentDiv = document.getElementById(containerId.replace('ia-analysis-', 'ia-content-'));
    const loadBtn = document.querySelector(`[onclick*="loadIAAnalysis(${subscriptionId}"]`);
    
    if (!contentDiv) {
        console.error('Conteneur IA non trouvé');
        return;
    }

    // Afficher le chargement
    contentDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Chargement du rapport IA...</div>';
    if (loadBtn) {
        loadBtn.disabled = true;
        loadBtn.textContent = 'Chargement...';
    }

    try {
        const response = await apiCall(`/ia/souscriptions/${subscriptionId}/analyse`);
        
        if (!response.success || !response.data) {
            contentDiv.innerHTML = `
                <div class="alert alert-warning">
                    <p>Aucun rapport d'analyse IA disponible pour cette souscription.</p>
                    <p class="muted">L'analyse IA peut être en cours de traitement ou les documents n'ont pas encore été analysés.</p>
                </div>
            `;
            return;
        }

        const data = response.data;
        contentDiv.innerHTML = renderIAAnalysisContent(data);
        
        if (loadBtn) {
            loadBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Erreur lors du chargement du rapport IA:', error);
        contentDiv.innerHTML = `
            <div class="alert alert-error">
                <p><strong>Erreur lors du chargement du rapport IA</strong></p>
                <p class="muted">${escapeHtml(error.message || 'Erreur inconnue')}</p>
                <button class="btn btn-outline btn-sm" onclick="loadIAAnalysis(${subscriptionId}, '${containerId}')" style="margin-top: 0.5rem;">
                    Réessayer
                </button>
            </div>
        `;
        if (loadBtn) {
            loadBtn.disabled = false;
            loadBtn.textContent = 'Charger le rapport';
        }
    }
}

function renderIAAnalysisContent(data) {
    const scores = data.scores || {};
    const evaluation = data.evaluation || {};
    const documents = data.documents_analyses || [];
    
    // Déterminer la classe CSS selon l'avis
    const avisClass = getAvisClass(evaluation.avis);
    const avisLabel = evaluation.avis || 'Non déterminé';
    
    // Formater les pourcentages
    const probAcceptation = (scores.probabilite_acceptation * 100).toFixed(1);
    const probFraude = (scores.probabilite_fraude * 100).toFixed(1);
    const probConfiance = (scores.probabilite_confiance_assureur * 100).toFixed(1);
    const scoreCoherence = scores.score_coherence?.toFixed(1) || 'N/A';
    const scoreRisque = scores.score_risque?.toFixed(1) || 'N/A';
    const scoreConfiance = scores.score_confiance?.toFixed(1) || 'N/A';
    
    // Signaux de fraude
    const signauxFraude = evaluation.signaux_fraude || [];
    const facteursRisque = evaluation.facteurs_risque || [];
    const incoherences = evaluation.incoherences || [];
    
    // Documents analysés
    const documentsHtml = documents.length > 0
        ? documents.map(doc => `
            <div class="ia-document-item">
                <div class="ia-document-header">
                    <strong>${escapeHtml(doc.nom_fichier || 'Document')}</strong>
                    ${doc.type_document ? `<span class="badge">${escapeHtml(doc.type_document)}</span>` : ''}
                </div>
                <div class="ia-document-details">
                    ${doc.confiance_ocr !== null ? `<span>Confiance OCR: ${doc.confiance_ocr > 1 ? doc.confiance_ocr.toFixed(1) : (doc.confiance_ocr * 100).toFixed(1)}%</span>` : ''}
                    ${doc.est_expire ? '<span class="badge badge-danger">Expiré</span>' : '<span class="badge badge-success">Valide</span>'}
                    ${doc.qualite_ok ? '<span class="badge badge-success">Qualité OK</span>' : '<span class="badge badge-warning">Qualité faible</span>'}
                    ${doc.est_complet ? '<span class="badge badge-success">Complet</span>' : '<span class="badge badge-warning">Incomplet</span>'}
                    ${doc.est_coherent ? '<span class="badge badge-success">Cohérent</span>' : '<span class="badge badge-danger">Incohérent</span>'}
                </div>
            </div>
        `).join('')
        : '<p class="muted">Aucun document analysé</p>';
    
    return `
        <div class="ia-analysis-report">
            <!-- Résumé exécutif -->
            <div class="ia-summary">
                <div class="ia-avis ${avisClass}">
                    <h5>Avis IA</h5>
                    <div class="ia-avis-value">${escapeHtml(avisLabel)}</div>
                    ${evaluation.message_ia ? `<p class="ia-message">${escapeHtml(evaluation.message_ia)}</p>` : ''}
                </div>
                
                <div class="ia-scores-grid">
                    <div class="ia-score-item">
                        <div class="ia-score-label">Probabilité d'acceptation</div>
                        <div class="ia-score-value ${getScoreClass(scores.probabilite_acceptation, true)}">
                            ${probAcceptation}%
                        </div>
                    </div>
                    <div class="ia-score-item">
                        <div class="ia-score-label">Probabilité de fraude</div>
                        <div class="ia-score-value ${getScoreClass(scores.probabilite_fraude, false)}">
                            ${probFraude}%
                        </div>
                    </div>
                    <div class="ia-score-item">
                        <div class="ia-score-label">Confiance assureur</div>
                        <div class="ia-score-value ${getScoreClass(scores.probabilite_confiance_assureur, true)}">
                            ${probConfiance}%
                        </div>
                    </div>
                    <div class="ia-score-item">
                        <div class="ia-score-label">Score cohérence</div>
                        <div class="ia-score-value">${scoreCoherence}/100</div>
                    </div>
                    <div class="ia-score-item">
                        <div class="ia-score-label">Score risque</div>
                        <div class="ia-score-value ${getScoreClass(scores.score_risque, false)}">
                            ${scoreRisque}/100
                        </div>
                    </div>
                    <div class="ia-score-item">
                        <div class="ia-score-label">Score confiance</div>
                        <div class="ia-score-value">${scoreConfiance}/100</div>
                    </div>
                </div>
            </div>
            
            <!-- Signaux d'alerte -->
            ${signauxFraude.length > 0 || facteursRisque.length > 0 || incoherences.length > 0 ? `
                <div class="ia-alerts">
                    ${signauxFraude.length > 0 ? `
                        <div class="ia-alert-section">
                            <h6><span class="icon">⚠️</span> Signaux de fraude détectés</h6>
                            <ul class="ia-alert-list">
                                ${signauxFraude.map(signal => `<li>${escapeHtml(signal)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${facteursRisque.length > 0 ? `
                        <div class="ia-alert-section">
                            <h6><span class="icon">🔍</span> Facteurs de risque</h6>
                            <ul class="ia-alert-list">
                                ${facteursRisque.map(facteur => `<li>${escapeHtml(facteur)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${incoherences.length > 0 ? `
                        <div class="ia-alert-section">
                            <h6><span class="icon">🚨</span> Incohérences détectées</h6>
                            <ul class="ia-alert-list">
                                ${incoherences.map(incoh => `<li>${escapeHtml(incoh)}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            ` : `
                <div class="alert alert-success">
                    <p>✅ Aucun signal d'alerte détecté. Les documents sont cohérents et valides.</p>
                </div>
            `}
            
            <!-- Documents analysés -->
            <div class="ia-documents">
                <h6>Documents analysés (${documents.length})</h6>
                <div class="ia-documents-list">
                    ${documentsHtml}
                </div>
            </div>
            
            <!-- Métadonnées -->
            <div class="ia-metadata">
                <small class="muted">
                    Analyse effectuée le ${formatDateTime(data.date_analyse)} • 
                    Demande ID: ${escapeHtml(data.demande_id || 'N/A')}
                </small>
            </div>
        </div>
        
        <style>
            .ia-analysis-content {
                margin-top: 1rem;
            }
            .ia-analysis-report {
                background: var(--light-bg, #f8f9fa);
                border-radius: 8px;
                padding: 1.5rem;
                border: 1px solid var(--border-color, #dee2e6);
            }
            .ia-summary {
                margin-bottom: 1.5rem;
            }
            .ia-avis {
                text-align: center;
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1.5rem;
                background: white;
            }
            .ia-avis.favorable {
                background: #d4edda;
                border: 2px solid #28a745;
            }
            .ia-avis.reserve {
                background: #fff3cd;
                border: 2px solid #ffc107;
            }
            .ia-avis.defavorable {
                background: #f8d7da;
                border: 2px solid #dc3545;
            }
            .ia-avis-value {
                font-size: 1.5rem;
                font-weight: bold;
                margin: 0.5rem 0;
            }
            .ia-message {
                margin-top: 0.5rem;
                font-size: 0.9rem;
                color: var(--dark-text, #333);
            }
            .ia-scores-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 1rem;
            }
            .ia-score-item {
                background: white;
                padding: 1rem;
                border-radius: 6px;
                text-align: center;
                border: 1px solid var(--border-color, #dee2e6);
            }
            .ia-score-label {
                font-size: 0.85rem;
                color: var(--muted-text, #6c757d);
                margin-bottom: 0.5rem;
            }
            .ia-score-value {
                font-size: 1.25rem;
                font-weight: bold;
            }
            .ia-score-value.score-high {
                color: #28a745;
            }
            .ia-score-value.score-medium {
                color: #ffc107;
            }
            .ia-score-value.score-low {
                color: #dc3545;
            }
            .ia-alerts {
                margin: 1.5rem 0;
            }
            .ia-alert-section {
                background: white;
                padding: 1rem;
                border-radius: 6px;
                margin-bottom: 1rem;
                border-left: 4px solid #dc3545;
            }
            .ia-alert-section h6 {
                margin: 0 0 0.75rem 0;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .ia-alert-list {
                margin: 0;
                padding-left: 1.5rem;
            }
            .ia-alert-list li {
                margin-bottom: 0.5rem;
            }
            .ia-documents {
                margin-top: 1.5rem;
            }
            .ia-documents h6 {
                margin-bottom: 1rem;
            }
            .ia-documents-list {
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
            }
            .ia-document-item {
                background: white;
                padding: 1rem;
                border-radius: 6px;
                border: 1px solid var(--border-color, #dee2e6);
            }
            .ia-document-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.5rem;
            }
            .ia-document-details {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                font-size: 0.85rem;
            }
            .ia-metadata {
                margin-top: 1rem;
                padding-top: 1rem;
                border-top: 1px solid var(--border-color, #dee2e6);
            }
            .badge-danger {
                background: #dc3545;
                color: white;
            }
            .badge-success {
                background: #28a745;
                color: white;
            }
            .badge-warning {
                background: #ffc107;
                color: #000;
            }
        </style>
    `;
}

function getAvisClass(avis) {
    if (!avis) return '';
    const avisLower = avis.toLowerCase();
    if (avisLower.includes('favorable') || avisLower.includes('approve')) {
        return 'favorable';
    }
    if (avisLower.includes('reserve') || avisLower.includes('réservé')) {
        return 'reserve';
    }
    if (avisLower.includes('defavorable') || avisLower.includes('défavorable') || avisLower.includes('rejet')) {
        return 'defavorable';
    }
    return '';
}

function getScoreClass(score, isPositive) {
    if (score === null || score === undefined) return '';
    const percentage = score * 100;
    if (isPositive) {
        // Pour probabilité d'acceptation : plus c'est haut, mieux c'est
        if (percentage >= 70) return 'score-high';
        if (percentage >= 40) return 'score-medium';
        return 'score-low';
    } else {
        // Pour probabilité de fraude : plus c'est bas, mieux c'est
        if (percentage <= 20) return 'score-high';
        if (percentage <= 50) return 'score-medium';
        return 'score-low';
    }
}

function formatClient(item) {
    if (!item.client_name && !item.client_email) {
        return 'Non renseigné';
    }
    if (item.client_name && item.client_email) {
        return `${item.client_name} (${item.client_email})`;
    }
    return item.client_name || item.client_email;
}

function formatDate(value) {
    if (!value) {
        return '—';
    }
    return new Date(value).toLocaleDateString('fr-FR');
}

function formatDateTime(value) {
    if (!value) {
        return '—';
    }
    return new Date(value).toLocaleString('fr-FR');
}

function formatAnswer(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    if (typeof value === 'boolean') {
        return value ? 'Oui' : 'Non';
    }
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        if (!normalized) {
            return '—';
        }
        if (normalized === 'oui') {
            return 'Oui';
        }
        if (normalized === 'non') {
            return 'Non';
        }
        return value;
    }
    if (Array.isArray(value)) {
        if (!value.length) {
            return '—';
        }
        return value.map((entry) => formatAnswer(entry)).join(', ');
    }
    if (typeof value === 'object') {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
}

function isEmbeddedImage(value) {
    if (typeof value === 'string') {
        return /^data:image\/[a-z0-9+.-]+;base64,/i.test(value.trim());
    }
    if (value && typeof value === 'object' && typeof value.dataUrl === 'string') {
        return /^data:image\/[a-z0-9+.-]+;base64,/i.test(value.dataUrl.trim());
    }
    return false;
}

function renderMediaPlaceholderRow(label) {
    return `
        <div class="question-row">
            <span class="question-label">${escapeHtml(label)}</span>
            <span class="question-answer question-answer--muted">Pièce jointe image disponible</span>
        </div>
    `;
}

function renderQuestionAnswerRow(questionnaireType, question, answer) {
    const questionLabel = resolveQuestionLabel(questionnaireType, question) || question;
    if (isEmbeddedImage(answer)) {
        return renderMediaPlaceholderRow(questionLabel);
    }
    if (answer && typeof answer === 'object' && !Array.isArray(answer)) {
        const nestedEntries = Object.entries(answer);
        const nestedRows = nestedEntries.length
            ? nestedEntries
                  .map(
                      ([key, value]) => `
                    <div class="answer-row">
                        <span class="answer-key">${escapeHtml(resolveQuestionLabel(questionnaireType, question, key) || key)}</span>
                        <span class="answer-value">
                            ${
                                isEmbeddedImage(value)
                                    ? 'Pièce jointe image disponible'
                                    : escapeHtml(formatAnswer(value))
                            }
                        </span>
                    </div>
                `,
                  )
                  .join('')
            : '<span class="muted">Aucune donnée détaillée.</span>';

        return `
            <div class="question-row question-row--nested">
                <span class="question-label">${escapeHtml(questionLabel)}</span>
                <div class="question-answer question-answer--nested">
                    ${nestedRows}
                </div>
            </div>
        `;
    }

    if (Array.isArray(answer)) {
        const listItems = answer.length
            ? answer
                  .map(
                      (value) => `
                    <li>${escapeHtml(formatAnswer(value))}</li>
                `,
                  )
                  .join('')
            : '<li class="muted">Aucune donnée</li>';

        return `
            <div class="question-row question-row--nested">
                <span class="question-label">${escapeHtml(questionLabel)}</span>
                <div class="question-answer question-answer--list">
                    <ul>${listItems}</ul>
                </div>
            </div>
        `;
    }

    return `
        <div class="question-row">
            <span class="question-label">${escapeHtml(questionLabel)}</span>
            <strong class="question-answer">${escapeHtml(formatAnswer(answer))}</strong>
        </div>
    `;
}

function renderMedicalQuestionnaire(questionnaire) {
    const responses = questionnaire.reponses || {};
    
    // Rendre les sections définies
    const sections = MEDICAL_SECTIONS.map((section) => {
        const sectionRows = section.fields
            .map((fieldKey) => {
                const value = getResponseValue(responses, fieldKey);
                return renderMedicalField(fieldKey, value);
            })
            .filter(Boolean)
            .join('');

        if (!sectionRows) {
            return '';
        }

        return `
            <div class="questionnaire-subsection">
                <div class="questionnaire-subsection__header">
                    <h6>${section.label}</h6>
                    ${section.description ? `<p>${section.description}</p>` : ''}
                </div>
                ${sectionRows}
            </div>
        `;
    }).filter(Boolean);

    // Si aucune section n'a été rendue, afficher toutes les données disponibles (fallback)
    if (sections.length === 0 && responses && Object.keys(responses).length > 0) {
        const allRows = Object.entries(responses)
            .map(([key, value]) => {
                if (hasAnswer(value)) {
                    return renderMedicalField(key, value);
                }
                return null;
            })
            .filter(Boolean)
            .join('');
        
        if (allRows) {
            return `
                <div class="questionnaire-subsection">
                    <div class="questionnaire-subsection__header">
                        <h6>Questionnaire médical</h6>
                    </div>
                    ${allRows}
                </div>
            `;
        }
    }

    return sections.length ? sections.join('') : '<p class="muted">Aucune réponse renseignée.</p>';
}

function renderMedicalField(fieldKey, value) {
    const label = resolveQuestionLabel('medical', fieldKey) || fieldKey;

    if (!hasAnswer(value)) {
        return `
            <div class="question-row">
                <span class="question-label">${escapeHtml(label)}</span>
                <span class="question-answer question-answer--muted">—</span>
            </div>
        `;
    }

    if (Array.isArray(value)) {
        return `
            <div class="question-row question-row--nested">
                <span class="question-label">${escapeHtml(label)}</span>
                ${renderPillList(value)}
            </div>
        `;
    }

    if (isEmbeddedImage(value)) {
        return renderMediaPlaceholderRow(label);
    }

    if (typeof value === 'object') {
        return renderQuestionAnswerRow('medical', fieldKey, value);
    }

    return `
        <div class="question-row">
            <span class="question-label">${escapeHtml(label)}</span>
            <strong class="question-answer">${escapeHtml(formatAnswer(value))}</strong>
        </div>
    `;
}

function renderPillList(values) {
    const pills = values
        .filter((entry) => hasAnswer(entry))
        .map((entry) => `<span class="questionnaire-pill">${escapeHtml(formatAnswer(entry))}</span>`)
        .join('');

    return pills
        ? `<div class="questionnaire-pill-list">${pills}</div>`
        : '<div class="questionnaire-pill-list"><span class="muted">Aucune donnée</span></div>';
}

function hasAnswer(value) {
    if (value === null || value === undefined) {
        return false;
    }
    if (typeof value === 'string') {
        return value.trim() !== '';
    }
    if (typeof value === 'boolean' || typeof value === 'number') {
        return true;
    }
    if (Array.isArray(value)) {
        return value.some((entry) => hasAnswer(entry));
    }
    if (typeof value === 'object') {
        return Object.keys(value).length > 0;
    }
    return true;
}

// Mapping de compatibilité pour les anciennes clés vers les nouvelles
const MEDICAL_KEY_ALIASES = {
    'chronicDiseases': ['symptoms', 'maladies_chroniques'],
    'regularTreatment': ['traitement_medical'],
    'treatmentDetails': ['traitement_medical_details'],
    'recentHospitalization': ['hospitalisation_12mois'],
    'hospitalizationDetails': ['hospitalisation_12mois_details'],
    'recentSurgery': ['operation_5ans'],
    'surgeryDetails': ['operation_5ans_details'],
    'infectiousDiseases': ['maladies_contagieuses'],
    'contactRisk': ['contact_personne_malade'],
};

function getResponseValue(responses, targetKey, depth = 0) {
    if (!responses || typeof responses !== 'object' || depth > 4) {
        return undefined;
    }

    const normalizedTarget = normalizeKey(targetKey);
    
    // Chercher d'abord la clé exacte
    for (const [key, value] of Object.entries(responses)) {
        if (normalizeKey(key) === normalizedTarget) {
            return value;
        }
    }
    
    // Si pas trouvé, chercher dans les alias (compatibilité avec anciennes données)
    const aliases = MEDICAL_KEY_ALIASES[targetKey] || [];
    for (const alias of aliases) {
        const normalizedAlias = normalizeKey(alias);
        for (const [key, value] of Object.entries(responses)) {
            if (normalizeKey(key) === normalizedAlias) {
                return value;
            }
        }
    }

    // Chercher récursivement dans les objets imbriqués
    for (const value of Object.values(responses)) {
        if (value && typeof value === 'object' && !Array.isArray(value)) {
            const nested = getResponseValue(value, targetKey, depth + 1);
            if (nested !== undefined) {
                return nested;
            }
        }
    }

    return undefined;
}

function normalizeKey(key) {
    return String(key)
        .toLowerCase()
        .replace(/[_\s-]+/g, '')
        .replace(/([a-z])(?=[A-Z])/g, '$1')
        .replace(/[^a-z0-9]/g, '');
}

function resolveQuestionLabel(questionnaireType, questionKey, nestedKey) {
    const typeConfig = QUESTION_FIELD_LABELS[questionnaireType];
    if (!typeConfig) {
        return null;
    }

    const fieldConfig = typeConfig[questionKey];
    if (!fieldConfig) {
        return null;
    }

    if (nestedKey) {
        if (fieldConfig.fields && fieldConfig.fields[nestedKey]) {
            return fieldConfig.fields[nestedKey];
        }
        return null;
    }

    if (typeof fieldConfig === 'string') {
        return fieldConfig;
    }

    return fieldConfig.label || null;
}

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatMedicalNotificationMessage(message) {
    if (!message || typeof message !== 'string') {
        return '<p class="muted">Aucun message</p>';
    }
    
    // Supprimer la section "--- Extrait du questionnaire ---" et tout ce qui suit
    const excerptIndex = message.indexOf('--- Extrait du questionnaire ---');
    if (excerptIndex !== -1) {
        message = message.substring(0, excerptIndex).trim();
    }
    
    // Supprimer aussi les variantes possibles
    message = message.replace(/---\s*Extrait du questionnaire\s*---.*$/s, '').trim();
    message = message.replace(/Extrait du questionnaire.*$/s, '').trim();
    
    // Échapper le HTML d'abord
    let formatted = escapeHtml(message);
    
    // Mettre en forme les sections avec des titres (doit être fait avant les sauts de ligne)
    formatted = formatted.replace(/(📋|📄|🔍|⚠️|🚨|🚑|💼)\s*([^\n]+)/g, '<div class="notification-section-title"><span class="notification-section-icon">$1</span><span>$2</span></div>');
    
    // Mettre en forme les listes à puces (doit être fait avant les sauts de ligne)
    const lines = formatted.split('\n');
    let inList = false;
    let result = [];
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Détecter le début d'une liste
        if (line.startsWith('•')) {
            if (!inList) {
                result.push('<ul class="notification-list">');
                inList = true;
            }
            const content = line.replace(/^•\s*/, '');
            // Extraire les paires clé-valeur pour un meilleur formatage
            const kvMatch = content.match(/^([^:]+):\s*(.+)$/);
            if (kvMatch) {
                result.push(`<li class="notification-list-item"><span class="notification-list-key">${kvMatch[1]}:</span> <span class="notification-list-value">${kvMatch[2]}</span></li>`);
            } else {
                result.push(`<li class="notification-list-item">${content}</li>`);
            }
        } else {
            // Fermer la liste si nécessaire
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            
            // Traiter les lignes normales
            if (line) {
                // Mettre en évidence les labels importants avec un meilleur formatage
                const enhanced = line.replace(/(Priorité|Adresse|Assuré|Dossier médical|Informations médicales|version|Alerte|Sinistre|Facture|Rapport|Hôpital|Montant|Médecin):/g, '<span class="notification-label">$1:</span>');
                // Détecter les valeurs importantes (numéros, montants)
                const withValues = enhanced.replace(/(#[A-Z0-9-]+|[\d,]+\.?\d*\s*€)/g, '<span class="notification-value">$1</span>');
                result.push(`<p class="notification-line">${withValues}</p>`);
            } else if (i < lines.length - 1) {
                // Ligne vide entre sections
                result.push('<div class="notification-spacer"></div>');
            }
        }
    }
    
    // Fermer la liste si elle est encore ouverte
    if (inList) {
        result.push('</ul>');
    }
    
    formatted = result.join('');
    
    return formatted;
}

function formatKeyLabel(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

async function submitReviewDecision(attestationId) {
    const decisionInput = document.querySelector(`input[name="decision-${attestationId}"]:checked`);
    if (!decisionInput) {
        showAlert('Veuillez sélectionner une décision.', 'error');
        return;
    }

    const commentField = document.getElementById(`comment-${attestationId}`);
    const comment = (commentField?.value || '').trim();

    if (decisionInput.value === 'reject' && !comment) {
        showAlert('Merci de préciser un commentaire en cas de refus.', 'error');
        return;
    }

    const submitBtn = document.getElementById(`submit-${attestationId}`);
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enregistrement...';
    }

    try {
        await attestationsAPI.createValidation(attestationId, {
            type_validation: reviewContext.type,
            est_valide: decisionInput.value === 'approve',
            commentaires: comment || null,
        });

        showAlert('Avis enregistré avec succès.', 'success');
        await loadReviewItems();
    } catch (error) {
        showAlert(error.message || 'Impossible d’enregistrer la validation.', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enregistrer l\'avis';
        }
    }
}

async function openAttestationPdf(attestationId) {
    try {
        const attestation = await attestationsAPI.getWithUrl(attestationId);
        window.location.href = attestation.url_signee;
    } catch (error) {
        showAlert(error.message || 'Impossible d’ouvrir l’attestation.', 'error');
    }
}

function initAlertValidationModule() {
    const section = document.getElementById('alertValidationSection');
    if (!section || reviewContext.type !== 'medecin') {
        return;
    }

    const userRole = (localStorage.getItem('user_role') || '').toLowerCase();
    if (!ALERT_VALIDATION_ALLOWED_ROLES.has(userRole)) {
        section.style.display = 'none';
        return;
    }

    alertValidationState.enabled = true;
    alertValidationState.elements = {
        section,
        table: document.getElementById('alertValidationTable'),
        body: document.getElementById('alertValidationTableBody'),
        emptyState: document.getElementById('alertValidationEmpty'),
        emptyMessage: document.getElementById('alertValidationEmptyMessage'),
        loading: document.getElementById('alertValidationLoading'),
        error: document.getElementById('alertValidationError'),
        refreshButton: document.getElementById('refreshAlertValidationBtn'),
        searchInput: document.getElementById('alertValidationSearchInput'),
        tabButtons: {
            sinistre: document.getElementById('tabSinistre'),
            sinistre_valide: document.getElementById('tabSinistreValide'),
            rapport: document.getElementById('tabRapport'),
            rapport_valide: document.getElementById('tabRapportValide'),
            facture: document.getElementById('tabFacture'),
            facture_valide: document.getElementById('tabFactureValide'),
            resolu: document.getElementById('tabResolu'),
        },
        tabCounts: {
            sinistre: document.getElementById('tabCountSinistre'),
            sinistre_valide: document.getElementById('tabCountSinistreValide'),
            rapport: document.getElementById('tabCountRapport'),
            rapport_valide: document.getElementById('tabCountRapportValide'),
            facture: document.getElementById('tabCountFacture'),
            facture_valide: document.getElementById('tabCountFactureValide'),
            resolu: document.getElementById('tabCountResolu'),
        },
    };

    if (alertValidationState.elements.body) {
        alertValidationState.elements.body.addEventListener('click', handleAlertValidationTableClick);
    }
    if (alertValidationState.elements.refreshButton) {
        alertValidationState.elements.refreshButton.addEventListener('click', () => loadAlertValidationItems(true));
    }
    REFERENT_STEP_KEYS.forEach((tabKey) => {
        const btn = alertValidationState.elements.tabButtons && alertValidationState.elements.tabButtons[tabKey];
        if (btn) {
            btn.addEventListener('click', () => setReferentTab(tabKey));
        }
    });
    if (alertValidationState.elements.searchInput) {
        let searchTimer = null;
        alertValidationState.elements.searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                filterAlertValidationRows(e.target.value.trim());
            }, 300);
        });
        alertValidationState.elements.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.target.value = '';
                filterAlertValidationRows('');
            }
        });
    }

    // Appliquer l'onglet depuis l'URL après le chargement des données (voir loadAlertValidationItems)
    alertValidationState.tabFromUrl = (() => {
        const urlParams = new URLSearchParams(window.location.search);
        const tab = urlParams.get('tab');
        return tab && REFERENT_STEP_KEYS.includes(tab) ? tab : null;
    })();

    // Rafraîchir la liste quand l'utilisateur revient sur l'onglet (données à jour)
    let visibilityRefreshTimer = null;
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState !== 'visible' || !alertValidationState.enabled) return;
        clearTimeout(visibilityRefreshTimer);
        visibilityRefreshTimer = setTimeout(() => loadAlertValidationItems(true), 300);
    });

    loadAlertValidationItems();
}

function setReferentTab(tabKey) {
    if (!REFERENT_STEP_KEYS.includes(tabKey)) {
        return;
    }
    alertValidationState.currentTab = tabKey;
    REFERENT_STEP_KEYS.forEach((key) => {
        const btn = alertValidationState.elements.tabButtons && alertValidationState.elements.tabButtons[key];
        if (btn) {
            btn.classList.toggle('active', key === tabKey);
            btn.setAttribute('aria-selected', key === tabKey ? 'true' : 'false');
        }
    });
    renderAlertValidationRows(alertValidationState.data);
}

function updateReferentTabCounts(alerts) {
    const counts = {
        sinistre: 0, sinistre_valide: 0, rapport: 0, rapport_valide: 0,
        facture: 0, facture_valide: 0, resolu: 0,
    };
    (alerts || []).forEach((a) => {
        const step = getReferentStep(a);
        if (counts[step] !== undefined) {
            counts[step]++;
        }
    });
    alertValidationState.tabCounts = counts;
    REFERENT_STEP_KEYS.forEach((key) => {
        const el = alertValidationState.elements.tabCounts && alertValidationState.elements.tabCounts[key];
        if (el) {
            el.textContent = String(counts[key] || 0);
            el.setAttribute('aria-label', `${counts[key] || 0} dossiers`);
        }
    });
}

async function loadAlertValidationItems(showToast = false) {
    if (!alertValidationState.enabled) {
        return;
    }

    const token = typeof getStoredAccessToken === 'function' ? getStoredAccessToken() : (window.MobilityAuth && window.MobilityAuth.getAccessToken && window.MobilityAuth.getAccessToken());
    if (!token) {
        setHidden(alertValidationState.elements.loading, true);
        if (alertValidationState.elements.error) {
            alertValidationState.elements.error.hidden = false;
            alertValidationState.elements.error.innerHTML = `
                <strong>Session expirée ou non connecté.</strong><br>
                <a href="login.html?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}">Se connecter</a> pour charger les alertes SOS.
            `;
        }
        updateNavAlertesCount(0);
        return;
    }

    setHidden(alertValidationState.elements.error, true);
    setHidden(alertValidationState.elements.loading, false);

    const cacheBust = `_t=${Date.now()}`;

    try {
        const alertes = await apiCall(`/sos/?limit=200&${cacheBust}`);
        const alertesArray = Array.isArray(alertes) ? alertes : [];
        
        // Charger les sinistres avec workflow_steps pour chaque alerte (données fraîches)
        const alertesWithSinistres = await Promise.all(
            alertesArray.map(async (alerte) => {
                if (alerte.sinistre_id) {
                    try {
                        const sinistre = await apiCall(`/sos/${alerte.id}/sinistre?${cacheBust}`);
                        alerte.sinistre = sinistre;
                    } catch (error) {
                        console.warn(`Impossible de charger le sinistre pour l'alerte ${alerte.id}:`, error);
                        alerte.sinistre = null;
                    }
                }
                return alerte;
            })
        );
        
        alertValidationState.data = alertesWithSinistres;
        const activeCount = alertesWithSinistres.filter((a) => ALERT_ACTIVE_STATUSES.has(a.statut)).length;
        updateNavAlertesCount(activeCount);
        updateReferentTabCounts(alertValidationState.data);

        // Appliquer l'onglet depuis l'URL après chargement (ex. ?tab=sinistre_valide)
        if (alertValidationState.tabFromUrl) {
            setReferentTab(alertValidationState.tabFromUrl);
            alertValidationState.tabFromUrl = null;
        } else {
            renderAlertValidationRows(alertValidationState.data);
        }

        if (showToast) {
            showAlert('Dossiers mis à jour.', 'success');
        }
    } catch (error) {
        console.error('Erreur lors du chargement des alertes SOS:', error);
        updateNavAlertesCount(0);
        if (alertValidationState.elements.error) {
            alertValidationState.elements.error.hidden = false;
            alertValidationState.elements.error.innerHTML = `
                <strong>Impossible de charger les alertes SOS.</strong><br>
                ${escapeHtml(error?.message || 'Erreur inconnue')}
            `;
        }
    } finally {
        setHidden(alertValidationState.elements.loading, true);
    }
}

function renderAlertValidationRows(alerts) {
    if (
        !alertValidationState.enabled ||
        !alertValidationState.elements.body ||
        !alertValidationState.elements.table ||
        !alertValidationState.elements.emptyState
    ) {
        return;
    }

    const currentTab = alertValidationState.currentTab || 'sinistre';
    const alertsForTab = (alerts || []).filter((a) => getReferentStep(a) === currentTab);

    const emptyMessages = {
        sinistre: 'Aucun sinistre en attente de validation de l\'urgence.',
        sinistre_valide: 'Aucun sinistre validé en attente de la prochaine étape.',
        rapport: 'Aucun rapport médical en attente de validation.',
        rapport_valide: 'Aucun dossier avec rapport validé en attente de facture.',
        facture: 'Aucune facture en attente de validation médicale.',
        facture_valide: 'Aucune facture validée en attente de compta.',
        resolu: 'Aucun dossier résolu (facturé par la compta MH).',
    };
    const emptyMsg = alertValidationState.elements.emptyMessage;
    if (emptyMsg) {
        emptyMsg.textContent = emptyMessages[currentTab] || 'Aucun dossier dans cette étape.';
    }

    if (!alertsForTab.length) {
        alertValidationState.elements.body.innerHTML = '';
        alertValidationState.elements.table.hidden = true;
        alertValidationState.elements.emptyState.hidden = false;
        return;
    }

    const sortedAlerts = alertsForTab
        .slice()
        .sort((a, b) => {
            const timestampA = getAlertTimestamp(a);
            const timestampB = getAlertTimestamp(b);
            if (timestampA === timestampB) {
                return (b.id || 0) - (a.id || 0);
            }
            return timestampB - timestampA;
        });

    const totalPages = Math.max(1, Math.ceil(sortedAlerts.length / ROWS_PER_PAGE));
    currentPageAlertValidation = Math.min(currentPageAlertValidation, totalPages - 1);
    const start = currentPageAlertValidation * ROWS_PER_PAGE;
    const pageData = sortedAlerts.slice(start, start + ROWS_PER_PAGE);

    alertValidationState.elements.table.hidden = false;
    alertValidationState.elements.emptyState.hidden = true;
    alertValidationState.elements.body.innerHTML = pageData
        .map((alerte) => buildAlertValidationRow(alerte, { isActive: ALERT_ACTIVE_STATUSES.has(alerte.statut) }))
        .join('');

    const pagEl = document.getElementById('alertValidationPagination');
    if (pagEl) {
        if (sortedAlerts.length <= ROWS_PER_PAGE) {
            pagEl.hidden = true;
            pagEl.innerHTML = '';
        } else {
            pagEl.hidden = false;
            const end = Math.min(start + ROWS_PER_PAGE, sortedAlerts.length);
            pagEl.innerHTML = `
                <div class="table-pagination" role="navigation">
                    <span class="table-pagination-info">Lignes ${start + 1}-${end} sur ${sortedAlerts.length}</span>
                    <div class="table-pagination-buttons">
                        <button type="button" class="btn btn-outline btn-sm" id="alertValPrev" ${currentPageAlertValidation <= 0 ? 'disabled' : ''}>◀ Précédent</button>
                        <span>Page ${currentPageAlertValidation + 1} / ${totalPages}</span>
                        <button type="button" class="btn btn-outline btn-sm" id="alertValNext" ${currentPageAlertValidation >= totalPages - 1 ? 'disabled' : ''}>Suivant ▶</button>
                    </div>
                </div>
            `;
            document.getElementById('alertValPrev')?.addEventListener('click', () => { currentPageAlertValidation--; renderAlertValidationRows(alerts); });
            document.getElementById('alertValNext')?.addEventListener('click', () => { currentPageAlertValidation++; renderAlertValidationRows(alerts); });
        }
    }
}

function filterAlertValidationRows(searchTerm) {
    if (!alertValidationState.enabled || !alertValidationState.data) {
        return;
    }
    
    const term = searchTerm.toLowerCase().trim();
    
    if (!term) {
        // Aucun filtre, afficher toutes les alertes
        renderAlertValidationRows(alertValidationState.data);
        return;
    }
    
    // Filtrer les alertes en fonction du terme de recherche
    const filteredAlerts = alertValidationState.data.filter((alerte) => {
        // Rechercher dans le numéro d'alerte
        const numero = (alerte.numero_alerte || `Alerte #${alerte.id}`).toLowerCase();
        if (numero.includes(term)) return true;
        
        // Rechercher dans le nom du patient
        const patient = (alerte.user_full_name || `Utilisateur #${alerte.user_id}`).toLowerCase();
        if (patient.includes(term)) return true;
        
        // Rechercher dans la description
        const description = (alerte.description || '').toLowerCase();
        if (description.includes(term)) return true;
        
        // Rechercher dans le numéro de souscription
        const souscription = (alerte.numero_souscription || `Souscription #${alerte.souscription_id || ''}`).toLowerCase();
        if (souscription.includes(term)) return true;
        
        // Rechercher dans le statut
        const statut = (alerte.statut || '').toLowerCase();
        if (statut.includes(term)) return true;
        
        // Rechercher dans le statut des actions
        const actionStatus = getActionStatusLabel(alerte).toLowerCase();
        if (actionStatus.includes(term)) return true;
        
        // Rechercher dans la priorité
        const priorite = (alerte.priorite || '').toLowerCase();
        if (priorite.includes(term)) return true;
        
        // Rechercher dans le nom de l'hôpital assigné
        const hospital = (alerte.assigned_hospital?.nom || '').toLowerCase();
        if (hospital.includes(term)) return true;
        
        // Rechercher dans l'ID de l'alerte
        const alertId = String(alerte.id || '').toLowerCase();
        if (alertId.includes(term)) return true;
        
        return false;
    });
    
    // Afficher les résultats filtrés
    renderAlertValidationRows(filteredAlerts);
    
    // Afficher un message si aucun résultat
    if (filteredAlerts.length === 0 && alertValidationState.data.length > 0) {
        alertValidationState.elements.body.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 2rem;">
                    <div class="empty-state">
                        <div class="empty-state-icon">🔍</div>
                        <p>Aucun résultat trouvé pour "<strong>${escapeHtml(searchTerm)}</strong>"</p>
                        <p class="muted">Essayez avec d'autres mots-clés</p>
                    </div>
                </td>
            </tr>
        `;
        alertValidationState.elements.table.hidden = false;
        alertValidationState.elements.emptyState.hidden = true;
        updateAlertValidationCount(0);
    }
}

function buildAlertValidationRow(alert, options = {}) {
    const isActive = options.isActive ?? ALERT_ACTIVE_STATUSES.has(alert.statut);
    const rowClasses = ['alert-row'];
    if (!isActive) {
        rowClasses.push('alert-row--inactive');
    }
    const numero = alert.numero_alerte || `Alerte #${alert.id}`;
    const patient = alert.user_full_name || `Utilisateur #${alert.user_id}`;
    const description = alert.description
        ? truncateText(alert.description, 140)
        : 'Aucune description fournie';
    const updatedAt = alert.updated_at || alert.created_at;
    const hospitalLine = alert.assigned_hospital?.nom
        ? `<div class="muted">${escapeHtml(alert.assigned_hospital.nom)}</div>`
        : '';

    const souscriptionDisplay = alert.numero_souscription
        ? escapeHtml(alert.numero_souscription)
        : (alert.souscription_id ? `Souscription #${alert.souscription_id}` : '—');
    const decisionNote = isActive ? '' : '<div class="table-note muted">Décision enregistrée par un médecin référent.</div>';

    return `
        <tr class="${rowClasses.join(' ')}">
            <td>
                <strong>${escapeHtml(numero)}</strong>
                <div class="muted">${souscriptionDisplay}</div>
            </td>
            <td>
                <div><strong>${escapeHtml(patient)}</strong></div>
                <div class="muted">${escapeHtml(description)}</div>
                ${hospitalLine}
            </td>
            <td>${getAlertPriorityBadge(alert.priorite)}</td>
            <td>${getAlertStatusBadge(alert.statut)}</td>
            <td><span class="action-status-badge">${escapeHtml(getActionStatusLabel(alert))}</span></td>
            <td>${formatDateTime(updatedAt)}</td>
            <td>
                <div class="table-actions">
                    <button
                        class="btn btn-outline btn-sm"
                        type="button"
                        data-alert-action="open-details"
                        data-alert-id="${alert.id}"
                    >
                        Voir le dossier
                    </button>
                </div>
                ${decisionNote}
            </td>
        </tr>
    `;
}

function handleAlertValidationTableClick(event) {
    const actionButton = event.target.closest('[data-alert-action]');
    if (!actionButton) {
        return;
    }
    const alertId = Number(actionButton.dataset.alertId);
    if (!alertId) {
        return;
    }
    if (actionButton.dataset.alertAction === 'open-details') {
        const url = `hospital-alert-details.html?alert_id=${alertId}`;
        window.location.href = url;
    }
}

function getAlertStatusBadge(status) {
    const label = ALERT_STATUS_LABELS[status] || status || 'Inconnu';
    const className = ALERT_STATUS_CLASSES[status] || 'status-pending';
    return `<span class="status-badge ${className}">${escapeHtml(label)}</span>`;
}

function getAlertPriorityBadge(priority) {
    const label = ALERT_PRIORITY_LABELS[priority] || (priority ? priority : 'Normale');
    const className = ALERT_PRIORITY_CLASSES[priority] || 'priority-normale';
    return `<span class="priority-badge ${className}">${escapeHtml(label)}</span>`;
}

function updateAlertValidationCount(value) {
    if (!alertValidationState.elements.count) {
        return;
    }
    const suffix = value > 1 ? 'alertes' : 'alerte';
    alertValidationState.elements.count.textContent = `${value} ${suffix}`;
}

function setHidden(element, hidden) {
    if (!element) {
        return;
    }
    element.hidden = hidden;
}

function getAlertTimestamp(alert) {
    if (!alert) {
        return 0;
    }
    // Priorité à la dernière action horodatée, puis updated_at, puis created_at
    const lastActionTime = getLastActionTimestamp(alert);
    if (lastActionTime > 0) {
        return lastActionTime;
    }
    // Fallback sur updated_at ou created_at
    const dateStr = alert.updated_at || alert.created_at;
    if (!dateStr) {
        return 0;
    }
    const baseDate = new Date(dateStr);
    const time = baseDate.getTime();
    return Number.isNaN(time) ? 0 : time;
}

function getLastActionTimestamp(alert) {
    if (!alert || !alert.sinistre || !alert.sinistre.workflow_steps) {
        return 0;
    }
    const workflowSteps = alert.sinistre.workflow_steps || [];
    
    // Actions importantes à considérer pour le tri
    const actionSteps = [
        'verification_urgence',      // Alerte avérée/non avérée
        'ambulance_en_route',        // Ambulance envoyée
        'validation_et_numero_sinistre', // Orientation médecin
        'facture_emise',             // Facture envoyée
        'validation_facture_medicale',   // Facture validée médicalement
    ];
    
    let lastTimestamp = 0;
    for (const step of workflowSteps) {
        if (actionSteps.includes(step.step_key) && step.completed_at) {
            const stepTime = new Date(step.completed_at).getTime();
            if (!Number.isNaN(stepTime) && stepTime > lastTimestamp) {
                lastTimestamp = stepTime;
            }
        }
    }
    
    return lastTimestamp;
}

/**
 * Détermine l'étape de validation du médecin référent pour un dossier (alerte + sinistre).
 * Dossier résolu = facturé par l'agent comptable MH après toutes les validations (stay invoiced ou facture validée/payée).
 * @param {Object} alert - Alerte avec alerte.sinistre (workflow_steps, hospital_stay, hospital_stay.invoice)
 * @returns {'sinistre'|'sinistre_valide'|'rapport'|'rapport_valide'|'facture'|'facture_valide'|'resolu'}
 */
function getReferentStep(alert) {
    if (!alert || !alert.sinistre) {
        return 'resolu';
    }
    const sinistre = alert.sinistre;
    const stay = sinistre.hospital_stay;
    const invoice = stay && stay.invoice;
    const stayStatus = stay ? String(stay.status || '').toLowerCase() : '';
    const invoiceStatut = invoice ? String(invoice.statut || '').toLowerCase() : '';

    // 1. Dossier résolu : facture finalisée par l'agent comptable MH (validée/payée), ou facture rejetée médicalement
    // Ne pas utiliser stay.status === 'invoiced' : la facture créée par l'hôpital a ce statut mais reste à valider par le médecin référent MH
    if (invoiceStatut === 'validated' || invoiceStatut === 'paid') {
        return 'resolu';
    }
    if (invoice && invoice.validation_medicale === 'rejected') {
        return 'resolu';
    }

    // 2. Rapport à valider : séjour en attente de validation du rapport
    if (stay && (stayStatus === 'awaiting_validation')) {
        return 'rapport';
    }

    const stepsMap = new Map((sinistre.workflow_steps || []).map((s) => [s.step_key, s]));
    const verificationUrgence = stepsMap.get('verification_urgence');
    const statutUrgence = verificationUrgence ? String(verificationUrgence.statut || '').toLowerCase() : '';

    // 3. Sinistre à valider : urgence pas encore décidée
    if (statutUrgence && statutUrgence !== 'completed' && statutUrgence !== 'cancelled') {
        return 'sinistre';
    }

    // 4. Facture à valider : facture en attente de validation médicale
    if (invoice && invoice.validation_medicale === 'pending') {
        return 'facture';
    }

    // 5. Facture validée : validation médicale approuvée par le référent, en attente compta / paiement
    if (invoice && invoice.validation_medicale === 'approved') {
        return 'facture_valide';
    }

    // 6. Rapport validé : rapport validé par le référent, en attente de facture ou de validation facture
    if (stay && stayStatus === 'validated' && (!invoice || invoice.validation_medicale !== 'pending')) {
        return 'rapport_valide';
    }

    // 7. Sinistre validé : urgence validée, en attente de la prochaine étape
    if (statutUrgence === 'completed' || (sinistre.numero_sinistre && !statutUrgence)) {
        return 'sinistre_valide';
    }

    return 'resolu';
}

function getActionStatusLabel(alert) {
    if (!alert || !alert.sinistre || !alert.sinistre.workflow_steps) {
        return '—';
    }
    
    const workflowSteps = alert.sinistre.workflow_steps || [];
    const stepsMap = new Map();
    workflowSteps.forEach(step => {
        stepsMap.set(step.step_key, step);
    });
    
    // Vérifier les actions dans l'ordre de priorité d'affichage
    if (stepsMap.get('validation_facture_medicale')?.statut === 'completed') {
        return 'Facture validée médicalement';
    }
    if (stepsMap.get('facture_emise')?.statut === 'completed') {
        return 'Facture envoyée';
    }
    if (stepsMap.get('validation_et_numero_sinistre')?.statut === 'completed') {
        return 'Orientation médecin';
    }
    if (stepsMap.get('ambulance_en_route')?.statut === 'completed') {
        return 'Ambulance envoyée';
    }
    if (stepsMap.get('verification_urgence')?.statut === 'completed') {
        return 'Alerte avérée';
    }
    if (stepsMap.get('verification_urgence')?.statut === 'cancelled') {
        return 'Alerte non avérée';
    }
    
    return 'En attente';
}

function truncateText(text, maxLength = 140) {
    if (typeof text !== 'string') {
        return '';
    }
    if (text.length <= maxLength) {
        return text;
    }
    return `${text.slice(0, maxLength - 3)}...`;
}

window.submitReviewDecision = submitReviewDecision;
window.openAttestationPdf = openAttestationPdf;

