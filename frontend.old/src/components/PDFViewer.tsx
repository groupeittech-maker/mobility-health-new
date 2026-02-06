import { useState, useEffect } from 'react'
import './PDFViewer.css'

interface PDFViewerProps {
  url: string
  title?: string
  onError?: (error: Error) => void
}

export default function PDFViewer({ url, title = 'Document PDF', onError }: PDFViewerProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
  }, [url])

  const handleLoad = () => {
    setLoading(false)
  }

  const handleError = () => {
    setLoading(false)
    const error = new Error('Erreur lors du chargement du PDF')
    setError('Impossible de charger le document PDF')
    if (onError) {
      onError(error)
    }
  }

  return (
    <div className="pdf-viewer-container">
      <div className="pdf-viewer-header">
        <h3>{title}</h3>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="pdf-download-link"
          download
        >
          Télécharger
        </a>
      </div>
      
      <div className="pdf-viewer-content">
        {loading && (
          <div className="pdf-loading">
            <div className="spinner"></div>
            <p>Chargement du document...</p>
          </div>
        )}
        
        {error && (
          <div className="pdf-error">
            <p>{error}</p>
            <button onClick={() => window.location.reload()}>Réessayer</button>
          </div>
        )}
        
        <iframe
          src={url}
          className="pdf-iframe"
          title={title}
          onLoad={handleLoad}
          onError={handleError}
          style={{ display: loading || error ? 'none' : 'block' }}
        />
      </div>
    </div>
  )
}

