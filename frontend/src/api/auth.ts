import client from './client'

interface AuthResponse {
  token: string
  username: string
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/auth/login', { username, password })
  return data
}

export async function register(username: string, password: string): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/auth/register', { username, password })
  return data
}

export async function fetchMe(): Promise<{ username: string }> {
  const { data } = await client.get('/auth/me')
  return data
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await client.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
}
