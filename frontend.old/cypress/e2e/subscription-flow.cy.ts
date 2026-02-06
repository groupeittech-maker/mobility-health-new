describe('Subscription E2E Flow', () => {
  beforeEach(() => {
    // Setup: Create test user and login
    cy.login('testuser', 'testpassword123')
    cy.visit('/')
  })

  afterEach(() => {
    cy.logout()
  })

  it('should complete full subscription flow', () => {
    // Step 1: Create travel project
    cy.visit('/travel-project')
    cy.get('h1').should('contain', 'Créer un projet de voyage')
    
    // Fill travel project form
    cy.get('input[name="titre"], input[placeholder*="titre" i]').type('Vacation to Paris')
    cy.get('input[name="destination"], input[placeholder*="destination" i]').type('Paris, France')
    cy.get('input[name="date_depart"], input[type="date"]').first().type('2024-06-01')
    cy.get('input[name="date_retour"], input[type="date"]').last().type('2024-06-15')
    cy.get('input[name="nombre_participants"], input[type="number"]').type('2')
    
    // Submit form
    cy.get('button[type="submit"], button:contains("Créer")').click()
    
    // Step 2: Should navigate to products page
    cy.url().should('include', '/products')
    cy.url().should('include', 'projet_id=')
    
    // Step 3: Select a product
    cy.get('[data-testid="product-card"], .product-card, article').first().click()
    // Or click on a "Select" or "Choose" button
    cy.get('button:contains("Sélectionner"), button:contains("Choisir"), a:contains("Sélectionner")').first().click()
    
    // Step 4: Should navigate to checkout
    cy.url().should('include', '/checkout')
    cy.url().should('include', 'product_id=')
    
    // Step 5: Confirm subscription
    cy.get('h1').should('contain', 'Finaliser votre souscription')
    cy.get('button:contains("Confirmer"), button:contains("Valider"), button[type="submit"]').click()
    
    // Step 6: Should navigate to questionnaire or success page
    cy.url().should('match', /\/questionnaire|\/subscription-success/)
  })

  it('should show error when required fields are missing in travel project form', () => {
    cy.visit('/travel-project')
    
    // Try to submit without filling required fields
    cy.get('button[type="submit"], button:contains("Créer")').click()
    
    // Should show validation errors
    cy.get('.error, [role="alert"], .invalid-feedback').should('exist')
  })

  it('should handle product selection and navigate to checkout', () => {
    // Assume we're already on products page with projet_id
    cy.visit('/products?projet_id=1')
    
    // Wait for products to load
    cy.get('[data-testid="product-card"], .product-card, article, .product-item').should('exist')
    
    // Select a product
    cy.get('[data-testid="product-card"], .product-card, article').first().within(() => {
      cy.get('button:contains("Sélectionner"), a:contains("Sélectionner"), button:contains("Choisir")').click()
    })
    
    // Should navigate to checkout
    cy.url().should('include', '/checkout')
    cy.url().should('include', 'product_id=')
  })
})




