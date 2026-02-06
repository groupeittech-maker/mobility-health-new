import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { sosApi, SinistreDetail } from '../api/sos'
import { Alerte } from '../types'
import './SinistreTracking.css'

export default function SinistreTracking() {
  const { alerteId } = useParams<{ alerteId: string }>()

  const { data: alerte, isLoading: isLoadingAlerte, error: alerteError } = useQuery({
    queryKey: ['alerte', alerteId],
    queryFn: () => sosApi.getAlerte(Number(alerteId)),
    enabled: !!alerteId,
    refetchInterval: 5000,
  })

  const { data: sinistre, isLoading: isLoadingSinistre, error: sinistreError } = useQuery({
    queryKey: ['sinistre', alerteId],
    queryFn: () => sosApi.getSinistreByAlerte(Number(alerteId)),
    enabled: !!alerteId,
    refetchInterval: 5000,
  })

  const isLoading = isLoadingAlerte || isLoadingSinistre
  const error = alerteError || sinistreError

  if (isLoading) {
    return (
      <div className="sinistre-tracking">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Chargement des informations du sinistre...</p>
        </div>
      </div>
    )
  }

  if (error || !alerte) {
    return (
      <div className="sinistre-tracking">
        <div className="error-container">
          <h2>Erreur</h2>
          <p>Impossible de charger les informations du sinistre.</p>
        </div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusBadge = (statut: string) => {
    const statusClass = `status-badge status-${statut}`
    const statusLabels: Record<string, string> = {
      en_attente: 'En attente',
      en_cours: 'En cours',
      resolue: 'Résolue',
      annulee: 'Annulée',
    }
    return <span className={statusClass}>{statusLabels[statut] || statut}</span>
  }

  const getPriorityBadge = (priorite: string) => {
    const priorityClass = `priority-badge priority-${priorite}`
  const workflowStatusLabel = (statut: string) => {
    const labels: Record<string, string> = {
      pending: 'En attente',
      in_progress: 'En cours',
      completed: 'Terminé',
      cancelled: 'Annulé',
    }
    return labels[statut] || statut
  }

  const workflowStatusIcon = (statut: string) => {
    const icons: Record<string, string> = {
      pending: '⏳',
      in_progress: '🚧',
      completed: '✅',
      cancelled: '⛔',
    }
    return icons[statut] || '•'
  }

    const priorityLabels: Record<string, string> = {
      faible: 'Faible',
      normale: 'Normale',
      elevee: 'Élevée',
      critique: 'Critique',
    }
    return <span className={priorityClass}>{priorityLabels[priorite] || priorite}</span>
  }


  return (
    <div className="sinistre-tracking">
      <div className="tracking-container">
        <div className="tracking-header">
          <h1>Suivi du Sinistre</h1>
          <div className="header-badges">
            {getStatusBadge(alerte.statut)}
            {getPriorityBadge(alerte.priorite)}
          </div>
        </div>

        <div className="tracking-content">
          {/* Informations principales */}
          <section className="info-section">
            <h2>Informations de l'alerte</h2>
            <div className="info-grid">
              <div className="info-item">
                <label>Numéro d'alerte</label>
                <p className="value">{alerte.numero_alerte}</p>
              </div>
              <div className="info-item">
                <label>Date de déclenchement</label>
                <p className="value">{formatDate(alerte.created_at)}</p>
              </div>
              <div className="info-item">
                <label>Statut</label>
                <div className="value">{getStatusBadge(alerte.statut)}</div>
              </div>
              <div className="info-item">
                <label>Priorité</label>
                <div className="value">{getPriorityBadge(alerte.priorite)}</div>
              </div>
            </div>
          </section>

          {/* Localisation */}
          <section className="info-section">
            <h2>📍 Localisation</h2>
            <div className="location-info">
              <div className="coordinates">
                <strong>Coordonnées GPS :</strong>
                <p>{alerte.latitude.toFixed(6)}, {alerte.longitude.toFixed(6)}</p>
              </div>
              {alerte.adresse && (
                <div className="address">
                  <strong>Adresse :</strong>
                  <p>{alerte.adresse}</p>
                </div>
              )}
              <div className="map-placeholder">
                {/* Placeholder pour une carte - à intégrer avec Leaflet ou Mapbox en production */}
                <p>🗺️ Carte interactive (à intégrer)</p>
                <a
                  href={`https://www.google.com/maps?q=${alerte.latitude},${alerte.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="map-link"
                >
                  Voir sur Google Maps
                </a>
              </div>
            </div>
          </section>

          {/* Description */}
          {alerte.description && (
            <section className="info-section">
              <h2>Description</h2>
              <div className="description-box">
                <p>{alerte.description}</p>
              </div>
            </section>
          )}

          {/* Hôpital proposé */}
          <section className="info-section">
            <h2>🏥 Hôpital proposé</h2>
            <div className="hospital-info">
              {sinistre?.hospital ? (
                <div className="hospital-card hospital-details">
                  <h3>{sinistre.hospital.nom}</h3>
                  {sinistre.hospital.adresse && (
                    <div className="hospital-address">
                      <strong>Adresse :</strong>
                      <p>
                        {sinistre.hospital.adresse}
                        {sinistre.hospital.ville && `, ${sinistre.hospital.ville}`}
                        {sinistre.hospital.pays && `, ${sinistre.hospital.pays}`}
                      </p>
                    </div>
                  )}
                  {sinistre.hospital.telephone && (
                    <div className="hospital-contact">
                      <strong>Téléphone :</strong>
                      <p>{sinistre.hospital.telephone}</p>
                    </div>
                  )}
                  {sinistre.hospital.email && (
                    <div className="hospital-contact">
                      <strong>Email :</strong>
                      <p>{sinistre.hospital.email}</p>
                    </div>
                  )}
                  <a
                    href={`https://www.google.com/maps?q=${sinistre.hospital.latitude},${sinistre.hospital.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="map-link"
                  >
                    Voir sur Google Maps
                  </a>
                </div>
              ) : (
                <div className="hospital-card">
                  <p className="hospital-loading">
                    ⏳ Hôpital en cours d'assignation...
                  </p>
                  <p className="hospital-note">
                    Un agent SOS vous contactera avec les détails de l'hôpital assigné.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Processus sinistre */}
          {sinistre?.workflow_steps && sinistre.workflow_steps.length > 0 && (
            <section className="info-section">
              <h2>🧭 Processus sinistre</h2>
              <div className="workflow-timeline">
                {sinistre.workflow_steps.map((step) => (
                  <div key={step.step_key} className={`workflow-step workflow-${step.statut}`}>
                    <div className="workflow-step-header">
                      <span className="workflow-icon">{workflowStatusIcon(step.statut)}</span>
                      <div>
                        <h4>{step.titre}</h4>
                        <span className={`workflow-badge workflow-${step.statut}`}>
                          {workflowStatusLabel(step.statut)}
                        </span>
                      </div>
                    </div>
                    <p className="workflow-description">{step.description}</p>
                    <div className="workflow-meta">
                      <span>Étape {step.ordre}</span>
                      {step.completed_at && (
                        <span>Complétée le {formatDate(step.completed_at)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Prise en charge */}
          <section className="info-section">
            <h2>✅ Prise en charge</h2>
            <div className="care-info">
              <div className="care-status">
                {alerte.statut === 'en_attente' && (
                  <div className="care-pending">
                    <span className="icon">⏳</span>
                    <div>
                      <strong>En attente de prise en charge</strong>
                      <p>Un agent SOS va prendre en charge votre alerte dans les plus brefs délais.</p>
                    </div>
                  </div>
                )}
                {alerte.statut === 'en_cours' && (
                  <div className="care-active">
                    <span className="icon">🚑</span>
                    <div>
                      <strong>Prise en charge en cours</strong>
                      <p>Votre alerte a été prise en charge. Un agent SOS suit votre dossier.</p>
                    </div>
                  </div>
                )}
                {alerte.statut === 'resolue' && (
                  <div className="care-resolved">
                    <span className="icon">✅</span>
                    <div>
                      <strong>Prise en charge terminée</strong>
                      <p>Votre alerte a été résolue.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Interventions */}
          <section className="info-section">
            <h2>🔧 Interventions</h2>
            <div className="interventions-list">
              <div className="intervention-item">
                <div className="intervention-header">
                  <span className="intervention-time">{formatDate(alerte.created_at)}</span>
                  <span className="intervention-status">Initialisation</span>
                </div>
                <div className="intervention-body">
                  <p>Alerte déclenchée et transmise au centre d'urgence</p>
                </div>
              </div>
              
              {/* Afficher les prestations (interventions médicales) */}
              {sinistre?.prestations && sinistre.prestations.length > 0 ? (
                sinistre.prestations.map((prestation) => (
                  <div key={prestation.id} className="intervention-item">
                    <div className="intervention-header">
                      <span className="intervention-time">{formatDate(prestation.date_prestation)}</span>
                      <span className={`intervention-status status-${prestation.statut}`}>
                        {prestation.statut === 'pending' ? 'En attente' : 
                         prestation.statut === 'validated' ? 'Validée' : 
                         prestation.statut === 'invoiced' ? 'Facturée' : prestation.statut}
                      </span>
                    </div>
                    <div className="intervention-body">
                      <p><strong>{prestation.libelle}</strong> ({prestation.code_prestation})</p>
                      {prestation.description && <p className="intervention-description">{prestation.description}</p>}
                      <p className="intervention-details">
                        Quantité: {prestation.quantite} × {prestation.montant_unitaire.toFixed(2)} = {prestation.montant_total.toFixed(2)} €
                      </p>
                    </div>
                  </div>
                ))
              ) : alerte.statut === 'en_cours' && (
                <div className="intervention-item">
                  <div className="intervention-header">
                    <span className="intervention-time">...</span>
                    <span className="intervention-status">En cours</span>
                  </div>
                  <div className="intervention-body">
                    <p>Un agent SOS suit votre dossier et coordonne les interventions nécessaires.</p>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Notes du gestionnaire */}
          <section className="info-section">
            <h2>📝 Notes du gestionnaire</h2>
            <div className="notes-container">
              {sinistre?.notes ? (
                <div className="notes-content">
                  <p>{sinistre.notes}</p>
                  {sinistre.agent_sinistre_nom && (
                    <p className="notes-author">
                      <em>— {sinistre.agent_sinistre_nom}</em>
                    </p>
                  )}
                </div>
              ) : (
                <p className="notes-placeholder">
                  Les notes du gestionnaire apparaîtront ici une fois qu'un agent SOS aura ajouté des informations.
                </p>
              )}
            </div>
          </section>

          {/* Informations sur l'agent et le médecin */}
          {sinistre && (sinistre.agent_sinistre_nom || sinistre.medecin_referent_nom) && (
            <section className="info-section">
              <h2>👥 Équipe de prise en charge</h2>
              <div className="info-grid">
                {sinistre.agent_sinistre_nom && (
                  <div className="info-item">
                    <label>Agent sinistre</label>
                    <p className="value">{sinistre.agent_sinistre_nom}</p>
                  </div>
                )}
                {sinistre.medecin_referent_nom && (
                  <div className="info-item">
                    <label>Médecin référent</label>
                    <p className="value">{sinistre.medecin_referent_nom}</p>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>

        {/* Actions */}
        <div className="tracking-actions">
          <button
            onClick={() => window.location.reload()}
            className="btn-refresh"
          >
            🔄 Actualiser
          </button>
        </div>
      </div>
    </div>
  )
}

