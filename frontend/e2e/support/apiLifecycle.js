/** Wait for a mocked API response by its method and pathname. */
export function waitForApiResponse(page, method, pathname) {
  return page.waitForResponse((response) => {
    const request = response.request()
    return request.method() === method && new URL(response.url()).pathname === pathname
  })
}

/** Ensure the response body has completed before a test ends or closes its context. */
export async function completeApiResponse(responsePromise) {
  const response = await responsePromise
  const error = await response.finished()
  if (error) throw error
  if (response.status() !== 200) {
    throw new Error(`Expected successful API response, received ${response.status()} for ${response.url()}`)
  }
  return response
}

export function waitForHomeResponses(page) {
  return [
    waitForApiResponse(page, 'GET', '/api/articles'),
    waitForApiResponse(page, 'GET', '/api/articles/hot')
  ]
}

export function waitForArticleThumbnailResponses(page) {
  return [
    waitForApiResponse(page, 'GET', '/api/thumb/101.png'),
    waitForApiResponse(page, 'GET', '/api/thumb/701.png')
  ]
}
