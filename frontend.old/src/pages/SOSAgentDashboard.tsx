import { useState, useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { sosApi } from '../api/sos'
import { Alerte } from '../types'
import './SOSAgentDashboard.css'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap } from 'react-leaflet'
import L, { LatLngExpression, LatLngBoundsExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface ActionLog {
  id: string
  timestamp: string
  type: string
  message: string
  alerte_id?: number
  sinistre_id?: number
}

export default function SOSAgentDashboard() {
  const [selectedAlerte, setSelectedAlerte] = useState<Alerte | null>(null)
  const [actionLogs, setActionLogs] = useState<ActionLog[]>([])
  const [isConnected, setIsConnected] = useState(false)

  const { data: alertes = [], refetch } = useQuery({
    queryKey: ['alertes'],
    queryFn: () => sosApi.getAlertes(),
    refetchInterval: 5000, // Rafraîchir toutes les 5 secondes
  })

  const activeAlertes = useMemo(
    () => alertes.filter(a => a.statut === 'en_attente' || a.statut === 'en_cours'),
    [alertes],
  )

  const alertsWithCoordinates = useMemo(
    () => activeAlertes.filter(hasValidCoordinates),
    [activeAlertes],
  )

  const hospitalMarkers = useMemo(() => {
    const map = new Map<number, { id: number; lat: number; lng: number; label: string }>()
    alertsWithCoordinates.forEach((alerte) => {
      const hospital = alerte.assigned_hospital
      if (!hospital || !hasValidCoordinates(hospital)) {
        return
      }
      if (!map.has(hospital.id)) {
        map.set(hospital.id, {
          id: hospital.id,
          lat: hospital.latitude,
          lng: hospital.longitude,
          label: hospital.nom,
        })
      }
    })
    return Array.from(map.values())
  }, [alertsWithCoordinates])

  const mapBounds = useMemo<LatLngBoundsExpression | null>(() => {
    const points: LatLngExpression[] = []
    alertsWithCoordinates.forEach((alerte) => {
      points.push([alerte.latitude, alerte.longitude])
      if (alerte.assigned_hospital && hasValidCoordinates(alerte.assigned_hospital)) {
        points.push([alerte.assigned_hospital.latitude, alerte.assigned_hospital.longitude])
      }
    })
    return points.length ? L.latLngBounds(points) : null
  }, [alertsWithCoordinates])

  const defaultCenter: LatLngExpression = useMemo(() => {
    if (alertsWithCoordinates.length > 0) {
      return [alertsWithCoordinates[0].latitude, alertsWithCoordinates[0].longitude]
    }
    return DEFAULT_CENTER
  }, [alertsWithCoordinates])

  // Connexion WebSocket
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const wsUrl = `ws://localhost:8000/ws/sos?token=${token}`
    const websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      setIsConnected(true)
      addActionLog('connected', 'Connexion WebSocket établie')
    }

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'new_alert') {
          addActionLog('new_alert', `Nouvelle alerte: ${data.numero_alerte}`, data.alerte_id, data.sinistre_id)
          refetch() // Rafraîchir la liste des alertes
        } else if (data.type === 'connected') {
          addActionLog('connected', data.message)
        }
      } catch (e) {
        console.error('Erreur parsing WebSocket message:', e)
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
      addActionLog('error', 'Erreur de connexion WebSocket')
    }

    websocket.onclose = () => {
      setIsConnected(false)
      addActionLog('disconnected', 'Connexion WebSocket fermée')
    }

    return () => {
      websocket.close()
    }
  }, [refetch])

  const addActionLog = (type: string, message: string, alerteId?: number, sinistreId?: number) => {
    const log: ActionLog = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      type,
      message,
      alerte_id: alerteId,
      sinistre_id: sinistreId,
    }
    setActionLogs(prev => [log, ...prev].slice(0, 50)) // Garder les 50 derniers
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  const getPriorityColor = (priorite: string) => {
    switch (priorite) {
      case 'critique':
        return '#dc3545'
      case 'elevee':
        return '#fd7e14'
      case 'normale':
        return '#ffc107'
      default:
        return '#6c757d'
    }
  }

  useEffect(() => {
    if (!selectedAlerte) {
      return
    }
    const updated = alertes.find((alert) => alert.id === selectedAlerte.id)
    if (updated) {
      setSelectedAlerte(updated)
    } else if (!activeAlertes.find((alert) => alert.id === selectedAlerte.id)) {
      setSelectedAlerte(null)
    }
  }, [alertes, activeAlertes, selectedAlerte])

  const selectedHasCoordinates =
    selectedAlerte && hasValidCoordinates(selectedAlerte)

  return (
    <div className="sos-agent-dashboard">
      <div className="dashboard-header">
        <h1>Dashboard Agent Sinistre</h1>
        <div className="header-info">
          <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Connecté' : '○ Déconnecté'}
          </span>
          <span className="alertes-count">{activeAlertes.length} alerte(s) active(s)</span>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="map-section">
          <h2>Carte des alertes</h2>
          <div className="map-container">
            {activeAlertes.length === 0 ? (
              <div className="map-empty-state">
                <p>Aucune alerte active à afficher.</p>
              </div>
            ) : (
              <MapContainer
                center={defaultCenter}
                zoom={MAP_DEFAULT_ZOOM}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom
              >
                <TileLayer
                  attribution="&copy; OpenStreetMap contributors"
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {mapBounds && <MapBoundsHelper bounds={mapBounds} />}
                {alertsWithCoordinates.map((alerte) => (
                  <CircleMarker
                    key={`alert-${alerte.id}`}
                    center={[alerte.latitude, alerte.longitude]}
                    pathOptions={ALERT_MARKER_STYLE}
                    eventHandlers={{
                      click: () => setSelectedAlerte(alerte),
                    }}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>{alerte.numero_alerte}</strong>
                        <p>{alerte.description || 'Aucune description'}</p>
                        <p>
                          {formatCoordinates(alerte.latitude, alerte.longitude)}
                        </p>
                        {alerte.assigned_hospital && (
                          <p>
                            🏥 {alerte.assigned_hospital.nom}
                            {isFiniteNumber(alerte.distance_to_hospital_km) && (
                              <span className="map-badge">
                                {alerte.distance_to_hospital_km!.toFixed(1)} km
                              </span>
                            )}
                          </p>
                        )}
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
                {hospitalMarkers.map((hospital) => (
                  <CircleMarker
                    key={`hospital-${hospital.id}`}
                    center={[hospital.lat, hospital.lng]}
                    pathOptions={HOSPITAL_MARKER_STYLE}
                  >
                    <Popup>
                      <div className="map-popup">
                        <strong>{hospital.label}</strong>
                      </div>
                    </Popup>
                  </CircleMarker>
                ))}
                {alertsWithCoordinates.map((alerte) => {
                  if (
                    !alerte.assigned_hospital ||
                    !hasValidCoordinates(alerte.assigned_hospital)
                  ) {
                    return null
                  }
                  return (
                    <Polyline
                      key={`link-${alerte.id}-${alerte.assigned_hospital.id}`}
                      positions={[
                        [alerte.latitude, alerte.longitude],
                        [alerte.assigned_hospital.latitude, alerte.assigned_hospital.longitude],
                      ]}
                      pathOptions={HOSPITAL_LINK_STYLE}
                    />
                  )
                })}
              </MapContainer>
            )}
          </div>
          <div className="map-legend">
            <span className="map-legend-item">
              <span className="map-dot alert-dot" /> Alerte
            </span>
            <span className="map-legend-item">
              <span className="map-dot hospital-dot" /> Hôpital assigné
            </span>
            <span className="map-legend-item">
              <span className="map-line" /> Liaison / distance
            </span>
          </div>

          {activeAlertes.length > 0 && (
            <div className="alertes-list-map">
              <h3>Alertes sur la carte</h3>
              {activeAlertes.map((alerte) => (
                <div
                  key={alerte.id}
                  className={`alerte-marker ${selectedAlerte?.id === alerte.id ? 'selected' : ''}`}
                  onClick={() => setSelectedAlerte(alerte)}
                  style={{ borderLeftColor: getPriorityColor(alerte.priorite) }}
                >
                  <div className="marker-header">
                    <strong>{alerte.numero_alerte}</strong>
                    <span className="priority-badge" style={{ backgroundColor: getPriorityColor(alerte.priorite) }}>
                      {alerte.priorite}
                    </span>
                  </div>
                  <div className="marker-body">
                    <p>{alerte.description || 'Aucune description'}</p>
                    <p className="coordinates">
                      {hasValidCoordinates(alerte)
                        ? `📍 ${formatCoordinates(alerte.latitude, alerte.longitude)}`
                        : '📍 Coordonnées indisponibles'}
                    </p>
                    {alerte.assigned_hospital && (
                      <p className="hospital-line">
                        🏥 {alerte.assigned_hospital.nom}
                        {isFiniteNumber(alerte.distance_to_hospital_km) && (
                          <span className="map-badge">
                            {alerte.distance_to_hospital_km!.toFixed(1)} km
                          </span>
                        )}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="details-section">
          {selectedAlerte ? (
            <>
              <div className="alerte-details">
                <h2>Alerte #{selectedAlerte.numero_alerte}</h2>
                <div className="detail-item">
                  <strong>Statut:</strong> {selectedAlerte.statut}
                </div>
                <div className="detail-item">
                  <strong>Priorité:</strong>
                  <span className="priority-badge" style={{ backgroundColor: getPriorityColor(selectedAlerte.priorite) }}>
                    {selectedAlerte.priorite}
                  </span>
                </div>
                <div className="detail-item">
                  <strong>Date:</strong> {formatDate(selectedAlerte.created_at)}
                </div>
                <div className="detail-item">
                  <strong>Coordonnées:</strong>
                  {selectedHasCoordinates ? (
                    <div className="location-info">
                      <span>{formatCoordinates(selectedAlerte.latitude, selectedAlerte.longitude, 6)}</span>
                      <a
                        href={`https://www.google.com/maps?q=${selectedAlerte.latitude},${selectedAlerte.longitude}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Ouvrir dans Maps
                      </a>
                    </div>
                  ) : (
                    <span>Non renseignées</span>
                  )}
                </div>
                {selectedAlerte.assigned_hospital && (
                  <div className="detail-item">
                    <strong>Hôpital assigné</strong>
                    <p>{selectedAlerte.assigned_hospital.nom}</p>
                    {isFiniteNumber(selectedAlerte.distance_to_hospital_km) && (
                      <p className="muted">
                        Distance estimée : {selectedAlerte.distance_to_hospital_km!.toFixed(1)} km
                      </p>
                    )}
                  </div>
                )}
                {selectedAlerte.adresse && (
                  <div className="detail-item">
                    <strong>Adresse:</strong> {selectedAlerte.adresse}
                  </div>
                )}
                {selectedAlerte.description && (
                  <div className="detail-item">
                    <strong>Description:</strong>
                    <p>{selectedAlerte.description}</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="no-selection">
              <p>Sélectionnez une alerte pour voir les détails</p>
            </div>
          )}

          <div className="action-log">
            <h2>Fil d'action temps réel</h2>
            <div className="log-container">
              {actionLogs.length === 0 ? (
                <p className="no-logs">Aucune action enregistrée</p>
              ) : (
                actionLogs.map((log) => (
                  <div key={log.id} className={`log-entry log-${log.type}`}>
                    <div className="log-time">{formatDate(log.timestamp)}</div>
                    <div className="log-message">{log.message}</div>
                    {log.alerte_id && (
                      <div className="log-meta">Alerte ID: {log.alerte_id}</div>
                    )}
                    {log.sinistre_id && (
                      <div className="log-meta">Sinistre ID: {log.sinistre_id}</div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const DEFAULT_CENTER: LatLngExpression = [5.347, -4.007]
const MAP_DEFAULT_ZOOM = 6

const ALERT_MARKER_STYLE = {
  color: '#e63946',
  weight: 1,
  fillOpacity: 0.85,
  radius: 10,
}

const HOSPITAL_MARKER_STYLE = {
  color: '#2a9d8f',
  weight: 1,
  fillOpacity: 0.9,
  radius: 8,
}

const HOSPITAL_LINK_STYLE = {
  color: '#6c63ff',
  weight: 2,
  dashArray: '4 4',
  opacity: 0.8,
}

type HasCoordinates = { latitude: number; longitude: number }

const hasValidCoordinates = (entity: HasCoordinates | Alerte): entity is HasCoordinates & { latitude: number; longitude: number } =>
  Number.isFinite(entity.latitude) && Number.isFinite(entity.longitude)

const isFiniteNumber = (value: number | null | undefined): value is number =>
  typeof value === 'number' && Number.isFinite(value)

const formatCoordinates = (lat: number, lon: number, precision = 4) =>
  `${lat.toFixed(precision)}, ${lon.toFixed(precision)}`

function MapBoundsHelper({ bounds }: { bounds: LatLngBoundsExpression }) {
  const map = useMap()
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 13 })
    }
  }, [bounds, map])
  return null
}
