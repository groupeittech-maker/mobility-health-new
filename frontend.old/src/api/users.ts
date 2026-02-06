import client from './client'

export interface UserSummary {
  id: number
  email: string
  username: string
  full_name?: string
  is_active: boolean
  role: string
}

export const usersApi = {
  getByRole: async (role: string): Promise<UserSummary[]> => {
    const response = await client.get('/users', { params: { role } })
    return response.data
  },
}


