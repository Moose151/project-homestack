// Shared checks for docs/36_Mobile_UX_Strategy_and_Implementation_Plan.md §9.1 global acceptance
// criteria. New mobile-converted screens should reuse these rather than re-deriving the checks.
import { expect, type Locator, type Page } from '@playwright/test'

/** §9.1: "No accidental document-level horizontal scrolling on ordinary screens at 320px+." */
export async function expectNoHorizontalOverflow(page: Page) {
  const result = await page.evaluate(() => {
    const root = document.documentElement
    const overflow = root.scrollWidth - root.clientWidth
    const offenders = [...document.querySelectorAll<HTMLElement>('body *')]
      .map(element => {
        const rect = element.getBoundingClientRect()
        return { element, rect }
      })
      .filter(({ rect }) => rect.right > root.clientWidth + 1 || rect.left < -1)
      .slice(0, 5)
      .map(({ element, rect }) => ({
        tag: element.tagName.toLowerCase(),
        label: element.getAttribute('aria-label') || element.textContent?.trim().slice(0, 60) || '',
        left: Math.round(rect.left),
        right: Math.round(rect.right),
        width: Math.round(rect.width),
      }))
    return { overflow, offenders }
  })
  expect(
    result.overflow,
    `document should not scroll horizontally; offenders: ${JSON.stringify(result.offenders)}`,
  ).toBeLessThanOrEqual(1)
}

/** §3.3 / §9.1: "Primary routine controls meet the approximately 44px touch-target baseline." */
export async function expectMinTouchTarget(locator: Locator, min = 44) {
  const box = await locator.boundingBox()
  expect(box, 'element should have a visible bounding box').not.toBeNull()
  if (!box) return
  // "approximately" — allow a couple of px of rounding/border slack rather than a hard cutoff.
  expect(box.width, 'touch target width').toBeGreaterThanOrEqual(min - 2)
  expect(box.height, 'touch target height').toBeGreaterThanOrEqual(min - 2)
}
