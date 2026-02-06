import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminSubscriptionsApi } from '../api/adminSubscriptions'
import { Souscription } from '../types'
import './AGPMHDashboard.css'

export default function AGPMHDashboard() {
  const [selectedSubscription, setSelectedSubscription] = useState<Souscription | null>(null)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const [validationNotes, setValidationNotes] = useState('')
  const [validationApproved, setValidationApproved] = useState(true)

  const queryClient = useQueryClient()

  const { data: subscriptions = [], isLoading } = useQuery({
    queryKey: ['pending-subscriptions'],
    queryFn: () => adminSubscriptionsApi.getPending(),
  })

  const approveFinalMutation = useMutation({
    mutationFn: ({ id, approved, notes }: { id: number; approved: boolean; notes?: string }) =>
      adminSubscriptionsApi.approveFinal(id, { approved, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-subscriptions'] })
      setShowValidationModal(false)
      setSelectedSubscription(null)
    },
  })

  const handleApproveFinal = () => {
    if (!selectedSubscription) return
    approveFinalMutation.mutate({
      id: selectedSubscription.id,
      approved: validationApproved,
      notes: validationNotes || undefined,
    })
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  // Filtrer les souscriptions prêtes pour validation finale
  // (validation médicale ET technique approuvées, mais pas encore validées finalement)
  const readyForFinalApproval = subscriptions.filter(
    (sub) =>
      sub.validation_medicale === 'approved' &&
      sub.validation_technique === 'approved' &&
      (!sub.validation_finale || sub.validation_finale === 'pending')
  )

  const canApproveFinal = (sub: Souscription) => {
    return (
      sub.validation_medicale === 'approved' &&
      sub.validation_technique === 'approved'
    )
  }

  return (
    <div className="agpmh-dashboard">
      <div className="dashboard-header">
        <h1>Dashboard Production MH</h1>
        <p>Validation finale des souscriptions</p>
      </div>

      <div className="dashboard-content">
        <div className="subscriptions-list">
          <h2>Dossiers prêts pour validation finale ({readyForFinalApproval.length})</h2>
          
          {isLoading ? (
            <div className="loading">Chargement...</div>
          ) : readyForFinalApproval.length === 0 ? (
            <div className="empty-state">Aucun dossier prêt pour validation finale</div>
          ) : (
            <div className="subscriptions-grid">
              {readyForFinalApproval.map((sub) => (
                <div
                  key={sub.id}
                  className={`subscription-card ${selectedSubscription?.id === sub.id ? 'selected' : ''} ${
                    canApproveFinal(sub) ? 'ready' : 'not-ready'
                  }`}
                  onClick={() => setSelectedSubscription(sub)}
                >
                  <div className="card-header">
                    <h3>Souscription #{sub.numero_souscription}</h3>
                    {sub.validation_finale === 'approved' && (
                      <span className="status-badge approved">Validé</span>
                    )}
                  </div>
                  <div className="card-body">
                    <div className="validation-summary">
                      <div className="validation-item">
                        <span className="label">Médical:</span>
                        <span className={`status ${sub.validation_medicale || 'pending'}`}>
                          {sub.validation_medicale === 'approved' ? '✓' : '○'}
                        </span>
                      </div>
                      <div className="validation-item">
                        <span className="label">Technique:</span>
                        <span className={`status ${sub.validation_technique || 'pending'}`}>
                          {sub.validation_technique === 'approved' ? '✓' : '○'}
                        </span>
                      </div>
                    </div>
                    <p><strong>Prix:</strong> {sub.prix_applique.toFixed(2)} €</p>
                    <p><strong>Date:</strong> {formatDate(sub.created_at)}</p>
                  </div>
                  {canApproveFinal(sub) && (
                    <div className="card-actions">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedSubscription(sub)
                          setShowValidationModal(true)
                          setValidationNotes(sub.validation_finale_notes || '')
                          setValidationApproved(sub.validation_finale === 'approved')
                        }}
                        className="btn-primary"
                      >
                        Valider définitivement
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {selectedSubscription && (
          <div className="subscription-details">
            <div className="details-header">
              <h2>Souscription #{selectedSubscription.numero_souscription}</h2>
            </div>

            <div className="details-section">
              <h3>Résumé des validations</h3>
              <div className="validations-summary">
                <div className={`validation-card ${selectedSubscription.validation_medicale || 'pending'}`}>
                  <h4>Validation médicale</h4>
                  <p className="status">
                    {selectedSubscription.validation_medicale || 'En attente'}
                  </p>
                  {selectedSubscription.validation_medicale_date && (
                    <p className="date">
                      {formatDate(selectedSubscription.validation_medicale_date)}
                    </p>
                  )}
                  {selectedSubscription.validation_medicale_notes && (
                    <p className="notes">{selectedSubscription.validation_medicale_notes}</p>
                  )}
                </div>
                <div className={`validation-card ${selectedSubscription.validation_technique || 'pending'}`}>
                  <h4>Validation technique</h4>
                  <p className="status">
                    {selectedSubscription.validation_technique || 'En attente'}
                  </p>
                  {selectedSubscription.validation_technique_date && (
                    <p className="date">
                      {formatDate(selectedSubscription.validation_technique_date)}
                    </p>
                  )}
                  {selectedSubscription.validation_technique_notes && (
                    <p className="notes">{selectedSubscription.validation_technique_notes}</p>
                  )}
                </div>
                <div className={`validation-card ${selectedSubscription.validation_finale || 'pending'}`}>
                  <h4>Validation finale</h4>
                  <p className="status">
                    {selectedSubscription.validation_finale || 'En attente'}
                  </p>
                  {selectedSubscription.validation_finale_date && (
                    <p className="date">
                      {formatDate(selectedSubscription.validation_finale_date)}
                    </p>
                  )}
                  {selectedSubscription.validation_finale_notes && (
                    <p className="notes">{selectedSubscription.validation_finale_notes}</p>
                  )}
                </div>
              </div>
            </div>

            <div className="details-section">
              <h3>Informations de la souscription</h3>
              <div className="info-grid">
                <div className="info-item">
                  <strong>Prix appliqué:</strong>
                  <span>{selectedSubscription.prix_applique.toFixed(2)} €</span>
                </div>
                <div className="info-item">
                  <strong>Date de début:</strong>
                  <span>{formatDate(selectedSubscription.date_debut)}</span>
                </div>
                {selectedSubscription.date_fin && (
                  <div className="info-item">
                    <strong>Date de fin:</strong>
                    <span>{formatDate(selectedSubscription.date_fin)}</span>
                  </div>
                )}
                <div className="info-item">
                  <strong>Statut:</strong>
                  <span>{selectedSubscription.statut}</span>
                </div>
              </div>
            </div>

            {canApproveFinal(selectedSubscription) && (
              <div className="details-section">
                <button
                  onClick={() => {
                    setShowValidationModal(true)
                    setValidationNotes(selectedSubscription.validation_finale_notes || '')
                    setValidationApproved(selectedSubscription.validation_finale === 'approved')
                  }}
                  className="btn-primary btn-large"
                >
                  Approuver définitivement
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {showValidationModal && selectedSubscription && (
        <div className="modal-overlay" onClick={() => setShowValidationModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Validation finale (Production)</h2>
            <div className="warning-box">
              <p>
                ⚠️ Cette validation finale activera la souscription. Assurez-vous que toutes les
                validations précédentes sont correctes.
              </p>
            </div>
            <div className="form-group">
              <label>
                <input
                  type="radio"
                  checked={validationApproved}
                  onChange={() => setValidationApproved(true)}
                />
                Approuver définitivement
              </label>
              <label>
                <input
                  type="radio"
                  checked={!validationApproved}
                  onChange={() => setValidationApproved(false)}
                />
                Rejeter
              </label>
            </div>
            <div className="form-group">
              <label>Notes (optionnel)</label>
              <textarea
                value={validationNotes}
                onChange={(e) => setValidationNotes(e.target.value)}
                rows={4}
                placeholder="Ajoutez des notes sur votre décision..."
              />
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowValidationModal(false)} className="btn-secondary">
                Annuler
              </button>
              <button
                onClick={handleApproveFinal}
                className="btn-primary"
                disabled={approveFinalMutation.isPending || !canApproveFinal(selectedSubscription)}
              >
                {approveFinalMutation.isPending ? 'Validation...' : 'Valider définitivement'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
