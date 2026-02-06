import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { sosApi } from '../api/sos'
import './SOSPage.css'

interface Position {
  latitude: number
  longitude: number
  address?: string
}

export default function SOSPage() {
  const navigate = useNavigate()
  const [position, setPosition] = useState<Position | null>(null)
  const [isGettingLocation, setIsGettingLocation] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [priorite, setPriorite] = useState('normale')
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)

  // Obtenir la géolocalisation automatique au chargement de la page
  useEffect(() => {
    getCurrentLocation()
  }, [])

  const getCurrentLocation = () => {
    setIsGettingLocation(true)
    setLocationError(null)

    if (!navigator.geolocation) {
      setLocationError('La géolocalisation n\'est pas supportée par votre navigateur')
      setIsGettingLocation(false)
      return
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const lat = position.coords.latitude
        const lon = position.coords.longitude

        // Essayer d'obtenir l'adresse depuis les coordonnées (reverse geocoding)
        let address = null
        try {
          // Utiliser un service de géocodage inverse (ex: Nominatim)
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`
          )
          const data = await response.json()
          if (data && data.display_name) {
            address = data.display_name
          }
        } catch (error) {
          console.error('Erreur lors de la récupération de l\'adresse:', error)
        }

        setPosition({
          latitude: lat,
          longitude: lon,
          address: address || undefined,
        })
        setIsGettingLocation(false)
      },
      (error) => {
        let errorMessage = 'Impossible d\'obtenir votre position'
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Permission de géolocalisation refusée. Veuillez autoriser l\'accès à votre position.'
            break
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Position non disponible'
            break
          case error.TIMEOUT:
            errorMessage = 'Délai d\'attente dépassé lors de la récupération de la position'
            break
        }
        setLocationError(errorMessage)
        setIsGettingLocation(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }

  const triggerSOSMutation = useMutation({
    mutationFn: sosApi.trigger,
    onSuccess: (alerte) => {
      // Rediriger vers la page de suivi du sinistre
      navigate(`/sinistre/${alerte.id}`)
    },
    onError: (error: any) => {
      alert(`Erreur lors de l'envoi de l'alerte: ${error.response?.data?.detail || error.message}`)
      setShowConfirmDialog(false)
    },
  })

  const handleTriggerSOS = () => {
    if (!position) {
      alert('Position GPS non disponible. Veuillez réessayer.')
      return
    }

    if (!showConfirmDialog) {
      setShowConfirmDialog(true)
      return
    }

    // Envoyer l'alerte
    triggerSOSMutation.mutate({
      latitude: position.latitude,
      longitude: position.longitude,
      adresse: position.address,
      description: description || undefined,
      priorite: priorite,
    })
  }

  const handleCancel = () => {
    setShowConfirmDialog(false)
  }

  return (
    <div className="sos-page">
      <div className="sos-container">
        <div className="sos-header">
          <h1>Service d'Urgence SOS</h1>
          <p className="subtitle">En cas d'urgence médicale, appuyez sur le bouton ALERTE</p>
        </div>

        {/* Statut de la géolocalisation */}
        <div className="location-status">
          {isGettingLocation ? (
            <div className="location-loading">
              <div className="spinner"></div>
              <p>Récupération de votre position GPS...</p>
            </div>
          ) : locationError ? (
            <div className="location-error">
              <span className="error-icon">⚠️</span>
              <p>{locationError}</p>
              <button onClick={getCurrentLocation} className="btn-retry">
                Réessayer
              </button>
            </div>
          ) : position ? (
            <div className="location-success">
              <span className="success-icon">✅</span>
              <div className="location-info">
                <p><strong>Position GPS détectée</strong></p>
                <p className="coordinates">
                  {position.latitude.toFixed(6)}, {position.longitude.toFixed(6)}
                </p>
                {position.address && (
                  <p className="address">📍 {position.address}</p>
                )}
                <button onClick={getCurrentLocation} className="btn-refresh-location">
                  Actualiser la position
                </button>
              </div>
            </div>
          ) : null}
        </div>

        {/* Description et priorité (optionnel) */}
        {!showConfirmDialog && position && (
          <div className="alerte-details">
            <div className="form-group">
              <label htmlFor="description">Description de l'urgence (optionnel)</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Décrivez brièvement la situation..."
                rows={3}
                className="form-control"
              />
            </div>

            <div className="form-group">
              <label htmlFor="priorite">Priorité</label>
              <select
                id="priorite"
                value={priorite}
                onChange={(e) => setPriorite(e.target.value)}
                className="form-control"
              >
                <option value="faible">Faible</option>
                <option value="normale">Normale</option>
                <option value="elevee">Élevée</option>
                <option value="critique">Critique</option>
              </select>
            </div>
          </div>
        )}

        {/* Dialog de confirmation */}
        {showConfirmDialog && (
          <div className="confirm-dialog">
            <div className="dialog-content">
              <h2>Confirmer l'alerte SOS</h2>
              <p>
                Vous êtes sur le point de déclencher une alerte SOS. 
                Votre position GPS sera transmise au centre d'urgence.
              </p>
              {description && (
                <div className="dialog-description">
                  <strong>Description :</strong>
                  <p>{description}</p>
                </div>
              )}
              <div className="dialog-actions">
                <button onClick={handleCancel} className="btn-cancel">
                  Annuler
                </button>
                <button
                  onClick={handleTriggerSOS}
                  disabled={triggerSOSMutation.isPending}
                  className="btn-confirm-alert"
                >
                  {triggerSOSMutation.isPending ? 'Envoi en cours...' : 'Confirmer l\'alerte'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bouton ALERTE principal */}
        {!showConfirmDialog && (
          <div className="alert-button-container">
            <button
              onClick={handleTriggerSOS}
              disabled={!position || isGettingLocation || triggerSOSMutation.isPending}
              className={`btn-alert ${!position || isGettingLocation ? 'disabled' : ''}`}
            >
              <span className="alert-icon">🚨</span>
              <span className="alert-text">ALERTE</span>
              <span className="alert-subtitle">Appuyez pour déclencher</span>
            </button>
          </div>
        )}

        {/* Informations importantes */}
        <div className="info-box">
          <h3>⚠️ Important</h3>
          <ul>
            <li>Cette fonction est réservée aux urgences médicales réelles</li>
            <li>Votre position GPS sera automatiquement transmise</li>
            <li>Un agent SOS vous contactera dans les plus brefs délais</li>
            <li>En cas d'urgence vitale, composez également le 15 (SAMU) ou le 112</li>
          </ul>
        </div>
      </div>
    </div>
  )
}




