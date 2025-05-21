# Test info

- Name: Error Boundaries and Loading States >> Global Error Boundary >> should catch critical application errors
- Location: /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:197:9

# Error details

```
Error: Timed out 5000ms waiting for expect(locator).toBeVisible()

Locator: locator('text=Critical Error')
Expected: visible
Received: <element(s) not found>
Call log:
  - expect.toBeVisible with timeout 5000ms
  - waiting for locator('text=Critical Error')

    at /home/bjorn/repos/agents/openai/agent1/tripsage-ai/frontend/e2e/error-boundaries-loading.spec.ts:209:57
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
- button "Open issues overlay": 3 Issue
- button "Collapse issues badge":
  - img
```

# Test source

```ts
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
  150 |       await expect(page.locator('text=Something went wrong')).toBeVisible()
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
> 209 |       await expect(page.locator('text=Critical Error')).toBeVisible({ timeout: 5000 })
      |                                                         ^ Error: Timed out 5000ms waiting for expect(locator).toBeVisible()
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
  251 |       for (let i = 0; i < 10; i++) {
  252 |         await page.route(`**/api/test-${i}`, async route => {
  253 |           await page.waitForTimeout(100)
  254 |           if (i % 2 === 0) {
  255 |             await route.fulfill({ status: 200, body: '{}' })
  256 |           } else {
  257 |             await route.fulfill({ status: 500 })
  258 |           }
  259 |         })
  260 |
  261 |         await page.goto(`/test-endpoint-${i}`)
  262 |         await page.waitForLoadState('networkidle')
  263 |       }
  264 |
  265 |       // If we get here without the page crashing, memory management is likely OK
  266 |       await expect(page.locator('body')).toBeVisible()
  267 |     })
  268 |
  269 |     test('should render loading skeletons efficiently', async ({ page }) => {
  270 |       const startTime = Date.now()
  271 |       
  272 |       await page.route('**/api/**', async route => {
  273 |         await page.waitForTimeout(500)
  274 |         await route.continue()
  275 |       })
  276 |
  277 |       await page.goto('/dashboard')
  278 |       
  279 |       // Check that loading skeletons appear quickly
  280 |       await expect(page.locator('[role="status"]').first()).toBeVisible({ timeout: 1000 })
  281 |       
  282 |       const loadingTime = Date.now() - startTime
  283 |       expect(loadingTime).toBeLessThan(2000) // Should render loading states quickly
  284 |     })
  285 |   })
  286 | })
```