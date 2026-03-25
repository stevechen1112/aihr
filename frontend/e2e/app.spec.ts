import { test, expect } from '@playwright/test'

/**
 * These tests require a running backend with a valid test user.
 * Set E2E_USER_EMAIL and E2E_USER_PASSWORD env vars.
 */
const EMAIL = process.env.E2E_USER_EMAIL || 'test@example.com'
const PASSWORD = process.env.E2E_USER_PASSWORD || 'testpassword'
const hasCreds = !!process.env.E2E_USER_EMAIL && !!process.env.E2E_USER_PASSWORD

test.describe('Document Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCreds, 'Authenticated E2E requires E2E_USER_EMAIL and E2E_USER_PASSWORD')
    // Login
    await page.goto('/login')
    await page.fill('input[type="email"], input[name="email"], input[placeholder*="mail"]', EMAIL)
    await page.fill('input[type="password"]', PASSWORD)
    await page.click('button[type="submit"]')
    await expect(page).not.toHaveURL(/\/login(?:\?|$)/)
  })

  test('should navigate to documents page', async ({ page }) => {
    await page.goto('/app/documents')
    await expect(page.locator('h1, h2, [class*="title"]')).toContainText(/文件|Documents/i)
  })
})

test.describe('Chat Flow', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!hasCreds, 'Authenticated E2E requires E2E_USER_EMAIL and E2E_USER_PASSWORD')
    await page.goto('/login')
    await page.fill('input[type="email"], input[name="email"], input[placeholder*="mail"]', EMAIL)
    await page.fill('input[type="password"]', PASSWORD)
    await page.click('button[type="submit"]')
    await expect(page).not.toHaveURL(/\/login(?:\?|$)/)
  })

  test('should navigate to chat page', async ({ page }) => {
    await page.goto('/app')
    await expect(page.locator('textarea, input[placeholder*="問"], input[placeholder*="ask"]')).toBeVisible()
  })
})
