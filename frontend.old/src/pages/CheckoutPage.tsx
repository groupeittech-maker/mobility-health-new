import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { productsApi } from '../api/products'
import { subscriptionsApi } from '../api/subscriptions'
import { voyagesApi } from '../api/voyages'
import { ProduitAssurance, ProjetVoyage, Currency } from '../types'
import './CheckoutPage.css'

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  XOF: 'CFA',
  XAF: 'FCFA',
}

export default function CheckoutPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [currency, setCurrency] = useState<Currency>('EUR')
  
  const projetId = searchParams.get('projet_id')
  const productId = searchParams.get('product_id')

  const { data: projet } = useQuery({
    queryKey: ['projet', projetId],
    queryFn: () => voyagesApi.getById(parseInt(projetId!)),
    enabled: !!projetId,
  })

  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => productsApi.getById(parseInt(productId!)),
    enabled: !!productId,
  })

  const startSubscriptionMutation = useMutation({
    mutationFn: subscriptionsApi.start,
    onSuccess: (subscription) => {
      navigate(`/subscription-success?id=${subscription.id}`)
    },
    onError: (error: any) => {
      alert(`Erreur lors de la création de la souscription: ${error.response?.data?.detail || error.message}`)
    },
  })

  const formatPrice = (price: number) => {
    return `${price.toFixed(2)} ${CURRENCY_SYMBOLS[currency]}`
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const handleConfirm = () => {
    if (!productId || !projetId) {
      alert('Informations manquantes')
      return
    }

    startSubscriptionMutation.mutate({
      produit_assurance_id: parseInt(productId),
      projet_voyage_id: parseInt(projetId),
    })
  }

  if (!projetId || !productId) {
    return (
      <div className="checkout-page">
        <div className="error-message">
          <h2>Informations manquantes</h2>
          <p>Veuillez sélectionner un projet et un produit.</p>
          <button onClick={() => navigate('/travel-project')} className="btn-primary">
            Retour
          </button>
        </div>
      </div>
    )
  }

  if (!projet || !product) {
    return (
      <div className="checkout-page">
        <div className="loading">Chargement...</div>
      </div>
    )
  }

  return (
    <div className="checkout-page">
      <div className="page-header">
        <h1>Finaliser votre souscription</h1>
      </div>

      <div className="checkout-content">
        <div className="checkout-summary">
          <div className="summary-section">
            <h2>Résumé du projet</h2>
            <div className="summary-item">
              <strong>Titre:</strong> {projet.titre}
            </div>
            <div className="summary-item">
              <strong>Destination:</strong> {projet.destination}
            </div>
            <div className="summary-item">
              <strong>Date de départ:</strong> {formatDate(projet.date_depart)}
            </div>
            {projet.date_retour && (
              <div className="summary-item">
                <strong>Date de retour:</strong> {formatDate(projet.date_retour)}
              </div>
            )}
            <div className="summary-item">
              <strong>Participants:</strong> {projet.nombre_participants}
            </div>
          </div>

          <div className="summary-section">
            <h2>Produit sélectionné</h2>
            <div className="summary-item">
              <strong>Nom:</strong> {product.nom}
            </div>
            <div className="summary-item">
              <strong>Code:</strong> {product.code}
            </div>
            {product.description && (
              <div className="summary-item">
                <strong>Description:</strong> {product.description}
              </div>
            )}
          </div>

          <div className="summary-section price-section">
            <div className="price-summary">
              <div className="price-row">
                <span>Prix de l'assurance:</span>
                <span className="price-value">{formatPrice(product.cout)}</span>
              </div>
              <div className="price-row total">
                <span>Total à payer:</span>
                <span className="price-value">{formatPrice(product.cout)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="checkout-actions">
          <div className="currency-selector">
            <label>Devise:</label>
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
            >
              <option value="EUR">EUR (€)</option>
              <option value="USD">USD ($)</option>
              <option value="XOF">XOF (CFA)</option>
              <option value="XAF">XAF (FCFA)</option>
            </select>
          </div>

          <div className="action-buttons">
            <button
              onClick={() => navigate(-1)}
              className="btn-secondary"
              disabled={startSubscriptionMutation.isPending}
            >
              Retour
            </button>
            <button
              onClick={handleConfirm}
              className="btn-primary"
              disabled={startSubscriptionMutation.isPending}
            >
              {startSubscriptionMutation.isPending ? 'Traitement...' : 'Confirmer et payer'}
            </button>
          </div>

          <p className="disclaimer">
            En confirmant, vous créez une souscription en statut "pending". 
            Le paiement sera traité dans une étape ultérieure.
          </p>
        </div>
      </div>
    </div>
  )
}
