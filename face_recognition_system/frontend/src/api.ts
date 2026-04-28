const API_BASE = ''

type ApiRequestOptions = RequestInit & {
  auth?: boolean
}

export class ApiError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export const getErrorMessage = (error: unknown, fallback = 'Ошибка запроса') => {
  if (error instanceof ApiError) {
    if (typeof error.payload === 'string') return error.payload
    if (isRecord(error.payload)) {
      const detail = error.payload.detail
      if (typeof detail === 'string') return detail
      if (isRecord(detail)) {
        return Object.values(detail).flat().join(' ') || fallback
      }
      const message = error.payload.message
      if (typeof message === 'string') return message
      const errorText = error.payload.error
      if (typeof errorText === 'string') return errorText
    }
    return error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { auth = false, headers, body, ...rest } = options
  const requestHeaders = new Headers(headers)

  if (body && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }

  if (auth) {
    const token = localStorage.getItem('access')
    if (!token) throw new ApiError('Требуется авторизация', 401, null)
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: requestHeaders,
    body,
  })

  const text = await response.text()
  let payload: unknown = null
  try {
    payload = text ? JSON.parse(text) : null
  } catch {
    payload = text
  }

  if (!response.ok) {
    throw new ApiError(getErrorMessage(new ApiError(response.statusText, response.status, payload)), response.status, payload)
  }

  return payload as T
}

export const toJsonBody = (value: unknown) => JSON.stringify(value)
