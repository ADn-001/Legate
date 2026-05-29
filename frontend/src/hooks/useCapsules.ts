import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { capsulesApi, CapsuleCreatePayload } from '../api/capsules'

export const useCapsules = () =>
  useQuery({ queryKey: ['capsules'], queryFn: () => capsulesApi.list().then(r => r.data) })

export const useCapsule = (id: string) =>
  useQuery({ queryKey: ['capsules', id], queryFn: () => capsulesApi.get(id).then(r => r.data) })

export const useCreateCapsule = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CapsuleCreatePayload) => capsulesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capsules'] }),
  })
}

export const useUpdateCapsule = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => capsulesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capsules'] }),
  })
}

export const useDeleteCapsule = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => capsulesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['capsules'] }),
  })
}
