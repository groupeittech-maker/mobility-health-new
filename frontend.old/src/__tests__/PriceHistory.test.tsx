import { render, screen } from '@testing-library/react'
import PriceHistory from '../components/PriceHistory'
import { HistoriquePrix } from '../types'

const mockHistory: HistoriquePrix[] = [
  {
    id: 1,
    produit_assurance_id: 1,
    ancien_prix: 100.00,
    nouveau_prix: 120.00,
    raison_modification: 'Augmentation des coûts',
    created_at: '2024-01-15T10:00:00',
    updated_at: '2024-01-15T10:00:00',
  },
  {
    id: 2,
    produit_assurance_id: 1,
    ancien_prix: undefined,
    nouveau_prix: 100.00,
    raison_modification: 'Création du produit',
    created_at: '2024-01-01T10:00:00',
    updated_at: '2024-01-01T10:00:00',
  },
]

describe('PriceHistory', () => {
  it('renders empty state when no history', () => {
    render(<PriceHistory history={[]} currency="EUR" />)
    expect(screen.getByText(/aucun historique/i)).toBeInTheDocument()
  })

  it('renders price history table with data', () => {
    render(<PriceHistory history={mockHistory} currency="EUR" />)
    
    expect(screen.getByText(/historique des prix/i)).toBeInTheDocument()
    expect(screen.getByText(/100.00 €/i)).toBeInTheDocument()
    expect(screen.getByText(/120.00 €/i)).toBeInTheDocument()
    expect(screen.getByText(/augmentation des coûts/i)).toBeInTheDocument()
  })

  it('displays N/A for undefined old price', () => {
    render(<PriceHistory history={mockHistory} currency="EUR" />)
    expect(screen.getByText(/N\/A/i)).toBeInTheDocument()
  })

  it('displays correct currency symbol', () => {
    const { rerender } = render(<PriceHistory history={mockHistory} currency="EUR" />)
    expect(screen.getByText(/€/i)).toBeInTheDocument()

    rerender(<PriceHistory history={mockHistory} currency="USD" />)
    expect(screen.getByText(/\$/i)).toBeInTheDocument()
  })
})
