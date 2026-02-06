import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi, Statistics } from '../api/dashboard'
import './StatisticsPage.css'

export default function StatisticsPage() {
  const [period, setPeriod] = useState<string>('month')

  const { data: statistics, isLoading } = useQuery({
    queryKey: ['statistics', period],
    queryFn: () => dashboardApi.getStatistics(period),
  })

  if (isLoading) {
    return (
      <div className="statistics-page">
        <div className="loading">Chargement des statistiques...</div>
      </div>
    )
  }

  return (
    <div className="statistics-page">
      <div className="page-header">
        <h1>Statistiques</h1>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          className="period-select"
        >
          <option value="day">Par jour (30 derniers jours)</option>
          <option value="week">Par semaine (12 dernières semaines)</option>
          <option value="month">Par mois (12 derniers mois)</option>
          <option value="year">Par année (5 dernières années)</option>
        </select>
      </div>

      <div className="statistics-content">
        {/* Souscriptions par période */}
        <section className="stat-section">
          <h2>Souscriptions par période</h2>
          <div className="chart-container">
            {statistics?.subscriptions_by_period && Object.keys(statistics.subscriptions_by_period).length > 0 ? (
              <div className="bar-chart">
                {Object.entries(statistics.subscriptions_by_period).map(([period, count]) => (
                  <div key={period} className="bar-item">
                    <div className="bar-label">{period}</div>
                    <div className="bar-wrapper">
                      <div
                        className="bar"
                        style={{
                          width: `${(count / Math.max(...Object.values(statistics.subscriptions_by_period))) * 100}%`,
                        }}
                      >
                        <span className="bar-value">{count}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">Aucune donnée disponible</p>
            )}
          </div>
        </section>

        {/* Produits les plus vendus */}
        <section className="stat-section">
          <h2>Produits les plus vendus</h2>
          <div className="products-list">
            {statistics?.top_products && statistics.top_products.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>Rang</th>
                    <th>Produit</th>
                    <th>Nombre de ventes</th>
                  </tr>
                </thead>
                <tbody>
                  {statistics.top_products.map((product, index) => (
                    <tr key={product.id}>
                      <td>#{index + 1}</td>
                      <td>{product.nom}</td>
                      <td>
                        <strong>{product.count}</strong>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="no-data">Aucune donnée disponible</p>
            )}
          </div>
        </section>

        {/* Revenus par période */}
        <section className="stat-section">
          <h2>Revenus par période</h2>
          <div className="chart-container">
            {statistics?.revenue_by_period && Object.keys(statistics.revenue_by_period).length > 0 ? (
              <div className="bar-chart">
                {Object.entries(statistics.revenue_by_period).map(([period, revenue]) => (
                  <div key={period} className="bar-item">
                    <div className="bar-label">{period}</div>
                    <div className="bar-wrapper">
                      <div
                        className="bar bar-revenue"
                        style={{
                          width: `${(revenue / Math.max(...Object.values(statistics.revenue_by_period))) * 100}%`,
                        }}
                      >
                        <span className="bar-value">{revenue.toFixed(2)} €</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">Aucune donnée disponible</p>
            )}
          </div>
        </section>

        {/* Sinistres par pays */}
        <section className="stat-section">
          <h2>Sinistres par pays</h2>
          <div className="chart-container">
            {statistics?.sinistres_by_country && Object.keys(statistics.sinistres_by_country).length > 0 ? (
              <div className="pie-chart">
                {Object.entries(statistics.sinistres_by_country).map(([country, count]) => (
                  <div key={country} className="pie-item">
                    <div className="pie-label">{country}</div>
                    <div className="pie-value">{count}</div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">Aucune donnée disponible</p>
            )}
          </div>
        </section>

        {/* Sinistres par produit */}
        <section className="stat-section">
          <h2>Sinistres par produit</h2>
          <div className="chart-container">
            {statistics?.sinistres_by_product && Object.keys(statistics.sinistres_by_product).length > 0 ? (
              <div className="bar-chart">
                {Object.entries(statistics.sinistres_by_product).map(([product, count]) => (
                  <div key={product} className="bar-item">
                    <div className="bar-label">{product}</div>
                    <div className="bar-wrapper">
                      <div
                        className="bar bar-sinistres"
                        style={{
                          width: `${(count / Math.max(...Object.values(statistics.sinistres_by_product))) * 100}%`,
                        }}
                      >
                        <span className="bar-value">{count}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">Aucune donnée disponible</p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

