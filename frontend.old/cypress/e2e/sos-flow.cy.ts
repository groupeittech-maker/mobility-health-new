describe('SOS Flow', () => {
  beforeEach(() => {
    cy.login('testuser', 'testpassword123')
    cy.visit('/')
  })

  afterEach(() => {
    cy.logout()
  })

  it('should trigger SOS alert successfully', () => {
    // Navigate to SOS page or trigger button
    cy.visit('/sos')
    // Or look for SOS button in navigation/dashboard
    cy.get('button:contains("SOS"), button:contains("Alerte"), [data-testid="sos-trigger"]').click()
    
    // Fill SOS form
    cy.get('input[name="adresse"], textarea[name="adresse"], input[placeholder*="adresse" i]').type('123 Test Street, Paris')
    cy.get('textarea[name="description"], textarea[name="description"]').type('Medical emergency - need assistance')
    cy.get('select[name="priorite"], input[name="priorite"]').select('haute')
    
    // Submit SOS alert
    cy.get('button[type="submit"], button:contains("Envoyer"), button:contains("Déclencher")').click()
    
    // Should show success message or confirmation
    cy.get('.success, [role="alert"]:contains("succès"), .alert-success').should('be.visible')
    
    // Should show alert number or confirmation
    cy.get('body').should('contain', 'ALERT')
  })

  it('should show error when triggering SOS without active subscription', () => {
    // Logout and login with user without subscription
    cy.logout()
    cy.login('userwithoutsubscription', 'password123')
    cy.visit('/sos')
    
    // Try to trigger SOS
    cy.get('button:contains("SOS"), [data-testid="sos-trigger"]').click()
    cy.get('button[type="submit"], button:contains("Envoyer")').click()
    
    // Should show error about missing subscription
    cy.get('.error, [role="alert"]').should('contain', 'souscription')
  })

  it('should display SOS agent dashboard for operators', () => {
    cy.logout()
    cy.login('sosoperator', 'sospassword123')
    cy.visit('/sos-agent-dashboard')
    
    // Should see list of alerts
    cy.get('h1, h2').should('contain', 'SOS')
    // Should see alerts table or list
    cy.get('table, [data-testid="alerts-list"], .alerts-list').should('exist')
  })

  it('should allow viewing alert details', () => {
    cy.visit('/sos')
    
    // If there are existing alerts, click on one
    cy.get('[data-testid="alert-item"], .alert-item, tr').first().click()
    
    // Should show alert details
    cy.get('h1, h2').should('contain', 'Alerte')
    cy.get('body').should('contain', 'Description')
    cy.get('body').should('contain', 'Statut')
  })
})




