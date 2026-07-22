import { expect, test } from '@playwright/test'

test('completes the local synthetic Stage 3 workflow', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Healthcare AI security, without the guesswork' })).toBeVisible()
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeFocused()

  await page.goto('/onboarding')
  await page.getByRole('checkbox', { name: /I confirm this environment/i }).check()
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.locator('legend', { hasText: 'Choose target type' })).toBeVisible()
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.locator('legend', { hasText: 'Connector mapping' })).toBeVisible()
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByText('No secret values are accepted here.')).toBeVisible()
  await expect(page.locator('input[type="password"]')).toHaveCount(0)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.locator('legend', { hasText: 'Integration capability' })).toBeVisible()
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.locator('legend', { hasText: 'Healthcare policy selection' })).toBeVisible()
  await page.getByRole('button', { name: 'Save configuration' }).click()
  await expect(page.locator('legend', { hasText: 'Harmless connection test' })).toBeVisible()
  await page.getByRole('button', { name: 'Test connection' }).click()
  await expect(page.locator('legend', { hasText: 'Initial audit' })).toBeVisible()

  const runAudit = async (path: 'baseline' | 'guarded') => {
    await page.goto('/audits/new')
    await page.getByLabel('Path type').selectOption(path)
    await page.getByRole('button', { name: 'Start audit' }).click()
    const resultLink = page.getByRole('link', { name: 'Open audit' })
    await expect(resultLink).toBeVisible({ timeout: 60_000 })
    const href = await resultLink.getAttribute('href')
    expect(href).toMatch(/^\/audits\/cg-/)
    return href!.split('/').at(-1)!
  }

  const baselineRun = await runAudit('baseline')
  const guardedRun = await runAudit('guarded')

  await page.goto(`/audits/${guardedRun}`)
  await expect(page.getByRole('heading', { name: 'Audit detail' })).toBeVisible()
  await expect(page.getByText('Denied proposals, not executions.')).toBeVisible()
  await expect(page.getByLabel('Status: REVIEW').first()).toBeVisible()

  await page.goto('/comparisons')
  await page.getByLabel('Baseline run').selectOption(baselineRun)
  await page.getByLabel('Guarded run').selectOption(guardedRun)
  await page.getByRole('button', { name: 'Generate comparison' }).click()
  await expect(page.locator('a.comparison-card').first()).toBeVisible()
  await page.locator('a.comparison-card').first().click()
  await expect(page.getByText('Identical scope verified')).toBeVisible()
  await expect(page.getByRole('table', { name: 'Baseline versus guarded scenario outcomes' })).toBeVisible()

  await page.goto('/reviews')
  await expect(page.getByRole('heading', { name: 'Review queue' })).toBeVisible()
  for (const scenarioId of ['CG-S002', 'CG-S004', 'CG-S008', 'CG-S009', 'CG-S010', 'CG-S013', 'CG-S015']) {
    await expect(page.getByRole('heading', { name: scenarioId, exact: true }).first()).toBeVisible()
  }
  await page.getByRole('button', { name: 'Record review' }).first().click()
  await expect(page.getByRole('dialog')).toContainText('This decision will not overwrite the automated evidence.')
  await page.getByRole('button', { name: 'Close review dialog' }).click()

  await page.goto('/events')
  const eventLink = page.locator('tbody a').first()
  await expect(eventLink).toBeVisible()
  await eventLink.click()
  await expect(page.getByRole('heading', { name: 'Sanitized event detail' })).toBeVisible()
  await expect(page.getByRole('table', { name: 'Safe source metadata without excerpts' })).toBeVisible()
  await expect(page.locator('body')).not.toContainText('raw_target_response_reference')

  await page.goto('/policies')
  await expect(page.getByRole('heading', { name: '15 policies, traceable to controls' })).toBeVisible()
  await page.locator('a.policy-card').first().click()
  await expect(page.getByRole('heading', { name: 'Control coverage' })).toBeVisible()

  await page.goto('/reports')
  await page.getByRole('link', { name: new RegExp(guardedRun) }).click()
  await expect(page.locator('.report-preview')).toBeVisible()
  await expect(page.locator('.report-boundaries').getByText('Not a production security guarantee.', { exact: true })).toBeVisible()

  await page.goto('/demo')
  await page.getByRole('button', { name: 'Send to guarded' }).click()
  await expect(page.locator('.demo-column.guarded .demo-result')).toBeVisible()

  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: 'System and limitations' })).toBeVisible()
  await expect(page.getByText('Stage 3 boundaries')).toBeVisible()
})
