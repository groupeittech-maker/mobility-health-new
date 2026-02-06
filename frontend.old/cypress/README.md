# Frontend E2E Tests with Cypress

This directory contains end-to-end tests for the Mobility Health frontend using Cypress.

## Test Structure

- `cypress/e2e/`: End-to-end test files
  - `auth-flow.cy.ts`: Authentication flow tests
  - `subscription-flow.cy.ts`: Complete subscription flow tests
  - `sos-flow.cy.ts`: SOS flow tests
- `cypress/support/`: Support files and custom commands
  - `commands.ts`: Custom Cypress commands (login, logout)
  - `e2e.ts`: Global configuration

## Running Tests

### Install Dependencies
```bash
cd frontend
npm install
```

### Open Cypress Test Runner (Interactive)
```bash
npm run cypress:open
```

### Run Tests Headless
```bash
npm run cypress:run
```

### Run Specific Test File
```bash
npx cypress run --spec "cypress/e2e/auth-flow.cy.ts"
```

## Test Coverage

### Auth Flow (auth-flow.cy.ts)
- Successful login with valid credentials
- Error handling with invalid credentials
- User registration
- Logout functionality
- Route protection (redirects to login when not authenticated)

### Subscription Flow (subscription-flow.cy.ts)
- Complete subscription flow:
  1. Create travel project
  2. Select product
  3. Navigate to checkout
  4. Confirm subscription
  5. Navigate to questionnaire or success page
- Form validation
- Error handling

### SOS Flow (sos-flow.cy.ts)
- Trigger SOS alert
- SOS alert without active subscription (error handling)
- SOS agent dashboard (for operators)
- View alert details

## Custom Commands

### `cy.login(username, password)`
Logs in a user and stores the access token in localStorage.

```typescript
cy.login('testuser', 'testpassword123')
```

### `cy.logout()`
Removes authentication tokens from localStorage.

```typescript
cy.logout()
```

## Configuration

Cypress configuration is in `cypress.config.ts`:
- Base URL: `http://localhost:5173` (Vite dev server)
- Viewport: 1280x720
- Timeouts: 10 seconds for commands, requests, and responses

## Prerequisites

1. Backend API must be running on `http://localhost:8000`
2. Frontend dev server must be running on `http://localhost:5173`
3. Test users must exist in the database (see `scripts/create_test_users.py`)

## Writing New Tests

1. Create a new file in `cypress/e2e/`
2. Use the custom commands (`cy.login`, `cy.logout`) for authentication
3. Follow the existing test patterns
4. Use data-testid attributes when possible for more reliable selectors

Example:
```typescript
describe('My Feature', () => {
  beforeEach(() => {
    cy.login('testuser', 'testpassword123')
    cy.visit('/my-feature')
  })

  afterEach(() => {
    cy.logout()
  })

  it('should do something', () => {
    // Test implementation
  })
})
```




