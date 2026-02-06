import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminSinistresApi } from '../api/adminSinistres'
import { sosApi, SinistreDetail } from '../api/sos'
import { hospitalsApi } from '../api/hospitals'
import { Alerte, Hospital } from '../types'
import './AdminSinistresPage.css'

type WorkflowStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'

export default function AdminSinistresPage() {
  const [selectedAlerte, setSelectedAlerte] = useState<number | null>(null)
  const [selectedSinistre, setSelectedSinistre] = useState<number | null>(null)
  const [statutFilter, setStatutFilter] = useState<string>('')
  const [showAssignHospitalModal, setShowAssignHospitalModal] = useState(false)
  const [showCloseModal, setShowCloseModal] = useState(false)
  const [closeNotes, setCloseNotes] = useState('')
  const [selectedHospitalId, setSelectedHospitalId] = useState<number | null>(null)
  const [workflowStatusDrafts, setWorkflowStatusDrafts] = useState<Record<string, WorkflowStatus>>({})
  const [workflowNotes, setWorkflowNotes] = useState<Record<string, string>>({})

  const queryClient = useQueryClient()

  const { data: alertes = [], isLoading: isLoadingAlertes } = useQuery({
    queryKey: ['admin-alertes', statutFilter],
    queryFn: () => adminSinistresApi.getAlertes(statutFilter || undefined),
  })

  const { data: sinistres = [] } = useQuery({
    queryKey: ['admin-sinistres', statutFilter],
    queryFn: () => adminSinistresApi.getSinistres(statutFilter || undefined),
  })

  const { data: sinistreDetail } = useQuery({
    queryKey: ['sinistre-detail', selectedAlerte],
    queryFn: () => sosApi.getSinistreByAlerte(selectedAlerte!),
    enabled: !!selectedAlerte,
  })

  const { data: hospitals = [] } = useQuery({
    queryKey: ['hospitals'],
    queryFn: () => hospitalsApi.getAll(),
  })

  const assignHospitalMutation = useMutation({
    mutationFn: (data: { hospital_id: number }) =>
      adminSinistresApi.assignHospital(selectedSinistre!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sinistre-detail'] })
      queryClient.invalidateQueries({ queryKey: ['admin-sinistres'] })
      setShowAssignHospitalModal(false)
      setSelectedHospitalId(null)
    },
  })

  const closeSinistreMutation = useMutation({
    mutationFn: (data: { notes?: string }) =>
      adminSinistresApi.closeSinistre(selectedSinistre!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sinistre-detail'] })
      queryClient.invalidateQueries({ queryKey: ['admin-sinistres'] })
      queryClient.invalidateQueries({ queryKey: ['admin-alertes'] })
      setShowCloseModal(false)
      setCloseNotes('')
    },
  })

  const updateNotesMutation = useMutation({
    mutationFn: (notes: string) =>
      adminSinistresApi.updateNotes(selectedSinistre!, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sinistre-detail'] })
    },
  })

  const updateWorkflowStepMutation = useMutation({
    mutationFn: (variables: { stepKey: string; statut: WorkflowStatus; notes?: string }) =>
      adminSinistresApi.updateWorkflowStep(selectedSinistre!, variables.stepKey, {
        statut: variables.statut,
        notes: variables.notes,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sinistre-detail'] })
    },
  })

  const workflowStatusLabel = (statut: string) => {
    const labels: Record<string, string> = {
      pending: 'En attente',
      in_progress: 'En cours',
      completed: 'Terminé',
      cancelled: 'Annulé',
    }
    return labels[statut] || statut
  }

  const handleWorkflowStatusChange = (stepKey: string, value: WorkflowStatus) => {
    setWorkflowStatusDrafts((prev) => ({ ...prev, [stepKey]: value }))
  }

  const handleWorkflowNoteChange = (stepKey: string, value: string) => {
    setWorkflowNotes((prev) => ({ ...prev, [stepKey]: value }))
  }

  const handleWorkflowUpdate = (stepKey: string, fallbackStatut: WorkflowStatus) => {
    if (!selectedSinistre) return
    const statut = workflowStatusDrafts[stepKey] || fallbackStatut
    const notes = workflowNotes[stepKey]?.trim() || undefined
    updateWorkflowStepMutation.mutate({ stepKey, statut, notes })
  }

  const handleAssignHospital = () => {
    if (selectedHospitalId) {
      assignHospitalMutation.mutate({ hospital_id: selectedHospitalId })
    }
  }

  const handleCloseSinistre = () => {
    closeSinistreMutation.mutate({ notes: closeNotes || undefined })
  }

  const getStatusBadge = (statut: string) => {
    const statusClass = `status-badge status-${statut}`
    const labels: Record<string, string> = {
      en_attente: 'En attente',
      en_cours: 'En cours',
      resolue: 'Résolue',
      annulee: 'Annulée',
    }
    return <span className={statusClass}>{labels[statut] || statut}</span>
  }

  const getPriorityBadge = (priorite: string) => {
    const priorityClass = `priority-badge priority-${priorite}`
    const labels: Record<string, string> = {
      faible: 'Faible',
      normale: 'Normale',
      elevee: 'Élevée',
      critique: 'Critique',
    }
    return <span className={priorityClass}>{labels[priorite] || priorite}</span>
  }

  return (
    <div className="admin-sinistres-page">
      <div className="page-header">
        <h1>Gestion des Sinistres</h1>
      </div>

      <div className="sinistres-layout">
        {/* Liste des alertes */}
        <div className="alertes-list">
          <div className="list-header">
            <h2>Alertes reçues</h2>
            <select
              value={statutFilter}
              onChange={(e) => setStatutFilter(e.target.value)}
              className="filter-select"
            >
              <option value="">Tous les statuts</option>
              <option value="en_attente">En attente</option>
              <option value="en_cours">En cours</option>
              <option value="resolue">Résolue</option>
              <option value="annulee">Annulée</option>
            </select>
          </div>

          {isLoadingAlertes ? (
            <div className="loading">Chargement...</div>
          ) : (
            <div className="alertes-table">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Numéro</th>
                    <th>Statut</th>
                    <th>Priorité</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {alertes.map((alerte) => (
                    <tr
                      key={alerte.id}
                      className={selectedAlerte === alerte.id ? 'selected' : ''}
                      onClick={() => {
                        setSelectedAlerte(alerte.id)
                      const sinistre = sinistres.find((s) => s.alerte_id === alerte.id)
                      if (sinistre) {
                        setSelectedSinistre(sinistre.id)
                        setWorkflowStatusDrafts({})
                        setWorkflowNotes({})
                      }
                      }}
                    >
                      <td>#{alerte.id}</td>
                      <td>{alerte.numero_alerte}</td>
                      <td>{getStatusBadge(alerte.statut)}</td>
                      <td>{getPriorityBadge(alerte.priorite)}</td>
                      <td>{new Date(alerte.created_at).toLocaleDateString('fr-FR')}</td>
                      <td>
                        <button
                          className="btn-view"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedAlerte(alerte.id)
                            const sinistre = sinistres.find((s) => s.alerte_id === alerte.id)
                            if (sinistre) {
                              setSelectedSinistre(sinistre.id)
                              setWorkflowStatusDrafts({})
                              setWorkflowNotes({})
                            }
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

        {/* Détails du sinistre */}
        {selectedAlerte && sinistreDetail && (
          <div className="sinistre-details">
            <div className="details-header">
              <h2>Sinistre #{sinistreDetail.numero_sinistre}</h2>
              <button
                className="btn-close"
                onClick={() => {
                  setSelectedAlerte(null)
                  setSelectedSinistre(null)
                  setWorkflowStatusDrafts({})
                  setWorkflowNotes({})
                }}
              >
                ✕
              </button>
            </div>

            <div className="details-content">
              {/* Informations de l'alerte */}
              <section className="info-section">
                <h3>Informations de l'alerte</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Numéro d'alerte</label>
                    <p>{sinistreDetail.alerte_id}</p>
                  </div>
                  <div className="info-item">
                    <label>Statut</label>
                    <p>{getStatusBadge(sinistreDetail.statut)}</p>
                  </div>
                  <div className="info-item">
                    <label>Date de création</label>
                    <p>{new Date(sinistreDetail.created_at).toLocaleString('fr-FR')}</p>
                  </div>
                </div>
              </section>

              {/* Géolocalisation */}
              <section className="info-section">
                <h3>📍 Géolocalisation</h3>
                <div className="location-info">
                  <div className="coordinates">
                    <strong>Coordonnées GPS :</strong>
                    <p>
                      {alertes.find((a) => a.id === selectedAlerte)?.latitude.toFixed(6)},{' '}
                      {alertes.find((a) => a.id === selectedAlerte)?.longitude.toFixed(6)}
                    </p>
                  </div>
                  {alertes.find((a) => a.id === selectedAlerte)?.adresse && (
                    <div className="address">
                      <strong>Adresse :</strong>
                      <p>{alertes.find((a) => a.id === selectedAlerte)?.adresse}</p>
                    </div>
                  )}
                  <a
                    href={`https://www.google.com/maps?q=${alertes.find((a) => a.id === selectedAlerte)?.latitude},${alertes.find((a) => a.id === selectedAlerte)?.longitude}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="map-link"
                  >
                    Voir sur Google Maps
                  </a>
                </div>
              </section>

              {/* Hôpital assigné */}
              <section className="info-section">
                <h3>🏥 Hôpital assigné</h3>
                {sinistreDetail.hospital ? (
                  <div className="hospital-card">
                    <h4>{sinistreDetail.hospital.nom}</h4>
                    {sinistreDetail.hospital.adresse && (
                      <p>
                        {sinistreDetail.hospital.adresse}
                        {sinistreDetail.hospital.ville && `, ${sinistreDetail.hospital.ville}`}
                        {sinistreDetail.hospital.pays && `, ${sinistreDetail.hospital.pays}`}
                      </p>
                    )}
                    {sinistreDetail.hospital.telephone && (
                      <p>
                        <strong>Téléphone :</strong> {sinistreDetail.hospital.telephone}
                      </p>
                    )}
                    {sinistreDetail.hospital.email && (
                      <p>
                        <strong>Email :</strong> {sinistreDetail.hospital.email}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="no-hospital">Aucun hôpital assigné</p>
                )}
                <button
                  className="btn-action btn-assign-hospital"
                  onClick={() => setShowAssignHospitalModal(true)}
                >
                  {sinistreDetail.hospital ? 'Changer l\'hôpital' : 'Assigner un hôpital'}
                </button>
              </section>

              {/* Interventions */}
              <section className="info-section">
                <h3>🔧 Interventions</h3>
                <div className="interventions-list">
                  {sinistreDetail.prestations && sinistreDetail.prestations.length > 0 ? (
                    sinistreDetail.prestations.map((prestation) => (
                      <div key={prestation.id} className="intervention-item">
                        <div className="intervention-header">
                          <span className="intervention-libelle">{prestation.libelle}</span>
                          <span className={`intervention-status status-${prestation.statut}`}>
                            {prestation.statut}
                          </span>
                        </div>
                        <div className="intervention-details">
                          <p>
                            {prestation.quantite} × {prestation.montant_unitaire.toFixed(2)} € ={' '}
                            {prestation.montant_total.toFixed(2)} €
                          </p>
                          <p className="intervention-date">
                            {new Date(prestation.date_prestation).toLocaleString('fr-FR')}
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">Aucune intervention enregistrée</p>
                  )}
                </div>
              </section>

              {/* Workflow */}
              {sinistreDetail.workflow_steps && sinistreDetail.workflow_steps.length > 0 && (
                <section className="info-section">
                  <h3>🧭 Processus sinistre</h3>
                  <div className="workflow-admin-list">
                    {sinistreDetail.workflow_steps.map((step) => {
                      const currentStatus = (workflowStatusDrafts[step.step_key] || step.statut) as WorkflowStatus
                      const noteValue = workflowNotes[step.step_key] || ''
                      return (
                        <div key={step.step_key} className="workflow-admin-item">
                          <div className="workflow-admin-header">
                            <div>
                              <h4>
                                Étape {step.ordre} · {step.titre}
                              </h4>
                              <p>{step.description}</p>
                            </div>
                            <span className={`workflow-badge workflow-${step.statut}`}>
                              {workflowStatusLabel(step.statut)}
                            </span>
                          </div>
                          <div className="workflow-admin-controls">
                            <select
                              className="workflow-status-select"
                              value={currentStatus}
                              onChange={(e) => handleWorkflowStatusChange(step.step_key, e.target.value as WorkflowStatus)}
                            >
                              <option value="pending">En attente</option>
                              <option value="in_progress">En cours</option>
                              <option value="completed">Terminé</option>
                              <option value="cancelled">Annulé</option>
                            </select>
                            <input
                              type="text"
                              className="workflow-note-input"
                              placeholder="Note (optionnel)"
                              value={noteValue}
                              onChange={(e) => handleWorkflowNoteChange(step.step_key, e.target.value)}
                            />
                            <button
                              className="btn-action btn-update-workflow"
                              onClick={() => handleWorkflowUpdate(step.step_key, currentStatus)}
                              disabled={updateWorkflowStepMutation.isPending}
                            >
                              {updateWorkflowStepMutation.isPending ? 'Mise à jour...' : 'Mettre à jour'}
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </section>
              )}

              {/* Notes */}
              <section className="info-section">
                <h3>📝 Notes du gestionnaire</h3>
                <div className="notes-container">
                  {sinistreDetail.notes ? (
                    <div className="notes-content">
                      <pre>{sinistreDetail.notes}</pre>
                    </div>
                  ) : (
                    <p className="no-data">Aucune note</p>
                  )}
                  <div className="add-notes-form">
                    <textarea
                      placeholder="Ajouter une note..."
                      rows={3}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && e.ctrlKey) {
                          const textarea = e.target as HTMLTextAreaElement
                          if (textarea.value.trim()) {
                            updateNotesMutation.mutate(textarea.value)
                            textarea.value = ''
                          }
                        }
                      }}
                    />
                    <p className="hint">Appuyez sur Ctrl+Entrée pour ajouter la note</p>
                  </div>
                </div>
              </section>

              {/* Actions */}
              <section className="actions-section">
                <h3>Actions</h3>
                <div className="actions-buttons">
                  <button
                    className="btn-action btn-close-sinistre"
                    onClick={() => setShowCloseModal(true)}
                    disabled={sinistreDetail.statut === 'resolu'}
                  >
                    {sinistreDetail.statut === 'resolu' ? 'Sinistre clôturé' : 'Clôturer le sinistre'}
                  </button>
                </div>
              </section>
            </div>
          </div>
        )}
      </div>

      {/* Modal d'assignation d'hôpital */}
      {showAssignHospitalModal && (
        <div className="modal-overlay" onClick={() => setShowAssignHospitalModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Assigner un hôpital</h2>
            <div className="modal-form">
              <label>
                Sélectionner un hôpital
                <select
                  value={selectedHospitalId || ''}
                  onChange={(e) => setSelectedHospitalId(Number(e.target.value))}
                >
                  <option value="">-- Sélectionner --</option>
                  {hospitals.map((hospital) => (
                    <option key={hospital.id} value={hospital.id}>
                      {hospital.nom} - {hospital.ville || ''} {hospital.pays || ''}
                    </option>
                  ))}
                </select>
              </label>
              <div className="modal-actions">
                <button
                  className="btn-cancel"
                  onClick={() => setShowAssignHospitalModal(false)}
                >
                  Annuler
                </button>
                <button
                  className="btn-confirm"
                  onClick={handleAssignHospital}
                  disabled={!selectedHospitalId || assignHospitalMutation.isPending}
                >
                  {assignHospitalMutation.isPending ? 'Assignation...' : 'Assigner'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de clôture */}
      {showCloseModal && (
        <div className="modal-overlay" onClick={() => setShowCloseModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Clôturer le sinistre</h2>
            <div className="modal-form">
              <label>
                Notes de clôture (optionnel)
                <textarea
                  value={closeNotes}
                  onChange={(e) => setCloseNotes(e.target.value)}
                  rows={4}
                  placeholder="Ajouter des notes sur la clôture du sinistre..."
                />
              </label>
              <div className="modal-actions">
                <button
                  className="btn-cancel"
                  onClick={() => setShowCloseModal(false)}
                >
                  Annuler
                </button>
                <button
                  className="btn-confirm"
                  onClick={handleCloseSinistre}
                  disabled={closeSinistreMutation.isPending}
                >
                  {closeSinistreMutation.isPending ? 'Clôture...' : 'Clôturer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

