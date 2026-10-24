import { assertNoMockEgress } from './mockEgress.js'

export default async function mockEgressTeardown() {
  // Playwright runs global teardown after workers and their browser contexts
  // have completed. The preview's atomic record is the independent final gate.
  assertNoMockEgress(process.env.WONIUNOTE_MOCK_EGRESS_LOG)
}
