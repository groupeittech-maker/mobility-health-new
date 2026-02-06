describe('Authentication Flow', () => {
  beforeEach(() => {
    cy.visit('/')
  })

  it('should login successfully with valid credentials', () => {
    cy.visit('/login')
    
    cy.get('input[name="username"], input[type="text"]').first().type('testuser')
    cy.get('input[name="password"], input[type="password"]').type('testpassword123')
    cy.get('button[type="submit"], button:contains("Connexion"), button:contains("Login")').click()
    
    // Should redirect to dashboard or home
    cy.url().should('not.include', '/login')
    // Should have token in localStorage
    cy.window().its('localStorage').invoke('getItem', 'access_token').should('exist')
  })

  it('should show error with invalid credentials', () => {
    cy.visit('/login')
    
    cy.get('input[name="username"], input[type="text"]').first().type('invaliduser')
    cy.get('input[name="password"], input[type="password"]').type('wrongpassword')
    cy.get('button[type="submit"], button:contains("Connexion")').click()
    
    // Should show error message
    cy.get('.error, [role="alert"], .alert-danger, .error-message').should('be.visible')
    cy.url().should('include', '/login')
  })

  it('should register new user successfully', () => {
    cy.visit('/register')
    
    const timestamp = Date.now()
    const email = `test${timestamp}@example.com`
    const username = `testuser${timestamp}`
    
    cy.get('input[name="email"], input[type="email"]').type(email)
    cy.get('input[name="username"], input[type="text"]').first().type(username)
    cy.get('input[name="password"], input[type="password"]').first().type('testpassword123')
    cy.get('input[name="full_name"], input[name="fullName"]').type('Test User')
    
    cy.get('button[type="submit"], button:contains("Inscription"), button:contains("Register")').click()
    
    // Should redirect after successful registration
    cy.url().should('not.include', '/register')
  })

  it('should logout successfully', () => {
    cy.login('testuser', 'testpassword123')
    cy.visit('/')
    
    // Click logout button
    cy.get('button:contains("Déconnexion"), button:contains("Logout"), [data-testid="logout"]').click()
    
    // Should redirect to login or home
    cy.url().should('match', /\/login|\/$/)
    // Token should be removed
    cy.window().its('localStorage').invoke('getItem', 'access_token').should('be.null')
  })

  it('should protect routes requiring authentication', () => {
    cy.logout()
    
    // Try to access protected route
    cy.visit('/travel-project')
    
    // Should redirect to login
    cy.url().should('include', '/login')
  })
})




