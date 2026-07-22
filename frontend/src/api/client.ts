const API_ROOT = '/api'
const DEFAULT_TIMEOUT = 20_000

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

async function request<T>(path: string, init: RequestInit = {}, timeout = DEFAULT_TIMEOUT): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(`${API_ROOT}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { 'content-type': 'application/json', ...init.headers },
    })
    const contentType = response.headers.get('content-type') ?? ''
    const payload = contentType.includes('application/json') ? await response.json() : await response.text()
    if (!response.ok) {
      const detail = typeof payload === 'object' && payload && 'detail' in payload ? String(payload.detail) : `Request failed (${response.status})`
      throw new ApiError(response.status, detail)
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') throw new ApiError(408, 'The local service did not respond in time.')
    throw new ApiError(0, 'The local CareGuard service is unavailable.')
  } finally {
    window.clearTimeout(timer)
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, timeout?: number) => request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }, timeout),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: 'DELETE' }),
}
