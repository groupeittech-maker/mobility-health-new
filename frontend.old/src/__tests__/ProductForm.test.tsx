import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProductForm from '../components/ProductForm'
import { ProduitAssurance } from '../types'
import { assureursApi } from '../api/assureurs'

jest.mock('../api/assureurs', () => ({
  assureursApi: {
    listAdmin: jest.fn(),
  },
}))

const mockAssureurs = [
  {
    id: 1,
    nom: 'Assureur Test',
    pays: 'France',
    logo_url: 'https://example.com/logo.png',
    adresse: '1 rue de Paris',
    telephone: '+33 1 23 45 67 89',
    agent_comptable_id: 42,
    agent_comptable: {
      id: 42,
      email: 'agent@test.com',
      username: 'agent_assureur',
      full_name: 'Agent Comptable Assurance',
      role: 'agent_comptable_assureur',
      is_active: true,
    },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
]

const mockProduct: ProduitAssurance = {
  id: 1,
  code: 'PROD001',
  nom: 'Produit Test',
  description: 'Description test',
  cout: 100.5,
  cle_repartition: 'fixe',
  est_actif: true,
  assureur: 'Assureur Test',
  assureur_id: 1,
  created_at: '2024-01-01T00:00:00',
  updated_at: '2024-01-01T00:00:00',
}

describe('ProductForm', () => {
  const mockOnSubmit = jest.fn()
  const mockOnCancel = jest.fn()
  const renderProductForm = (props: Partial<React.ComponentProps<typeof ProductForm>> = {}) => {
    const queryClient = new QueryClient()
    return render(
      <QueryClientProvider client={queryClient}>
        <ProductForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} currency="EUR" {...props} />
      </QueryClientProvider>
    )
  }

  beforeEach(() => {
    jest.clearAllMocks()
    ;(assureursApi.listAdmin as jest.Mock).mockResolvedValue(mockAssureurs)
  })

  it('renders form with empty fields for new product', async () => {
    renderProductForm()
    await screen.findByLabelText(/Assureur/i)
    expect(screen.getByLabelText(/code/i)).toHaveValue('')
    expect(screen.getByLabelText(/nom/i)).toHaveValue('')
    expect(screen.getByLabelText(/coût/i)).toHaveValue('')
  })

  it('renders form with product data for edit', async () => {
    renderProductForm({ product: mockProduct })
    await screen.findByLabelText(/Assureur/i)
    expect(screen.getByLabelText(/code/i)).toHaveValue('PROD001')
    expect(screen.getByLabelText(/nom/i)).toHaveValue('Produit Test')
    expect(screen.getByLabelText(/coût/i)).toHaveValue('100.5')
  })

  it('disables code field when editing', async () => {
    renderProductForm({ product: mockProduct })
    await screen.findByLabelText(/Assureur/i)
    expect(screen.getByLabelText(/code/i)).toBeDisabled()
  })

  it('shows validation errors for required fields', async () => {
    renderProductForm()
    await screen.findByLabelText(/Assureur/i)

    const submitButton = screen.getByText(/créer/i)
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/le code est requis/i)).toBeInTheDocument()
      expect(screen.getByText(/le nom est requis/i)).toBeInTheDocument()
      expect(screen.getByText(/le coût doit être supérieur à 0/i)).toBeInTheDocument()
      expect(screen.getByText(/sélectionnez un assureur/i)).toBeInTheDocument()
    })

    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit with correct data on valid submission', async () => {
    renderProductForm()
    const assureurSelect = await screen.findByLabelText(/Assureur/i)

    fireEvent.change(assureurSelect, { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText(/code/i), { target: { value: 'PROD002' } })
    fireEvent.change(screen.getByLabelText(/nom/i), { target: { value: 'Nouveau Produit' } })
    fireEvent.change(screen.getByLabelText(/coût/i), { target: { value: '150.75' } })

    const submitButton = screen.getByText(/créer/i)
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        code: 'PROD002',
        nom: 'Nouveau Produit',
        description: undefined,
        cout: 150.75,
        cle_repartition: 'fixe',
        est_actif: true,
        duree_validite_jours: undefined,
        conditions: undefined,
        garanties: undefined,
        assureur_id: 1,
        assureur: 'Assureur Test',
      })
    })
  })

  it('calls onCancel when cancel button is clicked', async () => {
    renderProductForm()
    await screen.findByLabelText(/Assureur/i)

    const cancelButton = screen.getByText(/annuler/i)
    fireEvent.click(cancelButton)

    expect(mockOnCancel).toHaveBeenCalled()
  })

  it('displays currency symbol correctly', async () => {
    const queryClient = new QueryClient()
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <ProductForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} currency="EUR" />
      </QueryClientProvider>
    )
    await screen.findByLabelText(/Assureur/i)
    expect(screen.getByText('€')).toBeInTheDocument()

    rerender(
      <QueryClientProvider client={queryClient}>
        <ProductForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} currency="USD" />
      </QueryClientProvider>
    )
    await screen.findByLabelText(/Assureur/i)
    expect(screen.getByText('$')).toBeInTheDocument()
  })
})
