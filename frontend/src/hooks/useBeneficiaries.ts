import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { beneficiariesApi, BeneficiaryCreatePayload } from '../api/beneficiaries'

export const useBeneficiaries = () =>
  useQuery({ queryKey: ['beneficiaries'], queryFn: () => beneficiariesApi.list().then(r => r.data) })

export const useCreateBeneficiary = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: BeneficiaryCreatePayload) => beneficiariesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beneficiaries'] }),
  })
}

export const useUpdateBeneficiary = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<BeneficiaryCreatePayload> }) =>
      beneficiariesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beneficiaries'] }),
  })
}

export const useDeleteBeneficiary = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => beneficiariesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['beneficiaries'] }),
  })
}
