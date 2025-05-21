# Test info

- Name: Error Boundaries and Loading States >> Error Boundaries >> should navigate home from error boundary
- Location: /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:139:9

# Error details

```
Error: Timed out 5000ms waiting for expect(locator).toBeVisible()

Locator: locator('text=Something went wrong')
Expected: visible
Received: <element(s) not found>
Call log:
  - expect.toBeVisible with timeout 5000ms
  - waiting for locator('text=Something went wrong')

    at /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:150:63
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
  - heading "404" [level=1]
  - heading "This page could not be found." [level=2]
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
  121 |             status: 200,
  122 |             body: JSON.stringify({ data: 'success' })
  123 |           })
  124 |         }
  125 |       })
  126 |
  127 |       await page.goto('/dashboard')
  128 |       
  129 |       // Should show error first
  130 |       await expect(page.locator('text=Something went wrong')).toBeVisible()
  131 |       
  132 |       // Click try again
  133 |       await page.click('button:has-text("Try Again")')
  134 |       
  135 |       // Should recover and show normal content
  136 |       await expect(page.locator('text=Something went wrong')).not.toBeVisible()
  137 |     })
  138 |
  139 |     test('should navigate home from error boundary', async ({ page }) => {
  140 |       await page.route('**/api/trips', async route => {
  141 |         await route.fulfill({
  142 |           status: 500,
  143 |           body: JSON.stringify({ error: 'Server error' })
  144 |         })
  145 |       })
  146 |
  147 |       await page.goto('/dashboard/trips')
  148 |       
  149 |       // Should show error
> 150 |       await expect(page.locator('text=Something went wrong')).toBeVisible()
      |                                                               ^ Error: Timed out 5000ms waiting for expect(locator).toBeVisible()
  151 |       
  152 |       // Click go home
  153 |       await page.click('button:has-text("Go Home")')
  154 |       
  155 |       // Should navigate to home page
  156 |       await expect(page).toHaveURL('/')
  157 |     })
  158 |
  159 |     test('should show compact error for partial failures', async ({ page }) => {
  160 |       await page.goto('/dashboard')
  161 |       
  162 |       // Simulate partial component failure
  163 |       await page.route('**/api/dashboard/recent-trips', async route => {
  164 |         await route.fulfill({
  165 |           status: 500,
  166 |           body: JSON.stringify({ error: 'Failed to load recent trips' })
  167 |         })
  168 |       })
  169 |
  170 |       // Should show compact error message
  171 |       await expect(page.locator('text=Failed to load')).toBeVisible()
  172 |       await expect(page.locator('button:has-text("Retry")')).toBeVisible()
  173 |     })
  174 |
  175 |     test('should display error ID for tracking in development', async ({ page }) => {
  176 |       // This test would only run in development mode
  177 |       const isDev = process.env.NODE_ENV === 'development'
  178 |       
  179 |       if (isDev) {
  180 |         await page.route('**/api/test-error', async route => {
  181 |           await route.fulfill({
  182 |             status: 500,
  183 |             body: JSON.stringify({ error: 'Test error for development' })
  184 |           })
  185 |         })
  186 |
  187 |         await page.goto('/test-error-page') // hypothetical error page
  188 |         
  189 |         // Should show error ID in development
  190 |         await expect(page.locator('text=/Error ID: error_\\d+_\\w+/')).toBeVisible()
  191 |         await expect(page.locator('text=Test error for development')).toBeVisible()
  192 |       }
  193 |     })
  194 |   })
  195 |
  196 |   test.describe('Global Error Boundary', () => {
  197 |     test('should catch critical application errors', async ({ page }) => {
  198 |       // Simulate a critical error that would trigger global error boundary
  199 |       await page.addInitScript(() => {
  200 |         // Inject error after page loads
  201 |         setTimeout(() => {
  202 |           throw new Error('Critical application error')
  203 |         }, 1000)
  204 |       })
  205 |
  206 |       await page.goto('/')
  207 |       
  208 |       // Global error boundary should catch this
  209 |       await expect(page.locator('text=Critical Error')).toBeVisible({ timeout: 5000 })
  210 |       await expect(page.locator('text=The application encountered a critical error')).toBeVisible()
  211 |     })
  212 |   })
  213 |
  214 |   test.describe('Accessibility', () => {
  215 |     test('loading states should have proper ARIA labels', async ({ page }) => {
  216 |       await page.route('**/api/**', async route => {
  217 |         await page.waitForTimeout(1000)
  218 |         await route.continue()
  219 |       })
  220 |
  221 |       await page.goto('/dashboard')
  222 |       
  223 |       // Check for proper ARIA labels on loading elements
  224 |       const loadingElements = page.locator('[role="status"]')
  225 |       await expect(loadingElements.first()).toHaveAttribute('aria-label', 'Loading...')
  226 |       
  227 |       // Check for screen reader text
  228 |       await expect(page.locator('text=Loading...')).toBeVisible()
  229 |     })
  230 |
  231 |     test('error boundaries should be accessible', async ({ page }) => {
  232 |       await page.route('**/api/dashboard', async route => {
  233 |         await route.fulfill({ status: 500 })
  234 |       })
  235 |
  236 |       await page.goto('/dashboard')
  237 |       
  238 |       // Error UI should be accessible
  239 |       const errorHeading = page.locator('text=Something went wrong')
  240 |       await expect(errorHeading).toBeVisible()
  241 |       
  242 |       // Buttons should be focusable
  243 |       const tryAgainButton = page.locator('button:has-text("Try Again")')
  244 |       await expect(tryAgainButton).toBeFocused({ timeout: 1000 })
  245 |     })
  246 |   })
  247 |
  248 |   test.describe('Performance', () => {
  249 |     test('should not create memory leaks with frequent error/loading state changes', async ({ page }) => {
  250 |       // Test for memory leaks by rapidly triggering loading states
```