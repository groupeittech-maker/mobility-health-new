import { FormEvent, useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { hospitalsApi, HospitalPayload, ReceptionistPayload } from '../api/hospitals'
import type { HospitalMarker, HospitalReceptionist } from '../types'
import './AdminHospitalsPage.css'

const DEFAULT_CENTER = {
  lat: 5.347,
  lng: -4.007,
}

type HospitalFormState = {
  nom: string
  adresse: string
  ville: string
  pays: string
  code_postal: string
  telephone: string
  email: string
  latitude: string
  longitude: string
  specialites: string
  capacite_lits: string
  notes: string
  est_actif: boolean
}

type ReceptionistFormState = {
  full_name: string
  email: string
  username: string
  password: string
  is_active: boolean
}

const emptyHospitalForm: HospitalFormState = {
  nom: '',
  adresse: '',
  ville: '',
  pays: 'Côte d\'Ivoire',
  code_postal: '',
  telephone: '',
  email: '',
  latitude: DEFAULT_CENTER.lat.toFixed(6),
  longitude: DEFAULT_CENTER.lng.toFixed(6),
  specialites: '',
  capacite_lits: '',
  notes: '',
  est_actif: true,
}

const emptyReceptionistForm: ReceptionistFormState = {
  full_name: '',
  email: '',
  username: '',
  password: '',
  is_active: true,
}

type MapClickHelperProps = {
  onSelect: (lat: number, lng: number) => void
}

function MapClickHelper({ onSelect }: MapClickHelperProps) {
  useMapEvents({
    click(event) {
      onSelect(event.latlng.lat, event.latlng.lng)
    },
  })
  return null
}

export default function AdminHospitalsPage() {
  const queryClient = useQueryClient()
  const [selectedHospitalId, setSelectedHospitalId] = useState<number | null>(null)
  const [hospitalForm, setHospitalForm] = useState<HospitalFormState>(emptyHospitalForm)
  const [receptionistForm, setReceptionistForm] = useState<ReceptionistFormState>(emptyReceptionistForm)
  const [hospitalFormError, setHospitalFormError] = useState<string | null>(null)
  const [receptionistFeedback, setReceptionistFeedback] = useState<{ type: 'error' | 'success'; message: string } | null>(null)

  const { data: hospitals = [], isLoading: hospitalsLoading } = useQuery({
    queryKey: ['hospitals'],
    queryFn: hospitalsApi.getAll,
  })

  const { data: markers = [] } = useQuery({
    queryKey: ['hospital-markers'],
    queryFn: hospitalsApi.getMapMarkers,
  })

  const { data: receptionists = [], isLoading: receptionistsLoading } = useQuery({
    queryKey: ['hospital-receptionists', selectedHospitalId],
    queryFn: () => hospitalsApi.getReceptionists(selectedHospitalId!),
    enabled: Boolean(selectedHospitalId),
  })

  useEffect(() => {
    if (!selectedHospitalId && hospitals.length > 0) {
      setSelectedHospitalId(hospitals[0].id)
    }
  }, [hospitals, selectedHospitalId])

  const selectedHospital = useMemo(
    () => hospitals.find((hospital) => hospital.id === selectedHospitalId) ?? null,
    [hospitals, selectedHospitalId],
  )

  const mapCenter = useMemo(() => {
    if (selectedHospital) {
      return {
        lat: Number(selectedHospital.latitude),
        lng: Number(selectedHospital.longitude),
      }
    }
    if (markers.length > 0) {
      return {
        lat: Number(markers[0].latitude),
        lng: Number(markers[0].longitude),
      }
    }
    return DEFAULT_CENTER
  }, [selectedHospital, markers])

  const createHospitalMutation = useMutation({
    mutationFn: (payload: HospitalPayload) => hospitalsApi.create(payload),
    onSuccess: () => {
      setHospitalForm(emptyHospitalForm)
      setHospitalFormError(null)
      queryClient.invalidateQueries({ queryKey: ['hospitals'] })
      queryClient.invalidateQueries({ queryKey: ['hospital-markers'] })
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Impossible de créer cet hôpital.'
      setHospitalFormError(detail)
    },
  })

  const createReceptionistMutation = useMutation({
    mutationFn: (payload: ReceptionistPayload) =>
      hospitalsApi.createReceptionist(selectedHospitalId!, payload),
    onSuccess: () => {
      setReceptionistForm(emptyReceptionistForm)
      setReceptionistFeedback({ type: 'success', message: 'Réceptionniste créé avec succès.' })
      queryClient.invalidateQueries({ queryKey: ['hospital-receptionists', selectedHospitalId] })
    },
    onError: (error: unknown) => {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Impossible de créer ce réceptionniste.'
      setReceptionistFeedback({ type: 'error', message: detail })
    },
  })

  const handleHospitalInputChange = (field: keyof HospitalFormState, value: string | boolean) => {
    setHospitalForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleReceptionistInputChange = (field: keyof ReceptionistFormState, value: string | boolean) => {
    setReceptionistFeedback(null)
    setReceptionistForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleHospitalSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setHospitalFormError(null)

    const latitude = Number(hospitalForm.latitude)
    const longitude = Number(hospitalForm.longitude)

    if (Number.isNaN(latitude) || Number.isNaN(longitude)) {
      setHospitalFormError('Veuillez saisir des coordonnées GPS valides.')
      return
    }

    const payload: HospitalPayload = {
      nom: hospitalForm.nom.trim(),
      adresse: hospitalForm.adresse.trim() || undefined,
      ville: hospitalForm.ville.trim() || undefined,
      pays: hospitalForm.pays.trim() || undefined,
      code_postal: hospitalForm.code_postal.trim() || undefined,
      telephone: hospitalForm.telephone.trim() || undefined,
      email: hospitalForm.email.trim() || undefined,
      latitude,
      longitude,
      est_actif: hospitalForm.est_actif,
      specialites: hospitalForm.specialites.trim() || undefined,
      capacite_lits: hospitalForm.capacite_lits ? Number(hospitalForm.capacite_lits) : undefined,
      notes: hospitalForm.notes.trim() || undefined,
    }

    if (!payload.nom) {
      setHospitalFormError('Le nom de l’hôpital est obligatoire.')
      return
    }

    createHospitalMutation.mutate(payload)
  }

  const handleReceptionistSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setReceptionistFeedback(null)

    if (!selectedHospitalId) {
      setReceptionistFeedback({ type: 'error', message: 'Sélectionnez un hôpital.' })
      return
    }

    if (receptionistForm.password.length < 8) {
      setReceptionistFeedback({
        type: 'error',
        message: 'Le mot de passe doit contenir au moins 8 caractères.',
      })
      return
    }

    const payload: ReceptionistPayload = {
      email: receptionistForm.email.trim(),
      username: receptionistForm.username.trim(),
      password: receptionistForm.password,
      full_name: receptionistForm.full_name.trim() || undefined,
      is_active: receptionistForm.is_active,
    }

    if (!payload.email || !payload.username) {
      setReceptionistFeedback({ type: 'error', message: "Email et identifiant sont requis." })
      return
    }

    createReceptionistMutation.mutate(payload)
  }

  const handleMapLocation = (lat: number, lng: number) => {
    setHospitalForm((prev) => ({
      ...prev,
      latitude: lat.toFixed(6),
      longitude: lng.toFixed(6),
    }))
  }

  const toNumber = (value: number | string): number => (typeof value === 'number' ? value : Number(value))

  return (
    <div className="admin-hospitals-page">
      <header className="page-header">
        <div>
          <h1>Hôpitaux affiliés Mobility Health</h1>
          <p>Ajoutez des partenaires, localisez-les sur la carte et gérez leurs équipes d’accueil.</p>
        </div>
      </header>

      <div className="admin-hospitals-grid">
        <section className="panel hospital-list-panel">
          <div className="panel-header">
            <div>
              <h2>Hôpitaux référencés ({hospitals.length})</h2>
              <p>Sélectionnez un hôpital pour voir ses informations et ses réceptionnistes.</p>
            </div>
          </div>
          <div className="hospital-list">
            {hospitalsLoading ? (
              <div className="empty-state">Chargement des hôpitaux...</div>
            ) : hospitals.length === 0 ? (
              <div className="empty-state">
                Aucun hôpital enregistré pour le moment.<br />
                Utilisez le formulaire pour en créer un premier.
              </div>
            ) : (
              hospitals.map((hospital) => (
                <button
                  type="button"
                  key={hospital.id}
                  className={`hospital-card ${selectedHospitalId === hospital.id ? 'selected' : ''}`}
                  onClick={() => setSelectedHospitalId(hospital.id)}
                >
                  <div>
                    <h3>{hospital.nom}</h3>
                    <p>
                      {[hospital.ville, hospital.pays].filter(Boolean).join(', ') || 'Localisation indisponible'}
                    </p>
                  </div>
                  <span className={`status-badge ${hospital.est_actif ? 'status-active' : 'status-inactive'}`}>
                    {hospital.est_actif ? 'Actif' : 'Inactif'}
                  </span>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="panel hospital-form-panel">
          <div className="panel-header">
            <div>
              <h2>Créer un hôpital affilié</h2>
              <p>Renseignez l’essentiel puis ajustez sa position en cliquant sur la carte.</p>
            </div>
          </div>
          {hospitalFormError && <div className="alert alert-error">{hospitalFormError}</div>}
          <form className="hospital-form" onSubmit={handleHospitalSubmit}>
            <div className="form-row">
              <label>
                Nom de l’hôpital *
                <input
                  type="text"
                  value={hospitalForm.nom}
                  onChange={(event) => handleHospitalInputChange('nom', event.target.value)}
                  placeholder="Centre hospitalier..."
                  required
                />
              </label>
              <label>
                Statut
                <select
                  value={hospitalForm.est_actif ? 'true' : 'false'}
                  onChange={(event) => handleHospitalInputChange('est_actif', event.target.value === 'true')}
                >
                  <option value="true">Actif</option>
                  <option value="false">Inactif</option>
                </select>
              </label>
            </div>

            <label>
              Adresse
              <input
                type="text"
                value={hospitalForm.adresse}
                onChange={(event) => handleHospitalInputChange('adresse', event.target.value)}
                placeholder="Rue, quartier..."
              />
            </label>

            <div className="form-row">
              <label>
                Ville
                <input
                  type="text"
                  value={hospitalForm.ville}
                  onChange={(event) => handleHospitalInputChange('ville', event.target.value)}
                />
              </label>
              <label>
                Pays
                <input
                  type="text"
                  value={hospitalForm.pays}
                  onChange={(event) => handleHospitalInputChange('pays', event.target.value)}
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                Code postal
                <input
                  type="text"
                  value={hospitalForm.code_postal}
                  onChange={(event) => handleHospitalInputChange('code_postal', event.target.value)}
                />
              </label>
              <label>
                Téléphone
                <input
                  type="text"
                  value={hospitalForm.telephone}
                  onChange={(event) => handleHospitalInputChange('telephone', event.target.value)}
                />
              </label>
            </div>

            <label>
              Email
              <input
                type="email"
                value={hospitalForm.email}
                onChange={(event) => handleHospitalInputChange('email', event.target.value)}
              />
            </label>

            <div className="form-row">
              <label>
                Latitude *
                <input
                  type="text"
                  value={hospitalForm.latitude}
                  onChange={(event) => handleHospitalInputChange('latitude', event.target.value)}
                  required
                />
              </label>
              <label>
                Longitude *
                <input
                  type="text"
                  value={hospitalForm.longitude}
                  onChange={(event) => handleHospitalInputChange('longitude', event.target.value)}
                  required
                />
              </label>
            </div>

            <label>
              Spécialités
              <textarea
                value={hospitalForm.specialites}
                onChange={(event) => handleHospitalInputChange('specialites', event.target.value)}
                placeholder="Urgences, cardiologie..."
                rows={2}
              />
            </label>

            <div className="form-row">
              <label>
                Capacité (lits)
                <input
                  type="number"
                  min={0}
                  value={hospitalForm.capacite_lits}
                  onChange={(event) => handleHospitalInputChange('capacite_lits', event.target.value)}
                />
              </label>
              <label>
                Notes internes
                <textarea
                  value={hospitalForm.notes}
                  onChange={(event) => handleHospitalInputChange('notes', event.target.value)}
                  rows={2}
                />
              </label>
            </div>

            <button type="submit" className="btn btn-primary" disabled={createHospitalMutation.isPending}>
              {createHospitalMutation.isPending ? 'Enregistrement...' : 'Créer l’hôpital'}
            </button>
          </form>
        </section>

        <section className="panel map-panel">
          <div className="panel-header">
            <div>
              <h2>Carte des hôpitaux</h2>
              <p>Cliquez pour repositionner le prochain hôpital à enregistrer.</p>
            </div>
          </div>
          <div className="map-wrapper">
            <MapContainer center={[mapCenter.lat, mapCenter.lng]} zoom={7} scrollWheelZoom className="hospital-map">
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" />
              {markers.map((marker: HospitalMarker) => (
                <CircleMarker
                  key={marker.id}
                  center={[toNumber(marker.latitude), toNumber(marker.longitude)]}
                  pathOptions={{
                    color: marker.id === selectedHospitalId ? '#2563eb' : '#0f172a',
                    fillOpacity: 0.8,
                  }}
                  radius={marker.id === selectedHospitalId ? 10 : 7}
                  eventHandlers={{
                    click: () => setSelectedHospitalId(marker.id),
                  }}
                >
                  <Popup>
                    <strong>{marker.nom}</strong>
                    <br />
                    {[marker.ville, marker.pays].filter(Boolean).join(', ')}
                    {marker.specialites && (
                      <>
                        <br />
                        <em>{marker.specialites}</em>
                      </>
                    )}
                  </Popup>
                </CircleMarker>
              ))}
              <MapClickHelper onSelect={handleMapLocation} />
            </MapContainer>
          </div>
          <p className="map-hint">Les coordonnées sélectionnées alimentent automatiquement le formulaire de création.</p>
        </section>

        <section className="panel reception-panel">
          <div className="panel-header">
            <div>
              <h2>Réceptionnistes</h2>
              <p>Chaque réceptionniste reçoit un accès limité au tableau de bord hôpital.</p>
            </div>
          </div>

          {!selectedHospital ? (
            <div className="empty-state">Sélectionnez un hôpital pour gérer ses réceptionnistes.</div>
          ) : (
            <>
              <div className="selected-hospital-banner">
                <div>
                  <strong>{selectedHospital.nom}</strong>
                  <span>{[selectedHospital.ville, selectedHospital.pays].filter(Boolean).join(', ')}</span>
                </div>
                <span className={`status-badge ${selectedHospital.est_actif ? 'status-active' : 'status-inactive'}`}>
                  {selectedHospital.est_actif ? 'Ouvert' : 'Inactif'}
                </span>
              </div>

              <div className="receptionists-list">
                {receptionistsLoading ? (
                  <div className="empty-state">Chargement des réceptionnistes...</div>
                ) : receptionists.length === 0 ? (
                  <div className="empty-state">Pas encore de réceptionnistes pour cet hôpital.</div>
                ) : (
                  receptionists.map((user: HospitalReceptionist) => (
                    <div key={user.id} className="receptionist-card">
                      <div>
                        <strong>{user.full_name || user.username}</strong>
                        <span>{user.email}</span>
                      </div>
                      <span className={`status-badge ${user.is_active ? 'status-active' : 'status-inactive'}`}>
                        {user.is_active ? 'Actif' : 'Inactif'}
                      </span>
                    </div>
                  ))
                )}
              </div>

              <div className="receptionist-form-wrapper">
                {receptionistFeedback && (
                  <div className={`alert ${receptionistFeedback.type === 'error' ? 'alert-error' : 'alert-success'}`}>
                    {receptionistFeedback.message}
                  </div>
                )}
                <form className="receptionist-form" onSubmit={handleReceptionistSubmit}>
                  <div className="form-row">
                    <label>
                      Nom complet
                      <input
                        type="text"
                        value={receptionistForm.full_name}
                        onChange={(event) => handleReceptionistInputChange('full_name', event.target.value)}
                        placeholder="Prénom Nom"
                      />
                    </label>
                    <label>
                      Actif
                      <select
                        value={receptionistForm.is_active ? 'true' : 'false'}
                        onChange={(event) => handleReceptionistInputChange('is_active', event.target.value === 'true')}
                      >
                        <option value="true">Oui</option>
                        <option value="false">Non</option>
                      </select>
                    </label>
                  </div>

                  <label>
                    Email *
                    <input
                      type="email"
                      value={receptionistForm.email}
                      onChange={(event) => handleReceptionistInputChange('email', event.target.value)}
                      required
                    />
                  </label>

                  <label>
                    Identifiant *
                    <input
                      type="text"
                      value={receptionistForm.username}
                      onChange={(event) => handleReceptionistInputChange('username', event.target.value)}
                      required
                    />
                  </label>

                  <label>
                    Mot de passe (min. 8 caractères) *
                    <input
                      type="password"
                      value={receptionistForm.password}
                      onChange={(event) => handleReceptionistInputChange('password', event.target.value)}
                      required
                      minLength={8}
                    />
                  </label>

                  <button
                    type="submit"
                    className="btn btn-secondary"
                    disabled={createReceptionistMutation.isPending}
                  >
                    {createReceptionistMutation.isPending ? 'Création...' : 'Ajouter un réceptionniste'}
                  </button>
                </form>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}


