# Test info

- Name: Error Boundaries and Loading States >> Loading States >> should show loading skeleton on initial page load
- Location: /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:10:9

# Error details

```
Error: Timed out 5000ms waiting for expect(locator).toBeVisible()

Locator: locator('[role="status"]').first()
Expected: visible
Received: <element(s) not found>
Call log:
  - expect.toBeVisible with timeout 5000ms
  - waiting for locator('[role="status"]').first()

    at /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:20:61
```

# Page snapshot

```yaml
- banner:
  - link "TripSageAI":
    - /url: /
  - navigation:
    - link "Home":
      - /url: /
    - link "Trips":
      - /url: /trips
    - link "Itinerary":
      - /url: /itinerary
    - link "Settings":
      - /url: /settings
  - link "Log in":
    - /url: /login
  - link "Sign up":
    - /url: /signup
  - button
- main:
  - link "TripSage AI":
    - /url: /
  - link "Log in":
    - /url: /auth/login
    - button "Log in"
  - link "Sign up":
    - /url: /auth/register
    - button "Sign up"
  - main:
    - heading "Plan Your Perfect Trip with TripSage AI" [level=1]
    - paragraph: Intelligent travel planning powered by AI. Get personalized recommendations, budget optimization, and seamless booking - all in one place.
    - link "Get Started":
      - /url: /auth/register
      - button "Get Started"
    - link "Try Demo":
      - /url: /dashboard/chat
      - button "Try Demo"
    - img "TripSage AI"
    - heading "Why Choose TripSage AI?" [level=2]
    - paragraph: Our AI-powered platform makes travel planning simpler, smarter, and more personalized than ever before.
    - heading "AI-Powered Planning" [level=3]
    - paragraph: Get intelligent recommendations based on your preferences, budget, and travel style.
    - heading "Budget Optimization" [level=3]
    - paragraph: Find the best deals and optimize your spending across flights, hotels, and activities.
    - heading "All-in-One Platform" [level=3]
    - paragraph: Plan, book, and manage your entire trip in one seamless experience.
  - paragraph: © 2025 TripSage AI. All rights reserved.
  - link "Privacy":
    - /url: /privacy
  - link "Terms":
    - /url: /terms
  - link "Contact":
    - /url: /contact
- region "Notifications (F8)":
  - list
- alert
- button "Open Next.js Dev Tools":
  - img
- button "Open issues overlay": 2 Issue
- button "Collapse issues badge":
  - img
```

# Test source

```ts
   1 | import { test, expect } from '@playwright/test'
   2 |
   3 | test.describe('Error Boundaries and Loading States', () => {
   4 |   test.beforeEach(async ({ page }) => {
   5 |     // Navigate to the app
   6 |     await page.goto('/')
   7 |   })
   8 |
   9 |   test.describe('Loading States', () => {
   10 |     test('should show loading skeleton on initial page load', async ({ page }) => {
   11 |       // Intercept API calls to simulate slow loading
   12 |       await page.route('**/api/**', async route => {
   13 |         await page.waitForTimeout(2000) // Simulate slow API
   14 |         await route.continue()
   15 |       })
   16 |
   17 |       await page.goto('/')
   18 |       
   19 |       // Should show loading skeleton initially
>  20 |       await expect(page.locator('[role="status"]').first()).toBeVisible()
      |                                                             ^ Error: Timed out 5000ms waiting for expect(locator).toBeVisible()
   21 |       
   22 |       // Wait for content to load
   23 |       await page.waitForLoadState('networkidle')
   24 |       
   25 |       // Loading should be replaced with actual content
   26 |       await expect(page.locator('[role="status"]')).toHaveCount(0)
   27 |     })
   28 |
   29 |     test('should show appropriate loading skeleton for dashboard', async ({ page }) => {
   30 |       await page.route('**/api/dashboard/**', async route => {
   31 |         await page.waitForTimeout(1000)
   32 |         await route.fulfill({
   33 |           status: 200,
   34 |           body: JSON.stringify({ trips: [], stats: {} })
   35 |         })
   36 |       })
   37 |
   38 |       await page.goto('/dashboard')
   39 |       
   40 |       // Check for dashboard-specific loading elements
   41 |       await expect(page.locator('[role="status"]')).toHaveCount({ min: 5 })
   42 |       
   43 |       // Wait for loading to complete
   44 |       await page.waitForLoadState('networkidle')
   45 |     })
   46 |
   47 |     test('should show chat loading skeleton', async ({ page }) => {
   48 |       await page.goto('/dashboard/chat')
   49 |       
   50 |       // Simulate loading chat history
   51 |       await page.route('**/api/chat/history', async route => {
   52 |         await page.waitForTimeout(1000)
   53 |         await route.fulfill({
   54 |           status: 200,
   55 |           body: JSON.stringify({ messages: [] })
   56 |         })
   57 |       })
   58 |
   59 |       // Should show chat loading skeleton
   60 |       await expect(page.locator('[role="status"]')).toHaveCount({ min: 3 })
   61 |       
   62 |       // Check for typing indicator (if applicable)
   63 |       await expect(page.locator('.animate-bounce')).toHaveCount({ min: 3 })
   64 |     })
   65 |
   66 |     test('should show search results loading skeleton', async ({ page }) => {
   67 |       await page.goto('/dashboard/search/flights')
   68 |       
   69 |       // Fill in search form
   70 |       await page.fill('[name="origin"]', 'NYC')
   71 |       await page.fill('[name="destination"]', 'LAX')
   72 |       
   73 |       // Intercept search API
   74 |       await page.route('**/api/search/flights', async route => {
   75 |         await page.waitForTimeout(2000)
   76 |         await route.fulfill({
   77 |           status: 200,
   78 |           body: JSON.stringify({ results: [] })
   79 |         })
   80 |       })
   81 |
   82 |       await page.click('button[type="submit"]')
   83 |       
   84 |       // Should show search results skeleton
   85 |       await expect(page.locator('[role="status"]')).toHaveCount({ min: 10 })
   86 |     })
   87 |   })
   88 |
   89 |   test.describe('Error Boundaries', () => {
   90 |     test('should catch and display route-level errors gracefully', async ({ page }) => {
   91 |       // Simulate a route error by returning 500
   92 |       await page.route('**/api/dashboard', async route => {
   93 |         await route.fulfill({
   94 |           status: 500,
   95 |           body: JSON.stringify({ error: 'Internal server error' })
   96 |         })
   97 |       })
   98 |
   99 |       await page.goto('/dashboard')
  100 |       
  101 |       // Should show error boundary UI
  102 |       await expect(page.locator('text=Something went wrong')).toBeVisible()
  103 |       await expect(page.locator('button:has-text("Try Again")')).toBeVisible()
  104 |       await expect(page.locator('button:has-text("Go Home")')).toBeVisible()
  105 |     })
  106 |
  107 |     test('should allow error recovery with try again button', async ({ page }) => {
  108 |       let requestCount = 0
  109 |       
  110 |       await page.route('**/api/dashboard', async route => {
  111 |         requestCount++
  112 |         if (requestCount === 1) {
  113 |           // First request fails
  114 |           await route.fulfill({
  115 |             status: 500,
  116 |             body: JSON.stringify({ error: 'Server error' })
  117 |           })
  118 |         } else {
  119 |           // Second request succeeds
  120 |           await route.fulfill({
```