import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { documentsApi, Document } from '../api/documents'
import { subscriptionsApi } from '../api/subscriptions'
import './DocumentsPage.css'

type DocumentTypeFilter = 'all' | 'attestation_provisoire' | 'attestation_definitive' | 'facture' | 'recu'

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  attestation_provisoire: 'Attestation Provisoire',
  attestation_definitive: 'Attestation Définitive',
  facture: 'Facture',
  recu: 'Reçu',
  justificatif: 'Justificatif',
}

const DOCUMENT_TYPE_ICONS: Record<string, string> = {
  attestation_provisoire: '📄',
  attestation_definitive: '✅',
  facture: '🧾',
  recu: '💰',
  justificatif: '📎',
}

export default function DocumentsPage() {
  const [searchParams] = useSearchParams()
  const [typeFilter, setTypeFilter] = useState<DocumentTypeFilter>('all')
  const subscriptionId = searchParams.get('subscription_id')

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', subscriptionId],
    queryFn: () => documentsApi.getAll(subscriptionId ? parseInt(subscriptionId) : undefined),
  })

  const { data: subscription } = useQuery({
    queryKey: ['subscription', subscriptionId],
    queryFn: () => subscriptionsApi.getById(parseInt(subscriptionId!)),
    enabled: !!subscriptionId,
  })

  const filteredDocuments = typeFilter === 'all' 
    ? documents 
    : documents.filter(doc => doc.type === typeFilter)

  const handleDownload = async (document: Document) => {
    if (document.url_download) {
      // Si on a une URL directe, ouvrir dans un nouvel onglet
      window.open(document.url_download, '_blank')
    } else {
      // Sinon, utiliser l'endpoint de téléchargement
      try {
        await documentsApi.download(document.id, document.type)
      } catch (error: any) {
        alert(`Erreur lors du téléchargement: ${error.response?.data?.detail || error.message}`)
      }
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getDocumentTypeCount = (type: string) => {
    return documents.filter(doc => doc.type === type).length
  }

  return (
    <div className="documents-page">
      <div className="page-header">
        <h1>Mes Documents</h1>
        {subscription && (
          <p className="subtitle">
            Souscription: {subscription.numero_souscription}
          </p>
        )}
      </div>

      {/* Filtres */}
      <div className="filters-section">
        <div className="filter-tabs">
          <button
            className={`filter-tab ${typeFilter === 'all' ? 'active' : ''}`}
            onClick={() => setTypeFilter('all')}
          >
            Tous ({documents.length})
          </button>
          <button
            className={`filter-tab ${typeFilter === 'attestation_provisoire' ? 'active' : ''}`}
            onClick={() => setTypeFilter('attestation_provisoire')}
          >
            {DOCUMENT_TYPE_ICONS.attestation_provisoire} Attestations Provisoires ({getDocumentTypeCount('attestation_provisoire')})
          </button>
          <button
            className={`filter-tab ${typeFilter === 'attestation_definitive' ? 'active' : ''}`}
            onClick={() => setTypeFilter('attestation_definitive')}
          >
            {DOCUMENT_TYPE_ICONS.attestation_definitive} Attestations Définitives ({getDocumentTypeCount('attestation_definitive')})
          </button>
          <button
            className={`filter-tab ${typeFilter === 'recu' ? 'active' : ''}`}
            onClick={() => setTypeFilter('recu')}
          >
            {DOCUMENT_TYPE_ICONS.recu} Reçus ({getDocumentTypeCount('recu')})
          </button>
          <button
            className={`filter-tab ${typeFilter === 'facture' ? 'active' : ''}`}
            onClick={() => setTypeFilter('facture')}
          >
            {DOCUMENT_TYPE_ICONS.facture} Factures ({getDocumentTypeCount('facture')})
          </button>
        </div>
      </div>

      {/* Liste des documents */}
      {isLoading ? (
        <div className="loading">Chargement des documents...</div>
      ) : filteredDocuments.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">📁</div>
          <h2>Aucun document disponible</h2>
          <p>
            {typeFilter === 'all' 
              ? "Vous n'avez pas encore de documents."
              : `Aucun document de type "${DOCUMENT_TYPE_LABELS[typeFilter]}" disponible.`}
          </p>
        </div>
      ) : (
        <div className="documents-grid">
          {filteredDocuments.map((document) => (
            <div key={`${document.type}-${document.id}`} className="document-card">
              <div className="document-header">
                <div className="document-icon">
                  {DOCUMENT_TYPE_ICONS[document.type] || '📄'}
                </div>
                <div className="document-info">
                  <h3>{document.titre}</h3>
                  <p className="document-number">{document.numero}</p>
                </div>
              </div>
              
              <div className="document-details">
                <div className="detail-item">
                  <span className="detail-label">Date de création:</span>
                  <span className="detail-value">{formatDate(document.date_creation)}</span>
                </div>
                {document.souscription_id && (
                  <div className="detail-item">
                    <span className="detail-label">Souscription:</span>
                    <span className="detail-value">#{document.souscription_id}</span>
                  </div>
                )}
              </div>

              <div className="document-actions">
                {document.url_download ? (
                  <button
                    onClick={() => handleDownload(document)}
                    className="btn-download"
                  >
                    📥 Télécharger
                  </button>
                ) : (
                  <button
                    onClick={() => handleDownload(document)}
                    className="btn-download"
                    disabled={document.type === 'recu'}
                  >
                    {document.type === 'recu' ? '⏳ Bientôt disponible' : '📥 Télécharger'}
                  </button>
                )}
                {document.url_download && (
                  <button
                    onClick={() => window.open(document.url_download!, '_blank')}
                    className="btn-view"
                  >
                    👁️ Voir
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

