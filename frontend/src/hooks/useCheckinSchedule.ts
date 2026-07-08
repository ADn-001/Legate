import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsApi, CheckinScheduleUpdate } from '../api/settings'

export const useCheckinSchedule = () =>
  useQuery({ queryKey: ['checkin-schedule'], queryFn: () => settingsApi.getCheckinSchedule().then(r => r.data) })

export const useUpdateCheckinSchedule = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CheckinScheduleUpdate) => settingsApi.updateCheckinSchedule(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['checkin-schedule'] }),
  })
}
