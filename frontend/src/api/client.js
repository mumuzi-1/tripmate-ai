const API_BASE = '/api/v1'
const TOKEN_KEY = 'tripmate_access_token'

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function saveToken(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('无效的登录令牌')
  }

  sessionStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY)
}

function formatErrorDetail(detail, status) {
  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map(item => {
        if (typeof item === 'string') return item

        const location = Array.isArray(item?.loc)
          ? item.loc.join('.')
          : ''

        return [
          location,
          item?.msg || '参数验证失败',
        ].filter(Boolean).join('：')
      })
      .join('；')
  }

  if (detail && typeof detail === 'object') {
    const messages = []

    if (detail.message) {
      messages.push(detail.message)
    }

    if (detail.agent_status) {
      messages.push(
        `Agent 状态：${detail.agent_status}`
      )
    }

    if (Array.isArray(detail.validation_errors)) {
      for (const item of detail.validation_errors) {
        messages.push(
          typeof item === 'string'
            ? item
            : JSON.stringify(item)
        )
      }
    }

    if (detail.agent_error) {
      messages.push(
        `Agent 错误：${detail.agent_error}`
      )
    }

    if (
      detail.itinerary_days !== undefined &&
      detail.itinerary_days !== null
    ) {
      messages.push(
        `已生成天数：${detail.itinerary_days}`
      )
    }

    if (messages.length > 0) {
      return messages.join('\n')
    }

    return JSON.stringify(detail)
  }

  return `HTTP ${status}：请求失败`
}

export async function apiRequest(
  path,
  {
    method = 'GET',
    body,
    authenticated = true,
    signal,
  } = {},
) {
  const headers = {
    Accept: 'application/json',
  }

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  if (authenticated) {
    const token = getToken()

    if (!token) {
      throw new Error('请先登录 TripMate AI')
    }

    headers.Authorization = `Bearer ${token}`
  }

  let response

  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined
        ? undefined
        : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw error
    }

    throw new Error(
      `无法连接后端服务：${error.message}`
    )
  }

  const contentType =
    response.headers.get('content-type') || ''

  let data = null

  if (contentType.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      throw new Error('服务器返回了无效的 JSON')
    }
  } else {
    data = await response.text()
  }

  if (!response.ok) {
    const detail = (
      data &&
      typeof data === 'object' &&
      'detail' in data
    )
      ? data.detail
      : data

    const message = formatErrorDetail(
      detail,
      response.status,
    )

    const error = new Error(message)
    error.status = response.status
    error.detail = detail

    if (response.status === 401) {
      error.message = '登录已失效或身份验证失败，请重新登录'
    }

    if (response.status === 403) {
      error.message = '没有权限执行此操作'
    }

    throw error
  }

  return data
}

export async function login(
  usernameOrEmail,
  password,
) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    authenticated: false,
    body: {
      username_or_email: usernameOrEmail,
      password,
    },
  })

  if (!data.access_token) {
    throw new Error('登录成功但未返回令牌')
  }

  saveToken(data.access_token)

  return data
}

export function getTrips() {
  return apiRequest('/trips')
}

export function getTripDetail(tripId) {
  return apiRequest(`/trips/${tripId}`)
}

export function getTripRequirements(tripId) {
  return apiRequest(`/trips/${tripId}/requirements`)
}

export function getItineraryVersions(tripId) {
  return apiRequest(`/trips/${tripId}/itineraries`)
}

export function getItineraryDetail(tripId, version) {
  return apiRequest(
    `/trips/${tripId}/itineraries/${version}`
  )
}

export function generateItinerary(tripId) {
  return apiRequest(`/trips/${tripId}/generate`, {
    method: 'POST',
  })
}
