# Frontend Unit Tests

This directory contains unit tests for React components using Jest and React Testing Library.

## Test Structure

- `TravelProjectFormPage.test.tsx`: Tests for the travel project form page
- `CheckoutPage.test.tsx`: Tests for the checkout page

## Running Tests

### Run all tests
```bash
npm test
```

### Run in watch mode
```bash
npm run test:watch
```

### Run with coverage
```bash
npm run test:coverage
```

## Test Coverage

### TravelProjectFormPage
- Renders page title and subtitle
- Renders the travel project form
- Navigates to products page after successful project creation
- Shows error alert on project creation failure

### CheckoutPage
- Shows error message when projet_id or product_id is missing
- Shows loading state while fetching data
- Renders checkout page with project and product data
- Creates subscription on confirm button click
- Navigates to success page after subscription creation

## Configuration

Jest configuration is in `jest.config.js`:
- Test environment: jsdom (for DOM testing)
- Setup files: `src/setupTests.ts`
- Module name mapping for CSS imports
- TypeScript support via ts-jest

## Writing New Tests

1. Create a test file: `ComponentName.test.tsx`
2. Import testing utilities from `@testing-library/react`
3. Mock API calls and external dependencies
4. Test user interactions and component behavior

Example:
```typescript
import { render, screen } from '@testing-library/react'
import MyComponent from '../components/MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
})
```




