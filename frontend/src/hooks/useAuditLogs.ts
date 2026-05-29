import { useQuery } from '@tanstack/react-query'
import { activityApi } from '../api/activity'

export const useAuditLogs = (page = 1) =>
  useQuery({
    queryKey: ['activity', page],
    queryFn: () => activityApi.list({ page, per_page: 20 }).then(r => r.data),
  })
