import client from './client'

export interface Document {
  id: number
  type: 'attestation_provisoire' | 'attestation_definitive' | 'facture' | 'recu' | 'justificatif'
  titre: string
  numero: string
  date_creation: string
  url_download: string | null
  souscription_id: number | null
  paiement_id: number | null
}

export const documentsApi = {
  /**
   * Obtenir tous les documents de l'utilisateur
   */
  getAll: async (subscriptionId?: number): Promise<Document[]> => {
    const params = subscriptionId ? { subscription_id: subscriptionId } : {}
    const response = await client.get<Document[]>('/documents', { params })
    return response.data
  },

  /**
   * Télécharger un document
   */
  download: async (documentId: number, documentType: string): Promise<void> => {
    const response = await client.get(`/documents/${documentId}/download`, {
      params: { document_type: documentType },
      responseType: 'blob',
    })
    
    // Créer un lien de téléchargement
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `document-${documentId}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

