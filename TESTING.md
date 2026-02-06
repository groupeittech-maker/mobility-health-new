# Testing Guide - Mobility Health

This document provides an overview of the testing strategy for the Mobility Health platform.

## Overview

The project includes comprehensive testing at both backend and frontend levels:

- **Backend**: pytest + httpx tests with 90% coverage target
- **Frontend**: Jest unit tests + Cypress E2E tests

## Backend Tests

### Location
`app/tests/`

### Test Files
- `conftest.py`: Test fixtures and configuration
- `test_auth_flows.py`: Authentication flow tests
- `test_subscription_e2e.py`: End-to-end subscription flow tests
- `test_sos_flow.py`: SOS flow tests

### Running Backend Tests

```bash
# Run all tests with coverage
pytest app/tests/ -v --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=90

# Run specific test suite
pytest app/tests/test_auth_flows.py -v
pytest app/tests/test_subscription_e2e.py -v
pytest app/tests/test_sos_flow.py -v

# Run by marker
pytest -m auth -v        # Authentication tests
pytest -m subscription -v  # Subscription tests
pytest -m sos -v         # SOS tests
pytest -m e2e -v         # All E2E tests
```

### Test Coverage

#### Auth Flows
- ✅ User registration (success, duplicates, validation)
- ✅ User login (success, failures, inactive users)
- ✅ Token refresh
- ✅ Logout
- ✅ Get current user
- ✅ Token expiration handling

#### Subscription E2E Flow
- ✅ Create travel project
- ✅ Choose insurance product
- ✅ Complete questionnaire (short and long)
- ✅ Initiate payment
- ✅ Payment webhook processing
- ✅ Attestation generation
- ✅ Error handling (inactive products, missing data, etc.)

#### SOS Flow
- ✅ Trigger SOS alert
- ✅ Agent reception and notification
- ✅ Automatic sinistre creation
- ✅ Hospital finding
- ✅ Alert list and detail views
- ✅ Access control

## Frontend Tests

### Unit Tests

#### Location
`frontend/src/__tests__/`

#### Test Files
- `TravelProjectFormPage.test.tsx`: Travel project form tests
- `CheckoutPage.test.tsx`: Checkout page tests

#### Running Unit Tests

```bash
cd frontend
npm test                 # Run all tests
npm run test:watch       # Watch mode
npm run test:coverage    # With coverage
```

### E2E Tests (Cypress)

#### Location
`frontend/cypress/e2e/`

#### Test Files
- `auth-flow.cy.ts`: Authentication flow E2E tests
- `subscription-flow.cy.ts`: Complete subscription flow E2E tests
- `sos-flow.cy.ts`: SOS flow E2E tests

#### Running Cypress Tests

```bash
cd frontend
npm run cypress:open      # Interactive mode
npm run cypress:run       # Headless mode
```

#### Prerequisites for E2E Tests
1. Backend API running on `http://localhost:8000`
2. Frontend dev server running on `http://localhost:5173`
3. Test users created in database

## Test Data

### Creating Test Users

Use the provided script to create test users:

```bash
# Python script
python scripts/create_test_users.py

# Or PowerShell
.\scripts\create_test_users.ps1
```

### Test Users

The following test users should exist:
- `testuser` / `testpassword123` (regular user)
- `admin` / `adminpassword123` (admin)
- `sosoperator` / `sospassword123` (SOS operator)
- `doctor` / `doctorpassword123` (doctor)

## Coverage Goals

- **Backend**: 90% code coverage (enforced by pytest configuration)
- **Frontend**: Unit tests for critical components, E2E tests for critical user flows

## Continuous Integration

### Recommended CI/CD Pipeline

```yaml
# Example GitHub Actions workflow
- name: Run Backend Tests
  run: pytest app/tests/ -v --cov=app --cov-fail-under=90

- name: Run Frontend Unit Tests
  run: cd frontend && npm test

- name: Run Frontend E2E Tests
  run: |
    cd frontend
    npm run cypress:run
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Clean State**: Tests should clean up after themselves (fixtures handle this)
3. **Realistic Data**: Use realistic test data that matches production scenarios
4. **Error Cases**: Test both success and failure paths
5. **Edge Cases**: Test boundary conditions and edge cases
6. **Access Control**: Test authorization and access control thoroughly

## Troubleshooting

### Backend Tests

**Issue**: Tests fail with database errors
- **Solution**: Ensure test database is properly isolated (SQLite in-memory)

**Issue**: Redis connection errors
- **Solution**: Mock Redis or use a test Redis instance

### Frontend Tests

**Issue**: Tests fail with "Cannot find module"
- **Solution**: Run `npm install` in the frontend directory

**Issue**: Cypress tests fail with connection errors
- **Solution**: Ensure both backend and frontend servers are running

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Cypress Documentation](https://docs.cypress.io/)
- [React Testing Library](https://testing-library.com/react)
- [Jest Documentation](https://jestjs.io/)















