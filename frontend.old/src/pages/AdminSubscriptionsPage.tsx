import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminSubscriptionsApi } from '../api/adminSubscriptions'
import { Souscription } from '../types'
import './AdminSubscriptionsPage.css'

export default function AdminSubscriptionsPage() {
  const [selectedSubscription, setSelectedSubscription] = useState<number | null>(null)
  const [statutFilter, setStatutFilter] = useState<string>('')
  const [showValidationModal, setShowValidationModal] = useState(false)
  const [validationType, setValidationType] = useState<'medical' | 'tech' | 'final'>('medical')
  const [validationNotes, setValidationNotes] = useState('')
  const [validationApproved, setValidationApproved] = useState(true)

  const queryClient = useQueryClient()

  const { data: subscriptions = [], isLoading } = useQuery({
    queryKey: ['admin-subscriptions', statutFilter],
    queryFn: () => adminSubscriptionsApi.getAll(statutFilter || undefined),
  })

  const { data: subscription, isLoading: isLoadingDetail } = useQuery({
    queryKey: ['admin-subscription', selectedSubscription],
    queryFn: () => adminSubscriptionsApi.getById(selectedSubscription!),
    enabled: !!selectedSubscription,
  })

  const { data: questionnaires = [] } = useQuery({
    queryKey: ['subscription-questionnaires', selectedSubscription],
    queryFn: () => adminSubscriptionsApi.getQuestionnaires(selectedSubscription!),
    enabled: !!selectedSubscription,
  })

  const { data: payments = [] } = useQuery({
    queryKey: ['subscription-payments', selectedSubscription],
    queryFn: () => adminSubscriptionsApi.getPayments(selectedSubscription!),
    enabled: !!selectedSubscription,
  })

  const validateMutation = useMutation({
    mutationFn: (data: { approved: boolean; notes?: string }) => {
      if (validationType === 'medical') {
        return adminSubscriptionsApi.validateMedical(selectedSubscription!, data)
      } else if (validationType === 'tech') {
        return adminSubscriptionsApi.validateTech(selectedSubscription!, data)
      } else {
        return adminSubscriptionsApi.approveFinal(selectedSubscription!, data)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-subscription'] })
      queryClient.invalidateQueries({ queryKey: ['admin-subscriptions'] })
      setShowValidationModal(false)
      setValidationNotes('')
    },
  })

  const generateAttestationMutation = useMutation({
    mutationFn: () => adminSubscriptionsApi.generateAttestation(selectedSubscription!),
    onSuccess: (data) => {
      if (data.url) {
        window.open(data.url, '_blank')
      }
    },
  })

  const handleValidate = () => {
    validateMutation.mutate({
      approved: validationApproved,
      notes: validationNotes || undefined,
    })
  }

  const getStatusBadge = (statut: string) => {
    const statusClass = `status-badge status-${statut.toLowerCase()}`
    return <span className={statusClass}>{statut}</span>
  }

  const getValidationBadge = (validation: string | null | undefined) => {
    if (!validation) return <span className="validation-badge pending">En attente</span>
    if (validation === 'approved') return <span className="validation-badge approved">✓ Approuvé</span>
    return <span className="validation-badge rejected">✗ Rejeté</span>
  }

  return (
    <div className="admin-subscriptions-page">
      <div className="page-header">
        <h1>Gestion des Souscriptions</h1>
      </div>

      <div className="subscriptions-layout">
        {/* Liste des souscriptions */}
        <div className="subscriptions-list">
          <div className="list-header">
            <h2>Souscriptions</h2>
            <select
              value={statutFilter}
              onChange={(e) => setStatutFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">Tous les statuts</option>
              <option value="en_attente">En attente</option>
              <option value="active">Active</option>
              <option value="expiree">Expirée</option>
              <option value="annulee">Annulée</option>
            </select>
          </div>

          {isLoading ? (
            <div className="loading">Chargement...</div>
          ) : (
            <div className="subscriptions-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Numéro</th>
                    <th>Statut</th>
                    <th>Prix</th>
                    <th>Date début</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((sub) => (
                    <tr
                      key={sub.id}
                      className={selectedSubscription === sub.id ? 'selected' : ''}
                      onClick={() => setSelectedSubscription(sub.id)}
                    >
                      <td>#{sub.id}</td>
                      <td>{sub.numero_souscription}</td>
                      <td>{getStatusBadge(sub.statut)}</td>
                      <td>{sub.prix_applique.toFixed(2)} €</td>
                      <td>{new Date(sub.date_debut).toLocaleDateString('fr-FR')}</td>
                      <td>
                        <button
                          className="btn-view"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedSubscription(sub.id)
                          }}
                        >
                          Voir
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Détails de la souscription */}
        {selectedSubscription && (
          <div className="subscription-details">
            {isLoadingDetail ? (
              <div className="loading">Chargement des détails...</div>
            ) : subscription ? (
              <>
                <div className="details-header">
                  <h2>Souscription #{subscription.id}</h2>
                  <button
                    className="btn-close"
                    onClick={() => setSelectedSubscription(null)}
                  >
                    ✕
                  </button>
                </div>

                <div className="details-content">
                  {/* Informations générales */}
                  <section className="info-section">
                    <h3>Informations générales</h3>
                    <div className="info-grid">
                      <div className="info-item">
                        <label>Numéro de souscription</label>
                        <p>{subscription.numero_souscription}</p>
                      </div>
                      <div className="info-item">
                        <label>Statut</label>
                        <p>{getStatusBadge(subscription.statut)}</p>
                      </div>
                      <div className="info-item">
                        <label>Prix appliqué</label>
                        <p>{subscription.prix_applique.toFixed(2)} €</p>
                      </div>
                      <div className="info-item">
                        <label>Date de début</label>
                        <p>{new Date(subscription.date_debut).toLocaleDateString('fr-FR')}</p>
                      </div>
                      {subscription.date_fin && (
                        <div className="info-item">
                          <label>Date de fin</label>
                          <p>{new Date(subscription.date_fin).toLocaleDateString('fr-FR')}</p>
                        </div>
                      )}
                    </div>
                  </section>

                  {/* Validations */}
                  <section className="info-section">
                    <h3>Validations</h3>
                    <div className="validations-grid">
                      <div className="validation-item">
                        <label>Validation médicale</label>
                        {getValidationBadge(subscription.validation_medicale)}
                        {subscription.validation_medicale_notes && (
                          <p className="validation-notes">{subscription.validation_medicale_notes}</p>
                        )}
                      </div>
                      <div className="validation-item">
                        <label>Validation technique</label>
                        {getValidationBadge(subscription.validation_technique)}
                        {subscription.validation_technique_notes && (
                          <p className="validation-notes">{subscription.validation_technique_notes}</p>
                        )}
                      </div>
                      <div className="validation-item">
                        <label>Validation finale (Production MH)</label>
                        {getValidationBadge(subscription.validation_finale)}
                        {subscription.validation_finale_notes && (
                          <p className="validation-notes">{subscription.validation_finale_notes}</p>
                        )}
                      </div>
                    </div>
                  </section>

                  {/* Questionnaires */}
                  <section className="info-section">
                    <h3>Questionnaires</h3>
                    <div className="questionnaires-list">
                      {questionnaires.length > 0 ? (
                        questionnaires.map((q) => (
                          <div key={q.id} className="questionnaire-item">
                            <div className="questionnaire-header">
                              <span className="questionnaire-type">
                                {q.type_questionnaire === 'short' ? 'Court' :
                                 q.type_questionnaire === 'long' ? 'Long' :
                                 q.type_questionnaire === 'administratif' ? 'Administratif' :
                                 q.type_questionnaire === 'medical' ? 'Médical' : q.type_questionnaire}
                              </span>
                              <span className="questionnaire-version">v{q.version}</span>
                              <span className={`questionnaire-status status-${q.statut}`}>
                                {q.statut}
                              </span>
                            </div>
                            <div className="questionnaire-content">
                              <pre>{JSON.stringify(q.reponses, null, 2)}</pre>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="no-data">Aucun questionnaire disponible</p>
                      )}
                    </div>
                  </section>

                  {/* Paiements */}
                  <section className="info-section">
                    <h3>Paiements</h3>
                    <div className="payments-list">
                      {payments.length > 0 ? (
                        <table>
                          <thead>
                            <tr>
                              <th>ID</th>
                              <th>Montant</th>
                              <th>Type</th>
                              <th>Statut</th>
                              <th>Date</th>
                            </tr>
                          </thead>
                          <tbody>
                            {payments.map((payment) => (
                              <tr key={payment.id}>
                                <td>#{payment.id}</td>
                                <td>{payment.montant.toFixed(2)} €</td>
                                <td>{payment.type_paiement}</td>
                                <td>
                                  <span className={`status-badge status-${payment.statut}`}>
                                    {payment.statut}
                                  </span>
                                </td>
                                <td>
                                  {payment.date_paiement
                                    ? new Date(payment.date_paiement).toLocaleDateString('fr-FR')
                                    : new Date(payment.created_at).toLocaleDateString('fr-FR')}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <p className="no-data">Aucun paiement enregistré</p>
                      )}
                    </div>
                  </section>

                  {/* Actions */}
                  <section className="actions-section">
                    <h3>Actions</h3>
                    <div className="actions-buttons">
                      <button
                        className="btn-action btn-validate-medical"
                        onClick={() => {
                          setValidationType('medical')
                          setShowValidationModal(true)
                        }}
                        disabled={subscription.validation_medicale === 'approved'}
                      >
                        Valider médicalement
                      </button>
                      <button
                        className="btn-action btn-validate-tech"
                        onClick={() => {
                          setValidationType('tech')
                          setShowValidationModal(true)
                        }}
                        disabled={subscription.validation_technique === 'approved'}
                      >
                        Valider techniquement
                      </button>
                      <button
                        className="btn-action btn-validate-final"
                        onClick={() => {
                          setValidationType('final')
                          setShowValidationModal(true)
                        }}
                        disabled={
                          subscription.validation_finale === 'approved' ||
                          subscription.validation_medicale !== 'approved' ||
                          subscription.validation_technique !== 'approved'
                        }
                      >
                        Approuver définitivement
                      </button>
                      <button
                        className="btn-action btn-generate-attestation"
                        onClick={() => generateAttestationMutation.mutate()}
                        disabled={
                          subscription.validation_finale !== 'approved' ||
                          generateAttestationMutation.isPending
                        }
                      >
                        {generateAttestationMutation.isPending
                          ? 'Génération...'
                          : 'Générer attestation PDF'}
                      </button>
                    </div>
                  </section>
                </div>
              </>
            ) : (
              <div className="error">Souscription non trouvée</div>
            )}
          </div>
        )}
      </div>

      {/* Modal de validation */}
      {showValidationModal && (
        <div className="modal-overlay" onClick={() => setShowValidationModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>
              {validationType === 'medical'
                ? 'Validation médicale'
                : validationType === 'tech'
                ? 'Validation technique'
                : 'Validation finale (Production MH)'}
            </h2>
            <div className="modal-form">
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
              <label>
                Notes (optionnel)
                <textarea
                  value={validationNotes}
                  onChange={(e) => setValidationNotes(e.target.value)}
                  rows={4}
                  placeholder="Ajouter des notes..."
                />
              </label>
              <div className="modal-actions">
                <button
                  className="btn-cancel"
                  onClick={() => setShowValidationModal(false)}
                >
                  Annuler
                </button>
                <button
                  className="btn-confirm"
                  onClick={handleValidate}
                  disabled={validateMutation.isPending}
                >
                  {validateMutation.isPending ? 'Validation...' : 'Confirmer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

