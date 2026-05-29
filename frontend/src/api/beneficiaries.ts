import client from './client'

export interface BeneficiaryCreatePayload {
  full_name: string
  email: string
  relationship?: string
  is_emergency_contact?: boolean
}

export const beneficiariesApi = {
  list: () => client.get('/beneficiaries/'),
  create: (data: BeneficiaryCreatePayload) => client.post('/beneficiaries/', data),
  update: (id: string, data: Partial<BeneficiaryCreatePayload>) => client.patch(`/beneficiaries/${id}`, data),
  delete: (id: string) => client.delete(`/beneficiaries/${id}`),
}
