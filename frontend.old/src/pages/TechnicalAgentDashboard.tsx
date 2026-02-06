import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminSubscriptionsApi } from '../api/adminSubscriptions'
import { Souscription } from '../types'
import './TechnicalAgentDashboard.css'

export default function TechnicalAgentDashboard() {
  const [selectedSubscription, setSelectedSubscription] = useState<Souscription | null>(null)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const [validationNotes, setValidationNotes] = useState('')
  const [validationApproved, setValidationApproved] = useState(true)

  const queryClient = useQueryClient()

  const { data: subscriptions = [], isLoading } = useQuery({
    queryKey: ['pending-subscriptions'],
    queryFn: () => adminSubscriptionsApi.getPending(),
  })

  const validateMutation = useMutation({
    mutationFn: ({ id, approved, notes }: { id: number; approved: boolean; notes?: string }) =>
      adminSubscriptionsApi.validateTech(id, { approved, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-subscriptions'] })
      setShowValidationModal(false)
      setSelectedSubscription(null)
    },
  })

  const handleValidate = () => {
    if (!selectedSubscription) return
    validateMutation.mutate({
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

  const getValidationStatus = (subscription: Souscription) => {
    if (subscription.validation_technique === 'approved') return { text: 'Approuvé', class: 'approved' }
    if (subscription.validation_technique === 'rejected') return { text: 'Rejeté', class: 'rejected' }
    return { text: 'En attente', class: 'pending' }
  }

  // Filtrer les souscriptions qui nécessitent une validation technique
  const pendingTechSubscriptions = subscriptions.filter(
    (sub) => !sub.validation_technique || sub.validation_technique === 'pending'
  )

  return (
    <div className="technical-agent-dashboard">
      <div className="dashboard-header">
        <h1>Dashboard Agent Technique</h1>
        <p>Gestion des validations techniques</p>
      </div>

      <div className="dashboard-content">
        <div className="subscriptions-list">
          <h2>Dossiers à valider ({pendingTechSubscriptions.length})</h2>
          
          {isLoading ? (
            <div className="loading">Chargement...</div>
          ) : pendingTechSubscriptions.length === 0 ? (
            <div className="empty-state">Aucun dossier en attente</div>
          ) : (
            <div className="subscriptions-table">
              <table>
                <thead>
                  <tr>
                    <th>Numéro</th>
                    <th>Date création</th>
                    <th>Prix</th>
                    <th>Statut validation</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingTechSubscriptions.map((sub) => {
                    const status = getValidationStatus(sub)
                    return (
                      <tr
                        key={sub.id}
                        className={selectedSubscription?.id === sub.id ? 'selected' : ''}
                        onClick={() => setSelectedSubscription(sub)}
                      >
                        <td>{sub.numero_souscription}</td>
                        <td>{formatDate(sub.created_at)}</td>
                        <td>{sub.prix_applique.toFixed(2)} €</td>
                        <td>
                          <span className={`status-badge ${status.class}`}>{status.text}</span>
                        </td>
                        <td>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedSubscription(sub)
                              setShowValidationModal(true)
                              setValidationNotes(sub.validation_technique_notes || '')
                              setValidationApproved(sub.validation_technique === 'approved')
                            }}
                            className="btn-small"
                          >
                            Valider
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {selectedSubscription && (
          <div className="subscription-details">
            <div className="details-header">
              <h2>Souscription #{selectedSubscription.numero_souscription}</h2>
            </div>

            <div className="details-section">
              <h3>Informations générales</h3>
              <div className="info-grid">
                <div className="info-item">
                  <strong>Date de création:</strong>
                  <span>{formatDate(selectedSubscription.created_at)}</span>
                </div>
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
              </div>
            </div>

            <div className="details-section">
              <h3>Validations</h3>
              <div className="validations-list">
                <div className="validation-item">
                  <strong>Validation médicale:</strong>
                  <span className={selectedSubscription.validation_medicale || 'pending'}>
                    {selectedSubscription.validation_medicale || 'En attente'}
                  </span>
                </div>
                <div className="validation-item">
                  <strong>Validation technique:</strong>
                  <span className={selectedSubscription.validation_technique || 'pending'}>
                    {selectedSubscription.validation_technique || 'En attente'}
                  </span>
                </div>
                <div className="validation-item">
                  <strong>Validation finale:</strong>
                  <span className={selectedSubscription.validation_finale || 'pending'}>
                    {selectedSubscription.validation_finale || 'En attente'}
                  </span>
                </div>
              </div>
            </div>

            {selectedSubscription.notes && (
              <div className="details-section">
                <h3>Notes</h3>
                <p>{selectedSubscription.notes}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {showValidationModal && selectedSubscription && (
        <div className="modal-overlay" onClick={() => setShowValidationModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Validation technique</h2>
            <div className="form-group">
              <label>
                <input
                  type="radio"
                  checked={validationApproved}
                  onChange={() => setValidationApproved(true)}
                />
                Approuver
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
                onClick={handleValidate}
                className="btn-primary"
                disabled={validateMutation.isPending}
              >
                {validateMutation.isPending ? 'Validation...' : 'Valider'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
