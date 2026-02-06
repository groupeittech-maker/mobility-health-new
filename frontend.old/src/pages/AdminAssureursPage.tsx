import { FormEvent, useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { assureursApi, AssureurPayload } from '../api/assureurs'
import { usersApi, UserSummary } from '../api/users'
import type { Assureur } from '../types'
import './AdminAssureursPage.css'

type AssureurFormState = {
  nom: string
  pays: string
  adresse: string
  telephone: string
  logo_url: string
  agent_comptable_id: string
}

const emptyForm: AssureurFormState = {
  nom: '',
  pays: 'Côte d\'Ivoire',
  adresse: '',
  telephone: '',
  logo_url: '',
  agent_comptable_id: '',
}

export default function AdminAssureursPage() {
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<AssureurFormState>(emptyForm)
  const [selectedAssureur, setSelectedAssureur] = useState<Assureur | null>(null)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data: assureurs = [], isLoading } = useQuery({
    queryKey: ['admin-assureurs'],
    queryFn: () => assureursApi.listAdmin(),
  })

  const { data: accountants = [] } = useQuery({
    queryKey: ['assureur-accountants'],
    queryFn: () => usersApi.getByRole('agent_comptable_assureur'),
  })

  useEffect(() => {
    if (selectedAssureur) {
      setFormState({
        nom: selectedAssureur.nom,
        pays: selectedAssureur.pays,
        adresse: selectedAssureur.adresse || '',
        telephone: selectedAssureur.telephone || '',
        logo_url: selectedAssureur.logo_url || '',
        agent_comptable_id: selectedAssureur.agent_comptable_id ? String(selectedAssureur.agent_comptable_id) : '',
      })
    } else {
      setFormState(emptyForm)
    }
  }, [selectedAssureur])

  const resetForm = () => {
    setSelectedAssureur(null)
    setFeedback(null)
    setFormState(emptyForm)
  }

  const handleInputChange = (field: keyof AssureurFormState, value: string) => {
    setFormState(prev => ({ ...prev, [field]: value }))
    if (feedback) {
      setFeedback(null)
    }
  }

  const asPayload = (): AssureurPayload | null => {
    const trimmedNom = formState.nom.trim()
    const trimmedPays = formState.pays.trim()
    if (!trimmedNom || !trimmedPays) {
      setFeedback({ type: 'error', message: 'Le nom et le pays sont obligatoires.' })
      return null
    }
    return {
      nom: trimmedNom,
      pays: trimmedPays,
      adresse: formState.adresse.trim() || undefined,
      telephone: formState.telephone.trim() || undefined,
      logo_url: formState.logo_url.trim() || undefined,
      agent_comptable_id: formState.agent_comptable_id ? Number(formState.agent_comptable_id) : null,
    }
  }

  const createMutation = useMutation({
    mutationFn: (payload: AssureurPayload) => assureursApi.createAdmin(payload),
    onSuccess: () => {
      setFeedback({ type: 'success', message: 'Assureur créé avec succès.' })
      queryClient.invalidateQueries({ queryKey: ['admin-assureurs'] })
      resetForm()
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Impossible de créer cet assureur.'
      setFeedback({ type: 'error', message })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: AssureurPayload }) =>
      assureursApi.updateAdmin(id, payload),
    onSuccess: () => {
      setFeedback({ type: 'success', message: 'Assureur mis à jour.' })
      queryClient.invalidateQueries({ queryKey: ['admin-assureurs'] })
    },
    onError: (error: unknown) => {
      const message =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Mise à jour impossible.'
      setFeedback({ type: 'error', message })
    },
  })

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const payload = asPayload()
    if (!payload) {
      return
    }
    if (selectedAssureur) {
      updateMutation.mutate({ id: selectedAssureur.id, payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <div className="admin-assureurs-page">
      <header className="page-header">
        <div>
          <h1>Gestion des assureurs partenaires</h1>
          <p>Créez les assureurs référencés par Mobility Health et assignez leur agent comptable.</p>
        </div>
        <button type="button" className="btn-secondary" onClick={resetForm} disabled={!selectedAssureur}>
          + Nouvel assureur
        </button>
      </header>

      <div className="assureurs-grid">
        <section className="assureurs-list-panel">
          <h2>Assureurs ({assureurs.length})</h2>
          {isLoading ? (
            <div className="empty-state">Chargement...</div>
          ) : assureurs.length === 0 ? (
            <div className="empty-state">Aucun assureur enregistré pour le moment.</div>
          ) : (
            <div className="assureurs-list">
              {assureurs.map((assureur) => (
                <button
                  key={assureur.id}
                  type="button"
                  className={`assureur-card ${selectedAssureur?.id === assureur.id ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedAssureur(assureur)
                    setFeedback(null)
                  }}
                >
                  <div>
                    <strong>{assureur.nom}</strong>
                    <span>{assureur.pays}</span>
                  </div>
                  <div className="assureur-meta">
                    <span>
                      {assureur.agent_comptable
                        ? assureur.agent_comptable.full_name || assureur.agent_comptable.username
                        : 'Agent non assigné'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="assureur-form-panel">
          <h2>{selectedAssureur ? 'Mettre à jour l’assureur' : 'Créer un assureur'}</h2>
          {feedback && (
            <div className={`alert ${feedback.type === 'error' ? 'alert-error' : 'alert-success'}`}>
              {feedback.message}
            </div>
          )}
          <form className="assureur-form" onSubmit={handleSubmit}>
            <div className="form-row">
              <label>
                Nom *
                <input
                  type="text"
                  value={formState.nom}
                  onChange={(e) => handleInputChange('nom', e.target.value)}
                  placeholder="Ex: AXA Afrique"
                  required
                />
              </label>
              <label>
                Pays *
                <input
                  type="text"
                  value={formState.pays}
                  onChange={(e) => handleInputChange('pays', e.target.value)}
                  required
                />
              </label>
            </div>

            <label>
              Adresse
              <input
                type="text"
                value={formState.adresse}
                onChange={(e) => handleInputChange('adresse', e.target.value)}
                placeholder="Adresse du siège"
              />
            </label>

            <div className="form-row">
              <label>
                Téléphone
                <input
                  type="text"
                  value={formState.telephone}
                  onChange={(e) => handleInputChange('telephone', e.target.value)}
                  placeholder="+225 ..."
                />
              </label>
              <label>
                URL du logo
                <input
                  type="url"
                  value={formState.logo_url}
                  onChange={(e) => handleInputChange('logo_url', e.target.value)}
                  placeholder="https://..."
                />
              </label>
            </div>

            <label>
              Agent comptable assurance
              <select
                value={formState.agent_comptable_id}
                onChange={(e) => handleInputChange('agent_comptable_id', e.target.value)}
              >
                <option value="">Non assigné</option>
                {accountants.map((user: UserSummary) => (
                  <option key={user.id} value={user.id}>
                    {(user.full_name || user.username) ?? user.email}
                  </option>
                ))}
              </select>
            </label>

            {formState.logo_url && (
              <div className="logo-preview">
                <p>Aperçu du logo</p>
                <img src={formState.logo_url} alt="Logo assureur" />
              </div>
            )}

            <div className="form-actions">
              <button
                type="submit"
                className="btn-primary"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {selectedAssureur ? 'Mettre à jour' : 'Créer'}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  )
}


