import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { productsApi } from '../api/products'
import { ProduitAssurance, Currency } from '../types'
import './ProductsResultsPage.css'

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  XOF: 'CFA',
  XAF: 'FCFA',
}

export default function ProductsResultsPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [currency, setCurrency] = useState<Currency>('EUR')
  const projetId = searchParams.get('projet_id')

  // Récupérer tous les produits actifs disponibles
  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products', 'active'],
    queryFn: () => productsApi.getPublicProducts(true),
  })

  const formatPrice = (price: number) => {
    return `${price.toFixed(2)} ${CURRENCY_SYMBOLS[currency]}`
  }

  const handleSelectProduct = (product: ProduitAssurance) => {
    if (projetId) {
      // Si un projet existe, rediriger vers le checkout avec le projet et le produit
      navigate(`/checkout?projet_id=${projetId}&product_id=${product.id}`)
    } else {
      // Sinon, rediriger vers la création de projet avec le produit pré-sélectionné
      navigate(`/travel-project?product_id=${product.id}`)
    }
  }

  // Note: La page fonctionne même sans projet_id pour permettre la consultation des produits
  // Si un projet_id est fourni, il sera utilisé lors de la sélection pour la navigation vers checkout

  // Fonction pour formater les garanties (peut être string ou array)
  const formatGuarantees = (garanties: string | any): string => {
    if (!garanties) return ''
    if (typeof garanties === 'string') return garanties
    if (Array.isArray(garanties)) {
      return garanties.map((g: any) => 
        typeof g === 'string' ? g : g.nom || g.libelle || JSON.stringify(g)
      ).join(', ')
    }
    return JSON.stringify(garanties)
  }

  return (
    <div className="products-results-page">
      <div className="subscription-steps-indicator">
        <div className="step completed">
          <div className="step-circle">1</div>
          <div className="step-label">Projet de voyage</div>
        </div>
        <div className="step active">
          <div className="step-circle">2</div>
          <div className="step-label">Choix du produit</div>
        </div>
        <div className="step">
          <div className="step-circle">3</div>
          <div className="step-label">Questionnaire</div>
        </div>
        <div className="step">
          <div className="step-circle">4</div>
          <div className="step-label">Paiement</div>
        </div>
      </div>

      <div className="page-header">
        <h1>Étape 2 : Choisissez votre produit d'assurance</h1>
        <div className="header-actions">
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value as Currency)}
            className="currency-select"
          >
            <option value="EUR">EUR (€)</option>
            <option value="USD">USD ($)</option>
            <option value="XOF">XOF (CFA)</option>
            <option value="XAF">XAF (FCFA)</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="loading">Chargement des produits...</div>
      ) : products.length === 0 ? (
        <div className="empty-state">
          <p>Aucun produit d'assurance disponible pour le moment.</p>
        </div>
      ) : (
        <div className="products-grid">
          {products.map((product) => (
            <div key={product.id} className="product-card">
              {/* Miniature du produit */}
              {product.image_url && (
                <div className="product-image">
                  <img 
                    src={product.image_url} 
                    alt={product.nom}
                    onError={(e) => {
                      (e.target as HTMLImageElement).style.display = 'none'
                    }}
                  />
                </div>
              )}
              
              <div className="product-header">
                <h3>{product.nom}</h3>
                <span className="product-code">{product.code}</span>
              </div>

              {/* Assureur */}
              {product.assureur && (
                <div className="product-insurer">
                  <span className="insurer-label">Assureur:</span>
                  <span className="insurer-name">{product.assureur}</span>
                </div>
              )}
              
              {/* Prix forfaitaire */}
              <div className="product-price">
                <span className="price-label">Prix forfaitaire:</span>
                <span className="price-value">{formatPrice(product.cout)}</span>
              </div>

              {/* Description / Caractéristiques principales */}
              {product.description && (
                <div className="product-description">
                  <strong>Description:</strong>
                  <p>{product.description}</p>
                </div>
              )}

              {/* Garanties */}
              {product.garanties && (
                <div className="product-guarantees">
                  <strong>Garanties principales:</strong>
                  <p>{formatGuarantees(product.garanties)}</p>
                </div>
              )}

              {/* Caractéristiques supplémentaires */}
              <div className="product-features">
                {product.duree_validite_jours && (
                  <div className="feature-item">
                    <span className="feature-label">Durée de validité:</span>
                    <span className="feature-value">{product.duree_validite_jours} jours</span>
                  </div>
                )}
                {product.age_minimum && product.age_maximum && (
                  <div className="feature-item">
                    <span className="feature-label">Âge:</span>
                    <span className="feature-value">{product.age_minimum} - {product.age_maximum} ans</span>
                  </div>
                )}
                {product.couverture_multi_entrees && (
                  <div className="feature-item">
                    <span className="feature-label">Multi-entrées:</span>
                    <span className="feature-value">Oui</span>
                  </div>
                )}
              </div>

              <button
                onClick={() => handleSelectProduct(product)}
                className="btn-select"
              >
                Sélectionner ce produit
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
