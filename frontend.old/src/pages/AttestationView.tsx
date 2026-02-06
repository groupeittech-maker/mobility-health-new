import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { attestationsApi } from '../api/attestations'
import PDFViewer from '../components/PDFViewer'
import './AttestationView.css'

export default function AttestationView() {
  const { attestationId } = useParams<{ attestationId: string }>()

  const { data: attestation, isLoading, error } = useQuery({
    queryKey: ['attestation', attestationId],
    queryFn: () => attestationsApi.getWithUrl(Number(attestationId)),
    enabled: !!attestationId,
  })

  if (isLoading) {
    return (
      <div className="attestation-view-container">
        <div className="loading">Chargement de l'attestation...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="attestation-view-container">
        <div className="error">
          Erreur lors du chargement de l'attestation. Veuillez réessayer.
        </div>
      </div>
    )
  }

  if (!attestation) {
    return (
      <div className="attestation-view-container">
        <div className="error">Attestation non trouvée</div>
      </div>
    )
  }

  const title = attestation.type_attestation === 'provisoire' 
    ? `Attestation Provisoire - ${attestation.numero_attestation}`
    : `Attestation Définitive - ${attestation.numero_attestation}`

  return (
    <div className="attestation-view-container">
      <div className="attestation-header">
        <h1>{title}</h1>
        <div className="attestation-info">
          <span className={`badge badge-${attestation.type_attestation}`}>
            {attestation.type_attestation === 'provisoire' ? 'Provisoire' : 'Définitive'}
          </span>
          <span className="attestation-date">
            Émise le {new Date(attestation.created_at).toLocaleDateString('fr-FR')}
          </span>
        </div>
      </div>
      
      <div className="attestation-viewer-wrapper">
        <PDFViewer
          url={attestation.url_signee}
          title={title}
          onError={(error) => {
            console.error('Erreur PDF:', error)
          }}
        />
      </div>
    </div>
  )
}

