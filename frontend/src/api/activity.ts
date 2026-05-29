import client from './client'

export const activityApi = {
  list: (params?: { page?: number; per_page?: number }) => client.get('/activity/', { params }),
}
