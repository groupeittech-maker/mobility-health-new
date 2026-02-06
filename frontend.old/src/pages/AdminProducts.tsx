import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productsApi } from '../api/products'
import { ProduitAssurance, Currency } from '../types'
import ProductForm from '../components/ProductForm'
import PriceHistory from '../components/PriceHistory'
import './AdminProducts.css'

const CURRENCIES: Currency[] = ['EUR', 'USD', 'XOF', 'XAF']

export default function AdminProducts() {
  const [editingProduct, setEditingProduct] = useState<ProduitAssurance | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null)
  const [currency, setCurrency] = useState<Currency>('EUR')
  const [estActifFilter, setEstActifFilter] = useState<boolean | undefined>(undefined)

  const queryClient = useQueryClient()

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['admin-products', estActifFilter],
    queryFn: () => productsApi.getAll(estActifFilter),
  })

  const { data: priceHistory = [] } = useQuery({
    queryKey: ['price-history', selectedProductId],
    queryFn: () => productsApi.getPriceHistory(selectedProductId!),
    enabled: !!selectedProductId,
  })

  const createMutation = useMutation({
    mutationFn: productsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
      setShowForm(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ProduitAssurance> }) =>
      productsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
      queryClient.invalidateQueries({ queryKey: ['price-history'] })
      setEditingProduct(null)
      setShowForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: productsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-products'] })
    },
  })

  const handleCreate = () => {
    setEditingProduct(null)
    setShowForm(true)
  }

  const handleEdit = (product: ProduitAssurance) => {
    setEditingProduct(product)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (window.confirm('Êtes-vous sûr de vouloir supprimer ce produit ?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleSubmit = (data: Partial<ProduitAssurance>) => {
    if (editingProduct) {
      updateMutation.mutate({ id: editingProduct.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingProduct(null)
  }

  const formatPrice = (price: number) => {
    const symbols: Record<Currency, string> = {
      EUR: '€',
      USD: '$',
      XOF: 'CFA',
      XAF: 'FCFA',
    }
    return `${price.toFixed(2)} ${symbols[currency]}`
  }

  if (showForm) {
    return (
      <div className="admin-products">
        <div className="page-header">
          <h1>{editingProduct ? 'Modifier le produit' : 'Créer un produit'}</h1>
        </div>
        <ProductForm
          product={editingProduct || undefined}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          currency={currency}
        />
      </div>
    )
  }

  return (
    <div className="admin-products">
      <div className="page-header">
        <h1>Gestion des produits</h1>
        <div className="header-actions">
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value as Currency)}
            className="currency-select"
          >
            {CURRENCIES.map((curr) => (
              <option key={curr} value={curr}>
                {curr}
              </option>
            ))}
          </select>
          <button onClick={handleCreate} className="btn-primary">
            + Nouveau produit
          </button>
        </div>
      </div>

      <div className="filters">
        <label>
          <input
            type="radio"
            name="filter"
            checked={estActifFilter === undefined}
            onChange={() => setEstActifFilter(undefined)}
          />
          Tous
        </label>
        <label>
          <input
            type="radio"
            name="filter"
            checked={estActifFilter === true}
            onChange={() => setEstActifFilter(true)}
          />
          Actifs uniquement
        </label>
        <label>
          <input
            type="radio"
            name="filter"
            checked={estActifFilter === false}
            onChange={() => setEstActifFilter(false)}
          />
          Inactifs uniquement
        </label>
      </div>

      {isLoading ? (
        <div className="loading">Chargement...</div>
      ) : (
        <>
          <div className="products-table-container">
            <table className="products-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Nom</th>
                  <th>Coût</th>
                  <th>Clé répartition</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="empty-state">
                      Aucun produit trouvé
                    </td>
                  </tr>
                ) : (
                  products.map((product) => (
                    <tr
                      key={product.id}
                      className={selectedProductId === product.id ? 'selected' : ''}
                      onClick={() => setSelectedProductId(product.id)}
                    >
                      <td>{product.code}</td>
                      <td>{product.nom}</td>
                      <td>{formatPrice(product.cout)}</td>
                      <td>{product.cle_repartition}</td>
                      <td>
                        <span className={`status-badge ${product.est_actif ? 'active' : 'inactive'}`}>
                          {product.est_actif ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td>
                        <div className="action-buttons">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleEdit(product)
                            }}
                            className="btn-edit"
                          >
                            Modifier
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDelete(product.id)
                            }}
                            className="btn-delete"
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {selectedProductId && (
            <PriceHistory history={priceHistory} currency={currency} />
          )}
        </>
      )}
    </div>
  )
}
