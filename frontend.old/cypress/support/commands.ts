/// <reference types="cypress" />

// Custom command to login
Cypress.Commands.add('login', (username: string, password: string) => {
  cy.request({
    method: 'POST',
    url: 'http://localhost:8000/api/v1/auth/login',
    body: {
      username,
      password,
    },
    form: true,
  }).then((response) => {
    expect(response.status).to.eq(200)
    const { access_token } = response.body
    window.localStorage.setItem('access_token', access_token)
    window.localStorage.setItem('user_id', '1')
  })
})

// Custom command to logout
Cypress.Commands.add('logout', () => {
  window.localStorage.removeItem('access_token')
  window.localStorage.removeItem('user_id')
})




