import client from './client'

export const usersApi = {
  update: (data: { needs_onboarding?: boolean }) => client.patch('/users/me', data),
  deleteAccount: (data: { confirmation: string; password: string }) =>
    client.delete('/users/me', { data }),
}
