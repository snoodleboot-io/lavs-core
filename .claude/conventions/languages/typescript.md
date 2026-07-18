# Core Conventions TypeScript

Language:             typescript e.g., TypeScript 5.x
Runtime:              v6.0 e.g., Node 20, Deno, Bun
Package Manager:      pnpm e.g., npm, pnpm, yarn
Linter:               eslint e.g., ESLint
Formatter:           prettier e.g., Prettier

### Naming Conventions

Files:               kebab-case
Variables:          camelCase
Constants:          UPPER_SNAKE
Classes/Types:      PascalCase
Functions:          camelCase
Database tables:    snake_case
Environment vars:   UPPER_SNAKE_CASE always

## TypeScript-Specific Rules

### Type System
- strict mode always on in tsconfig.json
- No `any` — use `unknown` + type narrowing
- Prefer `interface` for object shapes, `type` for unions/intersections
- Always type function return values explicitly
- Use `const` assertions (`as const`) for literal types

### Error Handling
- Use typed error unions: `function foo(): Result<T, FooError | BarError>`
- Never use `throw` in library code — return errors instead
- Use `never` for functions that don't return

### Imports & Exports
- Use path aliases (`@/`) configured in tsconfig.json
- Prefer named exports over default exports
- Use barrel files (index.ts) for clean public APIs
- Order imports: external → internal → types (with blank lines between)

### Testing

#### Coverage Targets
Line:           80          e.g., 80%
Branch:           70          e.g., 70%
Function:           90          e.g., 90%
Statement:           85          e.g., 85%
Mutation:           80          e.g., 80%
Path:           60          e.g., 60%

#### Test Types

##### Unit Tests
- One function or method in isolation
- Mock external dependencies (APIs, filesystem, database)
- Use `describe`/`it` blocks with descriptive names
- Test behavior, not implementation

##### Integration Tests
- Test at service or module boundary
- Use real services or in-memory alternatives (msw, testcontainers)
- Test API endpoints, database queries, file operations

##### E2E Tests
- Use Playwright or Cypress for browser testing
- Test critical user flows end-to-end

##### Component Tests
- Use Testing Library (@testing-library/react, @testing-library/vue)
- Test component rendering and user interactions

##### Mutation Tests
- Use `stryker-mutator` to verify test quality
- Run after unit tests pass

#### Framework & Tools
Framework:         vitest

### Code Style
- Use ESNext features (optional chaining, nullish coalescing)
- Prefer immutable patterns — use `readonly` for arrays/objects
- Use `enum` sparingly — prefer const objects or unions