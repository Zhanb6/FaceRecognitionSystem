export type UserRole = 'superadmin' | 'admin' | 'user' | 'camera'

export interface AuthUser {
  id: number
  username: string
  email?: string
  is_staff: boolean
  is_camera: boolean
  role?: UserRole
  company?: number | null
  company_name?: string | null
}

export interface AuthResponse {
  message: string
  user: AuthUser
  tokens: {
    access: string
    refresh: string
  }
}

export interface Face {
  id: number
  full_name: string
  role: string
  created_at: string
  allowed_cameras?: number[]
}

export interface RecognitionLog {
  id: number
  camera_account: number
  person_name: string | null
  unknown_face: boolean
  confidence: number
  timestamp: string
}

export interface CameraAcc {
  id: number
  username: string
  is_active: boolean
  date_joined: string
  owner_id?: number | null
  owner__username?: string | null
}

export interface AuditEntry {
  id: number
  username: string
  action: string
  details: string
  timestamp: string
}

export interface CompanyUser {
  id: number
  username: string
  email: string
  role: UserRole
  company: number | null
  company_name?: string
}

export interface CompanyAccount {
  id: number
  name: string
  created_at: string
}

export interface AdminAccount {
  id: number
  username: string
  email: string
  company_name?: string
}
