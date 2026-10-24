import { test as base, expect } from '@playwright/test'
import { basename } from 'node:path'
import { getMockContextPages, watchMockContext } from './mockEgress'
import { assertNoUnexpectedApiRequests } from './mockApi'

export const test = base.extend({
  mockContextAudit: [async ({ context }, use, testInfo) => {
    const audit = watchMockContext(context, {
      testId: testInfo.testId,
      project: testInfo.project.name,
      file: basename(testInfo.file),
      line: testInfo.line
    })
    await use()
    try {
      audit.assertClean()
    } finally {
      audit.beginTeardown()
    }
  }, { auto: true }]
})
export { expect }

test.afterEach(async ({ context }) => {
  for (const page of new Set(getMockContextPages(context))) {
    assertNoUnexpectedApiRequests(page)
  }
})
