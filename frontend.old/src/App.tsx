import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import AdminProducts from './pages/AdminProducts'
import QuestionnaireShort from './pages/QuestionnaireShort'
import QuestionnaireLong from './pages/QuestionnaireLong'
import QuestionnaireAdministratif from './pages/QuestionnaireAdministratif'
import QuestionnaireMedical from './pages/QuestionnaireMedical'
import AttestationView from './pages/AttestationView'
import SOSAgentDashboard from './pages/SOSAgentDashboard'
import ProductsResultsPage from './pages/ProductsResultsPage'
import CheckoutPage from './pages/CheckoutPage'
import PaymentPage from './pages/PaymentPage'
import DocumentsPage from './pages/DocumentsPage'
import TravelProjectFormPage from './pages/TravelProjectFormPage'
import SOSPage from './pages/SOSPage'
import SinistreTracking from './pages/SinistreTracking'
import BackOfficeDashboard from './pages/BackOfficeDashboard'
import AdminSubscriptionsPage from './pages/AdminSubscriptionsPage'
import AdminSinistresPage from './pages/AdminSinistresPage'
import StatisticsPage from './pages/StatisticsPage'
import AdminHospitalsPage from './pages/AdminHospitalsPage'
import AdminAssureursPage from './pages/AdminAssureursPage'
import HospitalInvoiceProcessingPage from './pages/HospitalInvoiceProcessingPage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/admin/products" element={<AdminProducts />} />
          <Route path="/subscriptions/:subscriptionId/questionnaire/short" element={<QuestionnaireShort />} />
          <Route path="/subscriptions/:subscriptionId/questionnaire/long" element={<QuestionnaireLong />} />
          <Route path="/subscriptions/:subscriptionId/questionnaire/administratif" element={<QuestionnaireAdministratif />} />
          <Route path="/subscriptions/:subscriptionId/questionnaire/medical" element={<QuestionnaireMedical />} />
          <Route path="/attestations/:attestationId" element={<AttestationView />} />
          <Route path="/sos/agent" element={<SOSAgentDashboard />} />
          <Route path="/sos" element={<SOSPage />} />
          <Route path="/sinistre/:alerteId" element={<SinistreTracking />} />
          <Route path="/backoffice/dashboard" element={<BackOfficeDashboard />} />
          <Route path="/backoffice/subscriptions" element={<AdminSubscriptionsPage />} />
          <Route path="/backoffice/sinistres" element={<AdminSinistresPage />} />
          <Route path="/backoffice/hospitals" element={<AdminHospitalsPage />} />
          <Route path="/backoffice/assureurs" element={<AdminAssureursPage />} />
          <Route path="/backoffice/statistics" element={<StatisticsPage />} />
          <Route path="/travel-project" element={<TravelProjectFormPage />} />
          <Route path="/products" element={<ProductsResultsPage />} />
          <Route path="/hospital/invoices" element={<HospitalInvoiceProcessingPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/payment" element={<PaymentPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/" element={<div>Home</div>} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
