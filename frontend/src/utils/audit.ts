/**
 * Audit log event type to human-readable label mapper
 */

export const eventTypeLabels: Record<string, string> = {
  login: 'Successful Login',
  capsule_created: 'Capsule Created',
  capsule_updated: 'Capsule Updated',
  beneficiary_added: 'Beneficiary Added',
  checkin_confirmed: 'Check-in Confirmed',
  checkin_snoozed: 'Check-in Snoozed',
  trigger_created: 'Delivery Trigger Created',
  delivery_sent: 'Capsule Delivered',
  key_accessed: 'Encryption Key Accessed',
}

export const getEventLabel = (eventType: string): string => {
  return eventTypeLabels[eventType] || eventType
}
