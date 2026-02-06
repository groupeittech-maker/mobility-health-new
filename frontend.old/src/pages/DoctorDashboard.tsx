import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminSubscriptionsApi } from '../api/adminSubscriptions'
import { questionnairesApi } from '../api/questionnaires'
import { Souscription } from '../types'
import './DoctorDashboard.css'

export default function DoctorDashboard() {
  const [selectedSubscription, setSelectedSubscription] = useState<Souscription | null>(null)
  const [showValidationModal, setShowValidationModal] = useState(false)
  const [validationNotes, setValidationNotes] = useState('')
  const [validationApproved, setValidationApproved] = useState(true)

  const queryClient = useQueryClient()

  const { data: subscriptions = [], isLoading } = useQuery({
    queryKey: ['pending-subscriptions'],
    queryFn: () => adminSubscriptionsApi.getPending(),
  })

  const { data: questionnaires = [] } = useQuery({
    queryKey: ['questionnaires', selectedSubscription?.id],
    queryFn: async () => {
      if (!selectedSubscription) return []
      // Récupérer les questionnaires pour cette souscription
      const short = await questionnairesApi.getBySubscription(selectedSubscription.id, 'short').catch(() => null)
      const long = await questionnairesApi.getBySubscription(selectedSubscription.id, 'long').catch(() => null)
      return [short, long].filter(Boolean)
    },
    enabled: !!selectedSubscription,
  })

  const validateMutation = useMutation({
    mutationFn: ({ id, approved, notes }: { id: number; approved: boolean; notes?: string }) =>
      adminSubscriptionsApi.validateMedical(id, { approved, notes }),
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
    if (subscription.validation_medicale === 'approved') return { text: 'Approuvé', class: 'approved' }
    if (subscription.validation_medicale === 'rejected') return { text: 'Rejeté', class: 'rejected' }
    return { text: 'En attente', class: 'pending' }
  }

  return (
    <div className="doctor-dashboard">
      <div className="dashboard-header">
        <h1>Dashboard Médecin</h1>
        <p>Gestion des validations médicales</p>
      </div>

      <div className="dashboard-content">
        <div className="subscriptions-list">
          <h2>Dossiers à valider ({subscriptions.length})</h2>
          
          {isLoading ? (
            <div className="loading">Chargement...</div>
          ) : subscriptions.length === 0 ? (
            <div className="empty-state">Aucun dossier en attente</div>
          ) : (
            <div className="subscriptions-grid">
              {subscriptions.map((sub) => {
                const status = getValidationStatus(sub)
                return (
                  <div
                    key={sub.id}
                    className={`subscription-card ${selectedSubscription?.id === sub.id ? 'selected' : ''}`}
                    onClick={() => setSelectedSubscription(sub)}
                  >
                    <div className="card-header">
                      <h3>Souscription #{sub.numero_souscription}</h3>
                      <span className={`status-badge ${status.class}`}>{status.text}</span>
                    </div>
                    <div className="card-body">
                      <p><strong>Date de création:</strong> {formatDate(sub.created_at)}</p>
                      <p><strong>Prix:</strong> {sub.prix_applique.toFixed(2)} €</p>
                      {sub.validation_medicale_date && (
                        <p><strong>Dernière validation:</strong> {formatDate(sub.validation_medicale_date)}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {selectedSubscription && (
          <div className="subscription-details">
            <div className="details-header">
              <h2>Détails de la souscription #{selectedSubscription.numero_souscription}</h2>
              <button
                onClick={() => {
                  setShowValidationModal(true)
                  setValidationNotes(selectedSubscription.validation_medicale_notes || '')
                  setValidationApproved(selectedSubscription.validation_medicale === 'approved')
                }}
                className="btn-primary"
              >
                Valider médicalement
              </button>
            </div>

            <div className="details-section">
              <h3>Données médicales</h3>
              {questionnaires.length === 0 ? (
                <p className="no-data">Aucun questionnaire disponible</p>
              ) : (
                <div className="questionnaires-list">
                  {questionnaires.map((q: any) => (
                    <div key={q.id} className="questionnaire-card">
                      <h4>Questionnaire {q.type_questionnaire === 'short' ? 'Court' : 'Long'}</h4>
                      <div className="questionnaire-content">
                        <pre>{JSON.stringify(q.reponses, null, 2)}</pre>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="details-section">
              <h3>Informations de validation</h3>
              {selectedSubscription.validation_medicale ? (
                <div className="validation-info">
                  <p><strong>Statut:</strong> {selectedSubscription.validation_medicale}</p>
                  {selectedSubscription.validation_medicale_date && (
                    <p><strong>Date:</strong> {formatDate(selectedSubscription.validation_medicale_date)}</p>
                  )}
                  {selectedSubscription.validation_medicale_notes && (
                    <p><strong>Notes:</strong> {selectedSubscription.validation_medicale_notes}</p>
                  )}
                </div>
              ) : (
                <p className="no-data">Aucune validation effectuée</p>
              )}
            </div>
          </div>
        )}
      </div>

      {showValidationModal && selectedSubscription && (
        <div className="modal-overlay" onClick={() => setShowValidationModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Validation médicale</h2>
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
