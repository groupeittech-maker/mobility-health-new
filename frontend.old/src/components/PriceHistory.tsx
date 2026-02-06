import { HistoriquePrix, Currency } from '../types'
import './PriceHistory.css'

interface PriceHistoryProps {
  history: HistoriquePrix[]
  currency: Currency
}

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  EUR: '€',
  USD: '$',
  XOF: 'CFA',
  XAF: 'FCFA',
}

export default function PriceHistory({ history, currency }: PriceHistoryProps) {
  if (history.length === 0) {
    return <div className="price-history-empty">Aucun historique de prix disponible</div>
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatPrice = (price: number | undefined) => {
    if (price === undefined || price === null) return 'N/A'
    return `${price.toFixed(2)} ${CURRENCY_SYMBOLS[currency]}`
  }

  return (
    <div className="price-history">
      <h3>Historique des prix</h3>
      <table className="price-history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Ancien prix</th>
            <th>Nouveau prix</th>
            <th>Raison</th>
          </tr>
        </thead>
        <tbody>
          {history.map((entry) => (
            <tr key={entry.id}>
              <td>{formatDate(entry.created_at)}</td>
              <td>{formatPrice(entry.ancien_prix)}</td>
              <td className="new-price">{formatPrice(entry.nouveau_prix)}</td>
              <td>{entry.raison_modification || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
