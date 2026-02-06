import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../api/dashboard'
import './BackOfficeDashboard.css'

export default function BackOfficeDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => dashboardApi.getStats(),
    refetchInterval: 30000, // Rafraîchir toutes les 30 secondes
  })

  if (isLoading) {
    return (
      <div className="backoffice-dashboard">
        <div className="loading">Chargement...</div>
      </div>
    )
  }

  return (
    <div className="backoffice-dashboard">
      <div className="dashboard-header">
        <h1>Tableau de bord Back-Office</h1>
      </div>

      <div className="stats-grid">
        {/* Nombre de souscriptions du jour */}
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <h3>Souscriptions du jour</h3>
            <p className="stat-value">{stats?.subscriptions_today || 0}</p>
          </div>
        </div>

        {/* Souscriptions en attente */}
        <div className="stat-card stat-warning">
          <div className="stat-icon">⏳</div>
          <div className="stat-content">
            <h3>Souscriptions en attente</h3>
            <p className="stat-value">{stats?.subscriptions_pending || 0}</p>
          </div>
        </div>

        {/* Sinistres ouverts */}
        <div className="stat-card stat-danger">
          <div className="stat-icon">🚨</div>
          <div className="stat-content">
            <h3>Sinistres ouverts</h3>
            <p className="stat-value">{stats?.sinistres_open || 0}</p>
          </div>
        </div>

        {/* Revenus du jour */}
        <div className="stat-card stat-success">
          <div className="stat-icon">💰</div>
          <div className="stat-content">
            <h3>Revenus du jour</h3>
            <p className="stat-value">{stats?.total_revenue_today.toFixed(2) || '0.00'} €</p>
          </div>
        </div>

        {/* Revenus totaux */}
        <div className="stat-card stat-info">
          <div className="stat-icon">💵</div>
          <div className="stat-content">
            <h3>Revenus totaux</h3>
            <p className="stat-value">{stats?.total_revenue.toFixed(2) || '0.00'} €</p>
          </div>
        </div>
      </div>

      <div className="quick-actions">
        <a className="quick-action-card" href="/backoffice/hospitals">
          <h3>Gestion des hôpitaux affiliés</h3>
          <p>Ajoutez des hôpitaux Mobility Health, posez-les sur la carte et créez leurs réceptionnistes.</p>
        </a>
        <a className="quick-action-card" href="/backoffice/assureurs">
          <h3>Gestion des assureurs</h3>
          <p>Créez les assureurs partenaires, associez un agent comptable et reliez-les aux produits.</p>
        </a>
      </div>

      {/* Historique des paiements récents */}
      <div className="recent-payments-section">
        <h2>Historique des paiements récents</h2>
        <div className="payments-table">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Montant</th>
                <th>Statut</th>
                <th>Date</th>
                <th>Souscription</th>
              </tr>
            </thead>
            <tbody>
              {stats?.payments_recent && stats.payments_recent.length > 0 ? (
                stats.payments_recent.map((payment) => (
                  <tr key={payment.id}>
                    <td>#{payment.id}</td>
                    <td>{payment.montant.toFixed(2)} €</td>
                    <td>
                      <span className={`status-badge status-${payment.statut}`}>
                        {payment.statut}
                      </span>
                    </td>
                    <td>
                      {payment.date_paiement
                        ? new Date(payment.date_paiement).toLocaleDateString('fr-FR')
                        : new Date(payment.created_at).toLocaleDateString('fr-FR')}
                    </td>
                    <td>#{payment.subscription_id}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="no-data">
                    Aucun paiement récent
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

