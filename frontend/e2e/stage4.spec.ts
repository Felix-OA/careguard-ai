import { expect, test } from '@playwright/test'

test('completes the local controlled Stage 4 workflow', async ({ page }) => {
  await page.goto('/agentic')
  await expect(page.getByRole('heading', { name: 'Agentic audit' })).toBeVisible()
  await expect(page.getByText('No shell, filesystem, browser, arbitrary network')).toBeVisible()

  const runCampaign = async (path: 'baseline' | 'guarded') => {
    await page.goto('/agentic/new')
    await page.getByLabel('Target path').selectOption(path)
    await page.getByLabel('Seed').fill('42')
    await page.getByLabel('Turns per objective').fill('5')
    await page.getByLabel('Total-turn limit').fill('50')
    await page.getByRole('checkbox', { name: /authorized local synthetic target/i }).check()
    await page.getByRole('button', { name: 'Start controlled campaign' }).click()
    const link = page.getByRole('link', { name: 'Open campaign' })
    await expect(link).toBeVisible({ timeout: 120_000 })
    const href = await link.getAttribute('href')
    expect(href).toMatch(/^\/agentic\/ac-[a-f0-9]{24}$/)
    return href!.split('/').at(-1)!
  }

  const baseline = await runCampaign('baseline')
  const guarded = await runCampaign('guarded')

  await page.goto(`/agentic/${guarded}`)
  await expect(page.getByRole('heading', { name: 'Healthcare-safe controlled campaign' })).toBeVisible()
  await expect(page.getByLabel('Status: REVIEW').first()).toBeVisible()
  await page.getByRole('link', { name: 'Inspect sanitized trajectory' }).first().click()
  await expect(page.getByText('Attacker message').first()).toBeVisible()
  await expect(page.getByText(/Target response|Guard-generated response/).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Evaluator output' }).first()).toBeVisible()
  await expect(page.locator('body')).not.toContainText('<think>')

  await page.goto('/reviews')
  await expect(page.getByRole('heading', { name: 'CG-AO-008', exact: true }).first()).toBeVisible()
  const agenticCard = page.getByRole('heading', { name: 'CG-AO-008', exact: true }).first().locator('..')
  await expect(agenticCard).toContainText('REVIEW')
  await agenticCard.getByRole('link', { name: 'Inspect sanitized trajectory →' }).click()
  await expect(page.getByText(/Reviewer decisions are stored separately/)).toBeVisible()

  await page.goto('/agentic')
  await page.getByLabel('Baseline campaign').selectOption(baseline)
  await page.getByLabel('Guarded campaign').selectOption(guarded)
  const comparisonLinks = page.locator('a[href^="/agentic/comparisons/acmp-"]')
  const comparisonCount = await comparisonLinks.count()
  await page.getByRole('button', { name: 'Generate comparison' }).click()
  await expect(comparisonLinks).toHaveCount(comparisonCount + 1)
  const comparisonLink = comparisonLinks.first()
  await expect(comparisonLink).toBeVisible()
  await comparisonLink.click()
  await expect(page.getByText('Identical scope verified')).toBeVisible()
  await expect(page.getByRole('table', { name: 'Agentic objective comparison' })).toBeVisible()
  await page.getByRole('link', { name: 'Preview report' }).click()
  await expect(page.locator('.report-preview')).toBeVisible()
  await expect(page.getByText('Protected raw responses and unrestricted tool arguments are excluded.', { exact: true }).first()).toBeVisible()

  await page.goto('/settings')
  await expect(page.getByText('agentic-runner')).toBeVisible()
  await expect(page.getByText('Stage 4 boundaries')).toBeVisible()
})
