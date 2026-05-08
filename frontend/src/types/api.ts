/**
 * API Response Types
 * - User, Capsule, Beneficiary, CheckinSchedule, AuditLog, etc.
 */

export interface User {
  id: string
  email: string
  firstName?: string
  lastName?: string
  createdAt: string
  updatedAt: string
}

export interface Capsule {
  id: string
  userId: string
  title: string
  content: string // Encrypted
  beneficiaries: Beneficiary[]
  status: 'draft' | 'active' | 'delivered'
  inactivityPeriodDays: number
  createdAt: string
  updatedAt: string
}

export interface Beneficiary {
  id: string
  userId: string
  firstName: string
  lastName: string
  email: string
  relationship?: string
  isEmergencyContact: boolean
  createdAt: string
  updatedAt: string
}

export interface CheckinSchedule {
  id: string
  userId: string
  checkInIntervalDays: number
  gracePeriodDays: number
  lastCheckinAt?: string
  nextCheckinAt?: string
}

export interface AuditLog {
  id: string
  userId: string
  eventType: string
  metadata?: Record<string, any>
  createdAt: string
}
