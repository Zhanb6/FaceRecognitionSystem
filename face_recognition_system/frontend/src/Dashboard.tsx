import React, { useState, useEffect, useCallback } from 'react'
import type { FC, CSSProperties, ReactNode } from 'react'
import { ApiError, apiRequest, getErrorMessage, toJsonBody } from './api'
import type { AdminAccount, AuditEntry, AuthUser, CameraAcc, CompanyUser, Face, RecognitionLog } from './types'

// ── Types ─────────────────────────────────────────────────────────────────────
type NavPage = 'overview' | 'users' | 'recognition' | 'cameras' | 'settings' | 'history'

interface DashboardProps {
  username?: string
  user: AuthUser | null
  onLogout: () => void
}

// ── Styles ─────────────────────────────────────────────────────────────────────
const S: Record<string, CSSProperties> = {
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
    background: 'var(--dash-bg)',
    color: 'var(--dash-text)',
  },
  // ── Top bar
  topbar: {
    height: 58,
    background: 'var(--dash-surface)',
    borderBottom: '1px solid var(--dash-border)',
    display: 'flex',
    alignItems: 'center',
    padding: '0 28px',
    gap: 14,
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 100,
  },
  topbarStripe: {
    height: 3,
    background: 'linear-gradient(90deg, #0a1f6b 0%, #1a3fd4 45%, #00aaff 75%, #00d4ff 100%)',
  },
  topbarBadge: {
    width: 36, height: 36, borderRadius: '50%',
    background: 'linear-gradient(135deg, #0a1f6b, #1a3fd4)',
    color: '#fff', display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: 10, fontWeight: 700,
    flexShrink: 0, letterSpacing: '-0.3px',
    boxShadow: '0 2px 8px rgba(26,63,212,0.35)',
  },
  topbarTitle: { fontSize: 14, fontWeight: 700, color: 'var(--dash-heading)', flex: 1 },
  topbarUser: {
    display: 'flex', alignItems: 'center', gap: 10,
    fontSize: 13, color: 'var(--dash-muted)',
  },
  userAvatar: {
    width: 32, height: 32, borderRadius: '50%',
    background: 'linear-gradient(135deg, #667eea, #764ba2)',
    color: '#fff', display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontSize: 13, fontWeight: 600,
  },
  logoutBtn: {
    background: 'none', border: '1px solid #e2e8f0',
    borderRadius: 7, padding: '5px 12px',
    fontSize: 12, color: 'var(--dash-muted)', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    transition: 'all 0.18s',
  },
  // ── Layout
  body: { display: 'flex', flex: 1, overflow: 'hidden' },
  // ── Sidebar
  sidebar: {
    width: 220, flexShrink: 0,
    background: 'var(--dash-surface)',
    borderRight: '1px solid var(--dash-border)',
    padding: '20px 0',
    display: 'flex', flexDirection: 'column',
    overflowY: 'auto' as const,
  },
  sidebarSection: {
    fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
    color: '#94a3b8', padding: '16px 20px 6px',
    textTransform: 'uppercase' as const,
  },
  // ── Main area
  main: { flex: 1, padding: 28, overflowY: 'auto' as const, background: 'var(--dash-bg)' },
  pageTitle: { fontSize: 22, fontWeight: 700, color: 'var(--dash-heading)', marginBottom: 6 },
  pageSubtitle: { fontSize: 13, color: 'var(--dash-muted)', marginBottom: 24 },
  // ── Stat cards
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
    gap: 18, marginBottom: 28,
  },
  statCard: {
    background: 'var(--dash-surface)', borderRadius: 14,
    padding: '20px 22px',
    boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
    display: 'flex', flexDirection: 'column' as const, gap: 6,
  },
  statIcon: { fontSize: 26, marginBottom: 4 },
  statValue: { fontSize: 28, fontWeight: 700, color: 'var(--dash-heading)', lineHeight: 1 },
  statLabel: { fontSize: 12, color: 'var(--dash-muted)', fontWeight: 500 },
  statDelta: { fontSize: 11, color: '#94a3b8', marginTop: 2 },
  // ── Card / Table
  card: {
    background: 'var(--dash-surface)', borderRadius: 14,
    boxShadow: '0 1px 6px rgba(0,0,0,0.06)',
    overflow: 'hidden',
    marginBottom: 24,
  },
  cardHeader: {
    padding: '16px 22px', borderBottom: '1px solid var(--dash-border-soft)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  cardTitle: { fontSize: 15, fontWeight: 600, color: 'var(--dash-heading)' },
  table: { width: '100%', borderCollapse: 'collapse' as const },
  th: {
    padding: '11px 18px', textAlign: 'left' as const,
    fontSize: 11, fontWeight: 600, color: '#94a3b8',
    textTransform: 'uppercase' as const, letterSpacing: '0.06em',
    background: 'var(--dash-table-head)', borderBottom: '1px solid var(--dash-border-soft)',
  },
  td: {
    padding: '12px 18px', fontSize: 13, color: 'var(--dash-text)',
    borderBottom: '1px solid var(--dash-border-soft)',
  },
  // ── Badges
  badgeSuccess: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    background: '#dcfce7', color: '#16a34a',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  badgeFailed: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    background: '#fee2e2', color: '#dc2626',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  badgeActive: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    background: '#dbeafe', color: '#1d4ed8',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  badgeInactive: {
    display: 'inline-flex', alignItems: 'center', gap: 4,
    background: '#f1f5f9', color: '#94a3b8',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  badgeOnline: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    background: '#dcfce7', color: '#16a34a',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  badgeOffline: {
    display: 'inline-flex', alignItems: 'center', gap: 5,
    background: '#fee2e2', color: '#dc2626',
    borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600,
  },
  dot: {
    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
  },
  // ── Mini button
  miniBtn: {
    background: 'var(--dash-control-bg)', border: '1px solid var(--dash-border)',
    borderRadius: 6, padding: '4px 10px',
    fontSize: 12, color: 'var(--dash-text)', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
  },
  primaryMiniBtn: {
    border: 'none',
    borderRadius: 6, padding: '5px 12px',
    fontSize: 12, color: '#fff', cursor: 'pointer',
    fontFamily: "'Inter', sans-serif",
    background: 'linear-gradient(135deg, #0a1f6b, #1a3fd4)',
    fontWeight: 600,
  },
  // ── Activity bar
  activityBar: {
    display: 'flex', gap: 3, alignItems: 'flex-end',
    height: 40,
  },
  // ── Settings form
  settingRow: {
    padding: '16px 22px', borderBottom: '1px solid var(--dash-border-soft)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  settingLabel: { fontSize: 14, color: 'var(--dash-text)', fontWeight: 500 },
  settingDesc: { fontSize: 12, color: 'var(--dash-muted-soft)', marginTop: 2 },
  toggle: {
    width: 42, height: 24, borderRadius: 12,
    cursor: 'pointer', position: 'relative' as const,
    border: 'none', transition: 'background 0.2s',
  },
  toggleThumb: {
    width: 18, height: 18, borderRadius: '50%',
    background: '#fff',
    position: 'absolute' as const,
    top: 3,
    boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
    transition: 'left 0.2s',
  },
  settingInput: {
    border: '1.5px solid var(--dash-border)', borderRadius: 8,
    padding: '7px 12px', fontSize: 13, color: 'var(--dash-heading)', background: 'var(--dash-input-bg)',
    fontFamily: "'Inter', sans-serif", outline: 'none', width: 200,
  },
  grid2: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18,
  },
  // ── Modals
  modalOverlay: {
    position: 'fixed' as const, top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(15, 23, 42, 0.65)', backdropFilter: 'blur(4px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000, animation: 'modalOverlay 0.25s ease',
  },
  modal: {
    background: 'var(--dash-surface)', borderRadius: 16, width: '90%',
    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)',
    animation: 'modalBox 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
    position: 'relative' as const, overflow: 'hidden',
  },
  modalHeader: {
    padding: '18px 28px', borderBottom: '1px solid var(--dash-border-soft)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    background: 'var(--dash-table-head)',
  },
  closeBtn: {
    background: 'var(--dash-control-bg)', border: 'none', width: 28, height: 28,
    borderRadius: '50%', cursor: 'pointer', display: 'flex',
    alignItems: 'center', justifyContent: 'center', fontSize: 20,
    color: '#64748b', transition: 'all 0.2s',
  },
  primaryBtn: {
    background: 'linear-gradient(135deg, #0a1f6b, #1a3fd4)',
    color: '#fff', border: 'none', borderRadius: 10,
    padding: '12px 24px', fontSize: 14, fontWeight: 600,
    cursor: 'pointer', transition: 'all 0.2s',
    fontFamily: "'Inter', sans-serif",
  },
}

// ── Nav item ───────────────────────────────────────────────────────────────────
const NavItem: FC<{ icon: ReactNode; label: string; active: boolean; onClick: () => void }> = ({
  icon, label, active, onClick,
}) => (
  <button
    onClick={onClick}
    style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '10px 18px 10px 20px',
      background: active ? 'rgba(26,63,212,0.07)' : 'none',
      border: 'none',
      borderRight: active ? '3px solid #1a3fd4' : '3px solid transparent',
      width: '100%', textAlign: 'left',
      cursor: 'pointer',
      fontSize: 13,
      fontWeight: active ? 600 : 400,
      color: active ? '#1a3fd4' : '#475569',
      fontFamily: "'Inter', sans-serif",
      transition: 'all 0.18s',
      marginRight: -1,
    }}
  >
    <span style={{ fontSize: 16, width: 20, textAlign: 'center' }}>{icon}</span>
    {label}
  </button>
)

// ── Toggle component ───────────────────────────────────────────────────────────
const Toggle: FC<{ on: boolean; onChange: () => void }> = ({ on, onChange }) => (
  <button
    onClick={onChange}
    style={{ ...S.toggle, background: on ? '#1a3fd4' : '#cbd5e1' }}
  >
    <div style={{ ...S.toggleThumb, left: on ? 21 : 3 }} />
  </button>
)

const lightThemeVars = {
  '--dash-bg': '#f0f4fa',
  '--dash-surface': '#ffffff',
  '--dash-heading': '#0d1b4b',
  '--dash-text': '#334155',
  '--dash-muted': '#64748b',
  '--dash-muted-soft': '#94a3b8',
  '--dash-border': '#e2e8f0',
  '--dash-border-soft': '#f1f5f9',
  '--dash-table-head': '#f8fafc',
  '--dash-control-bg': '#ffffff',
  '--dash-input-bg': '#ffffff',
} as CSSProperties

const darkThemeVars = {
  '--dash-bg': '#0f172a',
  '--dash-surface': '#111827',
  '--dash-heading': '#f8fafc',
  '--dash-text': '#dbe4ef',
  '--dash-muted': '#a5b4c8',
  '--dash-muted-soft': '#7f8ea3',
  '--dash-border': '#334155',
  '--dash-border-soft': '#263244',
  '--dash-table-head': '#162033',
  '--dash-control-bg': '#1f2937',
  '--dash-input-bg': '#0b1220',
} as CSSProperties

// ── Dashboard ─────────────────────────────────────────────────────────────────
const Dashboard: FC<DashboardProps> = ({ username = 'Admin', user, onLogout }) => {
  const [page, setPage] = useState<NavPage>('overview')
  const [settings, setSettings] = useState(() => ({
    liveDetect: true, alerts: true, saveLog: true, twoFactor: false,
    threshold: '85',
    darkMode: localStorage.getItem('dashboard_dark_mode') === 'true',
  }))
  const [searchUser, setSearchUser] = useState('')
  const [recognitionFilter, setRecognitionFilter] = useState<'all' | 'known' | 'unknown'>('all')

  const initial = username.charAt(0).toUpperCase()
  const role = user?.role
  const isSuperAdmin = role === 'superadmin' || user?.username === 'developer'
  const isCompanyAdmin = role === 'admin'
  const canManageCameras = isSuperAdmin || isCompanyAdmin
  const canManageFaces = isSuperAdmin || isCompanyAdmin || user?.is_camera
  const canViewHistory = isSuperAdmin
  const canViewCompanyUsers = isSuperAdmin || isCompanyAdmin

  const [faces, setFaces] = useState<Face[]>([])
  const [logs, setLogs] = useState<RecognitionLog[]>([])
  const [cameras, setCameras] = useState<CameraAcc[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([])
  const [companyUsers, setCompanyUsers] = useState<CompanyUser[]>([])
  const [adminAccounts, setAdminAccounts] = useState<AdminAccount[]>([])

  const [showAddModal, setShowAddModal] = useState(false)
  const [newFaceName, setNewFaceName] = useState('')
  const [newFaceRole, setNewFaceRole] = useState('Студент')
  const [customRole, setCustomRole] = useState('')
  const [selectedCameras, setSelectedCameras] = useState<number[]>([])
  const [addingFace, setAddingFace] = useState(false)

  // Multi-expanded row state for 'Camera Faces'
  const [expandedCameraIds, setExpandedCameraIds] = useState<number[]>([])
  const [expandedAdminIds, setExpandedAdminIds] = useState<number[]>([])
  const [cameraFacesMap, setCameraFacesMap] = useState<Record<number, Face[]>>({})
  const [cameraLoadingMap, setCameraLoadingMap] = useState<Record<number, boolean>>({})

  // Create Camera state
  const [showAddCamModal, setShowAddCamModal] = useState(false)
  const [newCamUser, setNewCamUser] = useState('')
  const [newCamPass, setNewCamPass] = useState('')
  const [creatingCam, setCreatingCam] = useState(false)

  const [showRequestModal, setShowRequestModal] = useState(false)
  const [requestLogin, setRequestLogin] = useState('')
  const [requestPassword, setRequestPassword] = useState('')
  const [creatingRequest, setCreatingRequest] = useState(false)
  const [requestError, setRequestError] = useState('')
  const [adminSearch, setAdminSearch] = useState('')
  const [adminCameraFilter, setAdminCameraFilter] = useState<'all' | 'with' | 'without'>('all')
  const [dashboardError, setDashboardError] = useState('')

  // Hover state for face cards
  const [hoveredCardKey, setHoveredCardKey] = useState<string | null>(null)

  // Modal for Adding Existing Face to Camera
  const [addExistingFaceModal, setAddExistingFaceModal] = useState<CameraAcc | null>(null)
  const [selectedFaceToAdd, setSelectedFaceToAdd] = useState<string>('')
  const [addingExistingFace, setAddingExistingFace] = useState(false)

  // Modal for Editing Face
  const [editFaceModal, setEditFaceModal] = useState<Face | null>(null)
  const [editName, setEditName] = useState('')
  const [editRole, setEditRole] = useState('')
  const [editCams, setEditCams] = useState<number[]>([])
  const [updatingFace, setUpdatingFace] = useState(false)

  const loadOptionalDashboardSection = useCallback(async <T,>(
    request: Promise<T>,
    apply: (data: T) => void,
    sectionName: string,
    signal?: AbortSignal,
  ) => {
    try {
      const data = await request
      if (!signal?.aborted) apply(data)
    } catch (error) {
      if (signal?.aborted) return
      console.error(`Error fetching ${sectionName}:`, error)
      if (error instanceof ApiError && error.status === 401) {
        onLogout()
        return
      }
      setDashboardError(prev => prev || getErrorMessage(error, `Не удалось загрузить ${sectionName}`))
    }
  }, [onLogout])

  const fetchDashboardData = useCallback(async (signal?: AbortSignal) => {
    try {
      setDashboardError('')
      const [facesData, logsData, camerasData] = await Promise.all([
        apiRequest<Face[]>('/api/auth/faces/all_faces/', { auth: true, signal }),
        apiRequest<RecognitionLog[]>('/api/auth/logs/all_logs/', { auth: true, signal }),
        apiRequest<CameraAcc[]>('/api/auth/cameras/', { auth: true, signal }),
      ])

      if (signal?.aborted) return

      setFaces(facesData)
      setLogs(logsData)
      setCameras(camerasData)

      const optionalRequests: Promise<void>[] = []

      if (canViewHistory) {
        optionalRequests.push(loadOptionalDashboardSection(
          apiRequest<AuditEntry[]>('/api/auth/audit-logs/', { auth: true, signal }),
          setAuditLogs,
          'историю действий',
          signal,
        ))
      }

      if (canViewCompanyUsers) {
        optionalRequests.push(loadOptionalDashboardSection(
          apiRequest<CompanyUser[]>('/api/auth/users/', { auth: true, signal }),
          setCompanyUsers,
          'пользователей компании',
          signal,
        ))
      }

      if (isSuperAdmin) {
        optionalRequests.push(loadOptionalDashboardSection(
          apiRequest<AdminAccount[]>('/api/auth/admin-users/', { auth: true, signal }),
          setAdminAccounts,
          'список администраторов',
          signal,
        ))
      }

      await Promise.all(optionalRequests)
    } catch (error) {
      if (signal?.aborted) return
      console.error('Error fetching dashboard data:', error)
      if (error instanceof ApiError && error.status === 401) {
        onLogout()
        return
      }
      setDashboardError(getErrorMessage(error, 'Не удалось загрузить данные панели'))
    }
  }, [canViewCompanyUsers, canViewHistory, isSuperAdmin, loadOptionalDashboardSection, onLogout])

  useEffect(() => {
    const controller = new AbortController()
    fetchDashboardData(controller.signal)
    return () => controller.abort()
  }, [fetchDashboardData])

  useEffect(() => {
    localStorage.setItem('dashboard_dark_mode', String(settings.darkMode))
    document.body.style.background = settings.darkMode ? '#0f172a' : '#f0f4fa'
  }, [settings.darkMode])

  const handleAddFace = async () => {
    if (!canManageFaces) return
    if (!newFaceName) return
    const finalRole = newFaceRole === 'Другое...' ? customRole.trim() : newFaceRole
    if (!finalRole) return

    setAddingFace(true)
    const finalCameras = selectedCameras.length > 0 ? selectedCameras : (cameras.length > 0 ? [cameras[0].id] : [])

    try {
      setDashboardError('')
      await apiRequest<Face>('/api/auth/faces/', {
        method: 'POST',
        auth: true,
        body: toJsonBody({
          full_name: newFaceName,
          role: finalRole,
          allowed_cameras: finalCameras
        })
      })
      setShowAddModal(false)
      setNewFaceName('')
      setNewFaceRole(finalRole)
      setCustomRole('')
      setSelectedCameras([])
      fetchDashboardData()
    } catch (error) {
      console.error("Error adding face", error)
      setDashboardError(getErrorMessage(error, 'Не удалось добавить пользователя'))
    } finally {
      setAddingFace(false)
    }
  }

  const handleCreateCamera = async () => {
    if (!canManageCameras) return
    if (!newCamUser || !newCamPass) return
    setCreatingCam(true)
    try {
      setDashboardError('')
      await apiRequest('/api/auth/cameras/create/', {
        method: 'POST',
        auth: true,
        body: toJsonBody({
          username: newCamUser,
          password: newCamPass
        })
      })
      setShowAddCamModal(false)
      setNewCamUser('')
      setNewCamPass('')
      fetchDashboardData()
    } catch (error) {
      console.error('Error creating camera:', error)
      setDashboardError(getErrorMessage(error, 'Ошибка при создании камеры'))
    } finally {
      setCreatingCam(false)
    }
  }
  const handleDeleteFace = async (id: number) => {
    if (!canManageFaces) return
    if (!confirm('Вы уверены, что хотите удалить этого пользователя?')) return
    try {
      setDashboardError('')
      await apiRequest<null>(`/api/auth/faces/${id}/`, {
        method: 'DELETE',
        auth: true,
      })
      setFaces(faces.filter(f => f.id !== id))
      fetchDashboardData()
    } catch (error) {
      console.error("Error deleting face", error)
      setDashboardError(getErrorMessage(error, 'Не удалось удалить пользователя'))
    }
  }

  const handleUpdateFace = async () => {
    if (!canManageFaces) return
    if (!editFaceModal) return
    setUpdatingFace(true)
    try {
      setDashboardError('')
      await apiRequest<Face>(`/api/auth/faces/${editFaceModal.id}/`, {
        method: 'PATCH',
        auth: true,
        body: toJsonBody({
          full_name: editName,
          role: editRole,
          allowed_cameras: editCams
        })
      })
      setEditFaceModal(null)
      fetchDashboardData()
    } catch (error) {
      console.error("Error updating face", error)
      setDashboardError(getErrorMessage(error, 'Не удалось обновить пользователя'))
    } finally {
      setUpdatingFace(false)
    }
  }

  const handleRemoveFaceFromCamera = async (camId: number, faceId: number) => {
    if (!canManageCameras) return
    if (!confirm('Вы уверены, что хотите убрать доступ для этого пользователя?')) return
    try {
      setDashboardError('')
      await apiRequest(`/api/auth/cameras/${camId}/remove_face/`, {
        method: 'POST',
        auth: true,
        body: toJsonBody({ face_id: faceId })
      })
      const data = await apiRequest<Face[]>(`/api/auth/cameras/${camId}/faces/`, { auth: true })
      setCameraFacesMap(prev => ({ ...prev, [camId]: data }))
      fetchDashboardData()
    } catch (error) {
      console.error("Error removing face from camera", error)
      setDashboardError(getErrorMessage(error, 'Не удалось убрать пользователя из камеры'))
    }
  }

  const handleToggleCameraFaces = async (cam: CameraAcc) => {
    const isExpanded = expandedCameraIds.includes(cam.id)
    if (isExpanded) {
      setExpandedCameraIds(prev => prev.filter(id => id !== cam.id))
      return
    }

    setExpandedCameraIds(prev => [...prev, cam.id])
    setCameraLoadingMap(prev => ({ ...prev, [cam.id]: true }))
    try {
      setDashboardError('')
      const data = await apiRequest<Face[]>(`/api/auth/cameras/${cam.id}/faces/`, { auth: true })
      setCameraFacesMap(prev => ({ ...prev, [cam.id]: data }))
    } catch (error) {
      console.error('Error fetching camera faces', error)
      setDashboardError(getErrorMessage(error, 'Не удалось загрузить пользователей камеры'))
    } finally {
      setCameraLoadingMap(prev => ({ ...prev, [cam.id]: false }))
    }
  }

  const handleAddExistingFace = async () => {
    if (!canManageCameras) return
    if (!addExistingFaceModal || !selectedFaceToAdd) return
    setAddingExistingFace(true)
    try {
      setDashboardError('')
      await apiRequest(`/api/auth/cameras/${addExistingFaceModal.id}/add_face/`, {
        method: 'POST',
        auth: true,
        body: toJsonBody({ face_id: parseInt(selectedFaceToAdd) })
      })
      if (expandedCameraIds.includes(addExistingFaceModal.id)) {
        const data = await apiRequest<Face[]>(`/api/auth/cameras/${addExistingFaceModal.id}/faces/`, { auth: true })
        setCameraFacesMap(prev => ({ ...prev, [addExistingFaceModal.id]: data }))
      }
      setAddExistingFaceModal(null)
      setSelectedFaceToAdd('')
      fetchDashboardData()
    } catch (error) {
      console.error('Error adding existing face', error)
      setDashboardError(getErrorMessage(error, 'Не удалось добавить пользователя в камеру'))
    } finally {
      setAddingExistingFace(false)
    }
  }

  const filteredFaces = faces.filter(f =>
    f.full_name.toLowerCase().includes(searchUser.toLowerCase()) ||
    f.role.toLowerCase().includes(searchUser.toLowerCase())
  )

  const filteredLogs = logs.filter(log => {
    if (recognitionFilter === 'known') return !log.unknown_face
    if (recognitionFilter === 'unknown') return log.unknown_face
    return true
  })

  const handleCycleRecognitionFilter = () => {
    setRecognitionFilter(current => {
      if (current === 'all') return 'known'
      if (current === 'known') return 'unknown'
      return 'all'
    })
  }

  const handleExportLogsCsv = () => {
    const header = ['id', 'person_name', 'timestamp', 'confidence', 'status']
    const rows = filteredLogs.map(log => [
      log.id,
      log.person_name || 'Неизвестный',
      log.timestamp,
      log.confidence.toFixed(1),
      log.unknown_face ? 'unknown' : 'success',
    ])
    const escapeCell = (value: string | number) => `"${String(value).replaceAll('"', '""')}"`
    const csv = [header, ...rows].map(row => row.map(escapeCell).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `recognition-logs-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const now = new Date()
  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)
  const tomorrowStart = new Date(todayStart)
  tomorrowStart.setDate(tomorrowStart.getDate() + 1)
  const yesterdayStart = new Date(todayStart)
  yesterdayStart.setDate(yesterdayStart.getDate() - 1)
  const sevenDaysAgo = new Date(now)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

  const todayLogs = logs.filter(log => {
    const timestamp = new Date(log.timestamp)
    return timestamp >= todayStart && timestamp < tomorrowStart
  })
  const yesterdayLogsCount = logs.filter(log => {
    const timestamp = new Date(log.timestamp)
    return timestamp >= yesterdayStart && timestamp < todayStart
  }).length
  const recentLogs = logs.filter(log => new Date(log.timestamp) >= sevenDaysAgo)
  const successfulRecentLogs = recentLogs.filter(log => !log.unknown_face).length
  const accuracyValue = recentLogs.length > 0 ? (successfulRecentLogs / recentLogs.length) * 100 : 0
  const activeCamerasCount = cameras.filter(camera => camera.is_active).length
  const offlineCamerasCount = Math.max(cameras.length - activeCamerasCount, 0)
  const recognitionDelta = yesterdayLogsCount > 0
    ? `${todayLogs.length >= yesterdayLogsCount ? '+' : ''}${Math.round(((todayLogs.length - yesterdayLogsCount) / yesterdayLogsCount) * 100)}% к вчера`
    : `${yesterdayLogsCount} вчера`

  const overviewStats = [
    { label: 'Всего пользователей', value: String(faces.length), delta: 'Профили в базе', icon: '👤', color: '#1a3fd4' },
    { label: 'Распознаваний сегодня', value: String(todayLogs.length), delta: recognitionDelta, icon: '🔍', color: '#0ea5e9' },
    { label: 'Точность системы', value: `${accuracyValue.toFixed(1)}%`, delta: 'Последние 7 дней', icon: '🎯', color: '#10b981' },
    { label: 'Активных камер', value: `${activeCamerasCount} / ${cameras.length}`, icon: '📷', delta: `${offlineCamerasCount} офлайн`, color: '#f59e0b' },
  ]

  const hourlyActivity = Array.from({ length: 12 }, (_, index) => {
    const hourStart = new Date(now)
    hourStart.setMinutes(0, 0, 0)
    hourStart.setHours(hourStart.getHours() - (11 - index))
    const hourEnd = new Date(hourStart)
    hourEnd.setHours(hourEnd.getHours() + 1)
    return {
      label: String(hourStart.getHours()),
      count: logs.filter(log => {
        const timestamp = new Date(log.timestamp)
        return timestamp >= hourStart && timestamp < hourEnd
      }).length,
    }
  })
  const maxHourlyActivity = Math.max(...hourlyActivity.map(item => item.count), 1)

  const filteredAdminAccounts = adminAccounts
    .filter(a => {
      const term = adminSearch.trim().toLowerCase()
      if (!term) return true
      const uname = (a.username || '').toLowerCase()
      const cname = (a.company_name || '').toLowerCase()
      return uname.includes(term) || cname.includes(term)
    })
    .filter(a => {
      if (adminCameraFilter === 'all') return true
      const count = cameras.filter(c => c.owner_id === a.id).length
      return adminCameraFilter === 'with' ? count > 0 : count === 0
    })

  const handleCreateRequest = async () => {
    if (!isSuperAdmin) return
    if (!requestLogin || !requestPassword) return

    setCreatingRequest(true)
    setRequestError('')
    try {
      await apiRequest('/api/auth/admin-users/', {
        method: 'POST',
        auth: true,
        body: toJsonBody({
          username: requestLogin,
          password: requestPassword,
        })
      })

      setRequestLogin('')
      setRequestPassword('')
      setShowRequestModal(false)
      fetchDashboardData()
    } catch (error) {
      console.error('Error creating admin request:', error)
      setRequestError(getErrorMessage(error, 'Ошибка соединения с сервером'))
    } finally {
      setCreatingRequest(false)
    }
  }

  const toggleSetting = (key: keyof typeof settings) =>
    setSettings(s => ({ ...s, [key]: !s[key] }))

  // ── Render pages ─────────────────────────────────────────────────────────────
  const renderPage = () => {
    switch (page) {

      // ─── OVERVIEW ────────────────────────────────────────────────────────────
      case 'overview': return (
        <div style={{ animation: 'dashFade 0.3s ease' }}>
          <div style={S.statsGrid}>
            {overviewStats.map(st => (
              <div key={st.label} style={S.statCard}>
                <div style={S.statIcon}>{st.icon}</div>
                <div style={{ ...S.statValue, color: st.color }}>{st.value}</div>
                <div style={S.statLabel}>{st.label}</div>
                <div style={S.statDelta}>{st.delta}</div>
              </div>
            ))}
            {canViewCompanyUsers && (
              <div style={S.statCard}>
                <div style={S.statIcon}>🏢</div>
                <div style={{ ...S.statValue, color: '#0d9488' }}>{companyUsers.length}</div>
                <div style={S.statLabel}>Аккаунтов компании</div>
                <div style={S.statDelta}>Админы и пользователи</div>
              </div>
            )}
          </div>

          <div style={S.grid2}>
            {/* Recent recognitions */}
            <div style={S.card}>
              <div style={S.cardHeader}>
                <span style={S.cardTitle}>Последние распознавания</span>
                <button style={S.miniBtn} onClick={() => setPage('recognition')}>Все →</button>
              </div>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>Имя</th>
                    <th style={S.th}>Время</th>
                    <th style={S.th}>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(0, 5).map(l => (
                    <tr key={l.id}>
                      <td style={S.td}>{l.person_name || 'Неизвестный'}</td>
                      <td style={{ ...S.td, color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                        {new Date(l.timestamp).toLocaleTimeString()}
                      </td>
                      <td style={S.td}>
                        {!l.unknown_face
                          ? <span style={S.badgeSuccess}>✓ Успех</span>
                          : <span style={S.badgeFailed}>✗ Отказ</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Activity chart */}
            <div style={S.card}>
              <div style={S.cardHeader}>
                <span style={S.cardTitle}>Активность за 12 часов</span>
                <span style={{ fontSize: 12, color: '#94a3b8' }}>распознаваний/час</span>
              </div>
              <div style={{ padding: '24px 22px 16px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 6, height: 120 }}>
                  {hourlyActivity.map((item, i) => (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                      <div style={{
                        width: '100%',
                        height: item.count > 0 ? `${Math.max((item.count / maxHourlyActivity) * 100, 4)}%` : 0,
                        background: i === hourlyActivity.length - 1
                          ? 'linear-gradient(180deg, #1a3fd4, #0a1f6b)'
                          : 'linear-gradient(180deg, #93c5fd, #dbeafe)',
                        borderRadius: 4,
                        transition: 'height 0.5s',
                      }} />
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                  {hourlyActivity.map((item, i) => (
                    <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: 10, color: '#94a3b8' }}>{item.label}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Camera status quick view */}
          <div style={S.card}>
            <div style={S.cardHeader}>
              <span style={S.cardTitle}>Статус камер</span>
              <button style={S.miniBtn} onClick={() => setPage('cameras')}>Управление →</button>
            </div>
            <div style={{ padding: '14px 22px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
              {cameras.map(c => (
                <div key={c.id} style={{
                  border: '1px solid #f1f5f9', borderRadius: 10, padding: '12px 14px',
                  display: 'flex', flexDirection: 'column', gap: 4,
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#334155' }}>{c.username}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>ID: {c.id}</div>
                  <div style={{ marginTop: 4 }}>
                    {c.is_active
                      ? <span style={S.badgeOnline}><div style={{ ...S.dot, background: '#16a34a' }} />Активна</span>
                      : <span style={S.badgeOffline}><div style={{ ...S.dot, background: '#dc2626' }} />Отключена</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )

      // ─── USERS ───────────────────────────────────────────────────────────────
      case 'users': return (
        <div style={{ animation: 'dashFade 0.3s ease' }}>
          <div style={S.card}>
            <div style={S.cardHeader}>
              <span style={S.cardTitle}>Пользователи системы ({faces.length})</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  placeholder="Поиск..."

                  value={searchUser}
                  onChange={e => setSearchUser(e.target.value)}
                  style={{ ...S.settingInput, width: 180, fontSize: 12, border: '1px solid #e2e8f0' }}
                />
                {isSuperAdmin && <button style={S.primaryMiniBtn} onClick={() => setShowRequestModal(true)}>Создать компанию</button>}
                {canManageFaces && <button style={S.primaryMiniBtn} onClick={() => setShowAddModal(true)}>+ Добавить пользователя</button>}
              </div>
            </div>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>Имя (ФИО)</th>
                  <th style={S.th}>Роль</th>
                  <th style={S.th}>Дата регистрации</th>
                  <th style={S.th}>Группы (Камеры)</th>
                  <th style={S.th}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {filteredFaces.map(f => (
                  <tr key={f.id} style={{ transition: 'background 0.15s' }}>
                    <td style={S.td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                        <div style={{
                          width: 30, height: 30, borderRadius: '50%',
                          background: 'linear-gradient(135deg, #667eea, #764ba2)',
                          color: '#fff', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', fontSize: 12, fontWeight: 600, flexShrink: 0,
                        }}>
                          {f.full_name.charAt(0)}
                        </div>
                        <span style={{ fontWeight: 500 }}>{f.full_name}</span>
                      </div>
                    </td>
                    <td style={S.td}>
                      <span style={f.role.includes('Админ') ? S.badgeActive : S.badgeInactive}>
                        {f.role}
                      </span>
                    </td>
                    <td style={{ ...S.td, color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                      {new Date(f.created_at).toLocaleDateString()}
                    </td>
                    <td style={S.td}>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {f.allowed_cameras && f.allowed_cameras.length > 0 ? (
                          f.allowed_cameras.map(camId => {
                            const cam = cameras.find(c => c.id === camId)
                            return (
                              <span key={camId} style={{ background: '#f1f5f9', color: '#475569', fontSize: 11, padding: '2px 6px', borderRadius: 4, whiteSpace: 'nowrap' }}>
                                {cam ? cam.username : `Cam: ${camId}`}
                              </span>
                            )
                          })
                        ) : (
                          <span style={{ fontSize: 11, color: '#94a3b8' }}>Нет доступа</span>
                        )}
                      </div>
                    </td>
                    <td style={S.td}>
                      {canManageFaces ? (
                        <div style={{ display: 'flex', gap: 6 }}>
                          <button
                            disabled
                            title="Face ID enrollment is not implemented in the backend"
                            style={{ ...S.miniBtn, background: '#f1f5f9', color: '#94a3b8', border: 'none', cursor: 'not-allowed', fontWeight: 500 }}
                          >
                            + Face ID
                          </button>
                          <button
                            style={S.miniBtn}
                            onClick={() => {
                              setEditFaceModal(f)
                              setEditName(f.full_name)
                              setEditRole(f.role)
                              setEditCams(f.allowed_cameras || [])
                            }}
                          >
                            Настройки
                          </button>
                          <button
                            onClick={() => handleDeleteFace(f.id)}
                            style={{ ...S.miniBtn, color: '#ef4444', borderColor: '#fecaca' }}
                          >
                            Удалить
                          </button>
                        </div>
                      ) : (
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>Только просмотр</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )

      // ─── RECOGNITION LOG ─────────────────────────────────────────────────────
      case 'recognition': return (
        <div style={{ animation: 'dashFade 0.3s ease' }}>
          <div style={S.card}>
            <div style={S.cardHeader}>
              <span style={S.cardTitle}>Лог распознаваний</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button style={S.miniBtn} onClick={handleExportLogsCsv} disabled={filteredLogs.length === 0}>Экспорт CSV</button>
                <button style={S.miniBtn} onClick={handleCycleRecognitionFilter}>
                  {recognitionFilter === 'all' ? 'Все записи' : recognitionFilter === 'known' ? 'Только успешные' : 'Только отказы'}
                </button>
              </div>
            </div>
            <table style={S.table}>
              <thead>
                <tr>
                  <th style={S.th}>#</th>
                  <th style={S.th}>Имя</th>
                  <th style={S.th}>Время</th>
                  <th style={S.th}>Камера</th>
                  <th style={S.th}>Уверенность</th>
                  <th style={S.th}>Статус</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map(l => (
                  <tr key={l.id}>
                    <td style={{ ...S.td, color: '#94a3b8' }}>{l.id}</td>
                    <td style={{ ...S.td, fontWeight: 500 }}>{l.person_name || 'Неизвестный'}</td>
                    <td style={{ ...S.td, color: '#94a3b8', fontVariantNumeric: 'tabular-nums' }}>
                      {new Date(l.timestamp).toLocaleString()}
                    </td>
                    <td style={{ ...S.td, color: '#64748b' }}>Текущая камера</td>
                    <td style={S.td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          height: 6, width: 80, borderRadius: 3,
                          background: '#f1f5f9', overflow: 'hidden',
                        }}>
                          <div style={{
                            height: '100%',
                            width: `${l.confidence}%`,
                            background: l.confidence > 80
                              ? 'linear-gradient(90deg, #10b981, #34d399)'
                              : 'linear-gradient(90deg, #ef4444, #f87171)',
                            borderRadius: 3,
                          }} />
                        </div>
                        <span style={{ fontSize: 12, fontVariantNumeric: 'tabular-nums' }}>{l.confidence.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td style={S.td}>
                      {!l.unknown_face
                        ? <span style={S.badgeSuccess}>✓ Успех</span>
                        : <span style={S.badgeFailed}>✗ Отказ</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )

      // ─── CAMERAS ─────────────────────────────────────────────────────────────
      case 'cameras': return (
        <div style={{ animation: 'dashFade 0.3s ease' }}>
          <div style={S.card}>
            <div style={S.cardHeader}>
              <span style={S.cardTitle}>{isSuperAdmin ? 'Список Администраторов' : 'Управление камерами'}</span>
              {isSuperAdmin ? (
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    placeholder="Поиск администратора..."
                    value={adminSearch}
                    onChange={e => setAdminSearch(e.target.value)}
                    style={{ ...S.settingInput, width: 220, fontSize: 12, border: '1px solid #e2e8f0' }}
                  />
                  <select
                    value={adminCameraFilter}
                    onChange={e => setAdminCameraFilter(e.target.value as 'all' | 'with' | 'without')}
                    style={{ ...S.settingInput, width: 190, fontSize: 12, border: '1px solid #e2e8f0' }}
                  >
                    <option value="all">Все администраторы</option>
                    <option value="with">Только с камерами</option>
                    <option value="without">Только без камер</option>
                  </select>
                </div>
              ) : (
                canManageCameras && <button style={S.primaryMiniBtn} onClick={() => setShowAddCamModal(true)}>+ Добавить камеру</button>
              )}
            </div>
            <table style={S.table}>
              <thead>
                <tr>
                  {isSuperAdmin ? (
                    <>
                      <th style={S.th}>Администратор (Логин)</th>
                      <th style={S.th}>Компания</th>
                      <th style={S.th}>Камер создано</th>
                      <th style={S.th}>Действия</th>
                    </>
                  ) : (
                    <>
                      <th style={S.th}>Камера (Имя профиля)</th>
                      <th style={S.th}>Дата создания</th>
                      <th style={S.th}>Статус</th>
                      <th style={S.th}>Действия</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {isSuperAdmin ? (
                  filteredAdminAccounts.map(a => {
                    const adminCameras = cameras.filter(c => c.owner_id === a.id)
                    const isExpanded = expandedAdminIds.includes(a.id)
                    return (
                      <React.Fragment key={a.id}>
                        <tr
                          style={{ cursor: 'pointer', transition: 'background 0.15s' }}
                          onClick={() => setExpandedAdminIds(prev => isExpanded ? prev.filter(id => id !== a.id) : [...prev, a.id])}
                        >
                          <td style={{ ...S.td, fontWeight: 500 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{
                                fontSize: 10, color: '#94a3b8',
                                transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                                transition: 'transform 0.2s ease'
                              }}>
                                ▶
                              </span>
                              {a.username}
                            </div>
                          </td>
                          <td style={{ ...S.td, color: '#64748b' }}>{a.company_name || '-'}</td>
                          <td style={{ ...S.td, fontWeight: 600, color: '#0d1b4b' }}>{adminCameras.length}</td>
                          <td style={S.td}><span style={S.badgeActive}>Администрация</span></td>
                        </tr>
                        {isExpanded && (
                          <tr>
                            <td colSpan={4} style={{ padding: 0, borderBottom: '1px solid #e2e8f0', background: '#fafbff' }}>
                              <div style={{ padding: '14px 24px 18px 42px', animation: 'dashFade 0.2s ease' }}>
                                <div style={{ fontSize: 13, fontWeight: 600, color: '#0d1b4b', marginBottom: 10 }}>
                                  Камеры, созданные этим администратором
                                </div>
                                {adminCameras.length === 0 ? (
                                  <div style={{ fontSize: 13, color: '#94a3b8' }}>Камеры пока не созданы</div>
                                ) : (
                                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                                    {adminCameras.map(cam => (
                                      <div
                                        key={cam.id}
                                        style={{
                                          border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 12px',
                                          background: '#fff', display: 'flex', flexDirection: 'column', gap: 4,
                                        }}
                                      >
                                        <div style={{ fontSize: 14, fontWeight: 600, color: '#0d1b4b' }}>{cam.username}</div>
                                        <div style={{ fontSize: 12, color: '#64748b' }}>
                                          Создана: {new Date(cam.date_joined).toLocaleDateString()}
                                        </div>
                                        <div>
                                          {cam.is_active
                                            ? <span style={S.badgeOnline}><div style={{ ...S.dot, background: '#16a34a' }} />Активна</span>
                                            : <span style={S.badgeOffline}><div style={{ ...S.dot, background: '#dc2626' }} />Отключена</span>}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    )
                  })
                ) : (
                  cameras.map(c => (
                    <React.Fragment key={c.id}>
                      <tr style={{ cursor: 'pointer', transition: 'background 0.15s' }} onClick={() => handleToggleCameraFaces(c)}>
                        <td style={{ ...S.td, fontWeight: 500 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{
                              fontSize: 10, color: '#94a3b8',
                              transform: expandedCameraIds.includes(c.id) ? 'rotate(90deg)' : 'rotate(0deg)',
                              transition: 'transform 0.2s ease'
                            }}>
                              ▶
                            </span>
                            {c.username}
                          </div>
                        </td>
                        <td style={{ ...S.td, color: '#64748b' }}>{new Date(c.date_joined).toLocaleDateString()}</td>
                        <td style={S.td}>
                          {c.is_active
                            ? <span style={S.badgeOnline}><div style={{ ...S.dot, background: '#16a34a' }} />Активна</span>
                            : <span style={S.badgeOffline}><div style={{ ...S.dot, background: '#dc2626' }} />Отключена</span>}
                        </td>
                        <td style={S.td}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                            {canManageCameras && <button style={S.miniBtn} onClick={() => setAddExistingFaceModal(c)}>+ Пользователь</button>}
                            <button style={S.miniBtn} onClick={() => setPage('recognition')}>Просмотр логов</button>
                            {canManageCameras && (
                              <button
                                style={{ ...S.miniBtn, opacity: 0.55, cursor: 'not-allowed' }}
                                disabled
                                title="Настройки камеры не реализованы в API"
                              >
                                Настройки
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                      {expandedCameraIds.includes(c.id) && (
                        <tr>
                          <td colSpan={4} style={{ padding: 0, borderBottom: '1px solid #e2e8f0', background: '#fafbff' }}>
                            <div style={{ padding: '16px 24px 20px 42px', animation: 'dashFade 0.2s ease' }}>
                              <div style={{ fontSize: 13, fontWeight: 600, color: '#0d1b4b', marginBottom: 12 }}>
                                Зарегистрированные пользователи этой камеры
                              </div>
                              {cameraLoadingMap[c.id] ? (
                                <div style={{ fontSize: 13, color: '#64748b' }}>Загрузка пользователей...</div>
                              ) : (cameraFacesMap[c.id] || []).length === 0 ? (
                                <div style={{ fontSize: 13, color: '#94a3b8' }}>Нет зарегистрированных пользователей</div>
                              ) : (
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
                                  {(cameraFacesMap[c.id] || []).map(f => {
                                    const cardKey = `${c.id}-${f.id}`
                                    return (
                                      <div
                                        key={f.id}
                                        onMouseEnter={() => setHoveredCardKey(cardKey)}
                                        onMouseLeave={() => setHoveredCardKey(null)}
                                        style={{
                                          border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 14px',
                                          background: '#fff', display: 'flex', flexDirection: 'column',
                                          position: 'relative', transition: 'all 0.2s ease',
                                          boxShadow: hoveredCardKey === cardKey ? '0 4px 6px -1px rgba(0,0,0,0.1)' : 'none',
                                          borderColor: hoveredCardKey === cardKey ? '#cbd5e1' : '#e2e8f0'
                                        }}
                                      >
                                        {hoveredCardKey === cardKey && canManageCameras && (
                                          <button
                                            onClick={() => handleRemoveFaceFromCamera(c.id, f.id)}
                                            title="Убрать из этой камеры"
                                            style={{
                                              position: 'absolute', top: -6, right: -6,
                                              width: 18, height: 18, borderRadius: '50%',
                                              background: '#ef4444', color: '#fff', border: 'none',
                                              fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
                                              cursor: 'pointer', boxShadow: '0 2px 4px rgba(0,0,0,0.15)', zIndex: 5,
                                              lineHeight: 1
                                            }}
                                          >
                                            ×
                                          </button>
                                        )}
                                        <div style={{ fontSize: 14, fontWeight: 500, color: '#0d1b4b' }}>{f.full_name}</div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                                          <span style={{ fontSize: 12, color: '#64748b' }}>{f.role}</span>
                                          <span style={{ fontSize: 11, color: '#94a3b8' }}>
                                            {new Date(f.created_at).toLocaleDateString()}
                                          </span>
                                        </div>
                                      </div>
                                    )
                                  })}
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
                {isSuperAdmin && filteredAdminAccounts.length === 0 && (
                  <tr>
                    <td colSpan={4} style={{ ...S.td, textAlign: 'center', color: '#94a3b8' }}>
                      По заданным условиям администраторы не найдены
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )

      // ─── HISTORY ─────────────────────────────────────────────────────────────
      case 'history': {
        const formatAuditDetails = (text: string) => {
          if (!text) return ''
          const parts = text.split(/(\*\*.*?\*\*)/g)
          return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={i} style={{ color: '#0d1b4b', fontWeight: 700 }}>{part.slice(2, -2)}</strong>
            }
            return part
          })
        }

        return (
          <div style={{ animation: 'dashFade 0.3s ease' }}>
            <div style={S.card}>
              <div style={S.cardHeader}><span style={S.cardTitle}>Лог аудита ({auditLogs.length})</span></div>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>Дата и время</th>
                    <th style={S.th}>Администратор</th>
                    <th style={S.th}>Действие</th>
                    <th style={S.th}>Детали</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map(a => (
                    <tr key={a.id}>
                      <td style={{ ...S.td, color: '#94a3b8', fontSize: 13 }}>
                        {new Date(a.timestamp).toLocaleString()}
                      </td>
                      <td style={{ ...S.td, fontWeight: 500 }}>{a.username}</td>
                      <td style={S.td}>
                        <span style={{
                          padding: '4px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                          background: a.action.includes('Удаление') ? '#fef2f2' : '#f0f9ff',
                          color: a.action.includes('Удаление') ? '#ef4444' : '#1a3fd4',
                        }}>
                          {a.action}
                        </span>
                      </td>
                      <td style={{ ...S.td, color: '#64748b' }}>{formatAuditDetails(a.details)}</td>
                    </tr>
                  ))}
                  {auditLogs.length === 0 && (
                    <tr><td colSpan={4} style={{ ...S.td, textAlign: 'center', color: '#94a3b8' }}>История пуста</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )
      }

      // ─── SETTINGS ────────────────────────────────────────────────────────────
      case 'settings': return (
        <div style={{ animation: 'dashFade 0.3s ease' }}>
          <div style={{ ...S.grid2, alignItems: 'start' }}>
            <div>
              <div style={S.card}>
                <div style={S.cardHeader}><span style={S.cardTitle}>Параметры распознавания</span></div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Живое распознавание</div>
                    <div style={S.settingDesc}>Обрабатывать кадры в реальном времени</div>
                  </div>
                  <Toggle on={settings.liveDetect} onChange={() => toggleSetting('liveDetect')} />
                </div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Порог уверенности</div>
                    <div style={S.settingDesc}>Минимум для успешного распознавания (%)</div>
                  </div>
                  <input
                    type="number" min={50} max={100}
                    value={settings.threshold}
                    onChange={e => setSettings(s => ({ ...s, threshold: e.target.value }))}
                    style={S.settingInput}
                  />
                </div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Сохранять лог</div>
                    <div style={S.settingDesc}>Записывать все попытки распознавания</div>
                  </div>
                  <Toggle on={settings.saveLog} onChange={() => toggleSetting('saveLog')} />
                </div>
              </div>
            </div>

            <div>
              <div style={S.card}>
                <div style={S.cardHeader}><span style={S.cardTitle}>Безопасность</span></div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Уведомления о попытках взлома</div>
                    <div style={S.settingDesc}>Отправлять алерт при подозрительной активности</div>
                  </div>
                  <Toggle on={settings.alerts} onChange={() => toggleSetting('alerts')} />
                </div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Двухфакторная аутентификация</div>
                    <div style={S.settingDesc}>Дополнительная защита аккаунта</div>
                  </div>
                  <Toggle on={settings.twoFactor} onChange={() => toggleSetting('twoFactor')} />
                </div>
              </div>

              <div style={S.card}>
                <div style={S.cardHeader}><span style={S.cardTitle}>Интерфейс</span></div>
                <div style={S.settingRow}>
                  <div>
                    <div style={S.settingLabel}>Тёмная тема</div>
                    <div style={S.settingDesc}>Переключить оформление</div>
                  </div>
                  <Toggle on={settings.darkMode} onChange={() => toggleSetting('darkMode')} />
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    }
  }

  const PAGE_META: Record<NavPage, { title: string; subtitle: string }> = {
    overview: { title: 'Обзор', subtitle: 'Статус системы распознавания лиц в реальном времени' },
    users: { title: 'Пользователи', subtitle: 'Управление зарегистрированными в системе' },
    recognition: { title: 'Лог распознаваний', subtitle: 'История всех событий распознавания' },
    cameras: {
      title: isSuperAdmin ? 'Список Администраторов' : 'Камеры',
      subtitle: isSuperAdmin ? 'Пользователи с ролью Администрация и их созданные камеры' : 'Мониторинг и управление камерами'
    },
    settings: { title: 'Настройки', subtitle: 'Конфигурация системы' },
    history: { title: 'История действий', subtitle: 'Аудит системных событий, изменений и прав доступа' },
  }

  return (
    <div
      className={settings.darkMode ? 'dashboard-dark' : 'dashboard-light'}
      style={{
        ...S.root,
        ...(settings.darkMode ? darkThemeVars : lightThemeVars),
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        @keyframes dashFade { from { opacity:0; transform:translateY(8px) } to { opacity:1; transform:translateY(0) } }
        @keyframes modalOverlay { from { opacity: 0 } to { opacity: 1 } }
        @keyframes modalBox { from { opacity: 0; transform: scale(0.95); } to { opacity: 1; transform: scale(1); } }
        .dash-nav-btn:hover { background: rgba(26,63,212,0.05) !important; color: #1a3fd4 !important; }
        .dash-logout:hover { background: #fee2e2 !important; color: #dc2626 !important; border-color: #fecaca !important; }
        .dash-mini-btn:hover { background: #f8fafc !important; }
        tr:hover td { background: #fafbff; }
        .dashboard-dark .dash-nav-btn:hover { background: rgba(96,165,250,0.14) !important; color: #93c5fd !important; }
        .dashboard-dark .dash-mini-btn:hover { background: #243244 !important; }
        .dashboard-dark tr:hover td { background: #182338 !important; }
        .dashboard-dark input,
        .dashboard-dark select {
          background: var(--dash-input-bg) !important;
          border-color: var(--dash-border) !important;
          color: var(--dash-heading) !important;
        }
        .dashboard-dark input::placeholder {
          color: var(--dash-muted-soft) !important;
        }
        .dashboard-dark nav button {
          color: var(--dash-text) !important;
        }
        .dashboard-dark td,
        .dashboard-dark th,
        .dashboard-dark label,
        .dashboard-dark h3 {
          color: var(--dash-text) !important;
        }
        .dashboard-dark div,
        .dashboard-dark span,
        .dashboard-dark label,
        .dashboard-dark td,
        .dashboard-dark th,
        .dashboard-dark h3 {
          color: inherit;
        }
      `}</style>

      {/* Modal Overlay for Adding User */}
      {showAddModal && canManageFaces && (() => {
        const uniqueRoles = Array.from(
          new Set(['Студент', 'Преподаватель', 'Гость', ...faces.map(f => f.role)])
        ).filter(r => !/админ/i.test(r))
        return (
          <div style={{
            position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
            background: 'rgba(0,0,0,0.4)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'modalOverlay 0.2s ease',
          }}>
            <div style={{
              background: '#fff', padding: 28, borderRadius: 16, width: 360,
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)', animation: 'modalBox 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
            }}>
              <h3 style={{ margin: '0 0 16px', fontSize: 18, color: '#0d1b4b' }}>Добавить пользователя</h3>

              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 4 }}>ФИО</label>
                <input
                  value={newFaceName} onChange={e => setNewFaceName(e.target.value)}
                  placeholder="Фамилия Имя Отчество"
                  style={{
                    width: '92%', padding: '9px 12px', borderRadius: 8,
                    border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', fontFamily: "'Inter', sans-serif",
                    color: '#0d1b4b', background: '#fff'
                  }}
                />
              </div>

              <div style={{ marginBottom: newFaceRole === 'Другое...' ? 12 : 24 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 4 }}>Роль</label>
                <select
                  value={newFaceRole} onChange={e => setNewFaceRole(e.target.value)}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8,
                    border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', fontFamily: "'Inter', sans-serif",
                    background: '#fff', color: '#0d1b4b'
                  }}
                >
                  {uniqueRoles.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                  <option value="Другое...">Другое...</option>
                </select>
              </div>

              {newFaceRole === 'Другое...' && (
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 4 }}>Название новой роли</label>
                  <input
                    value={customRole} onChange={e => setCustomRole(e.target.value)}
                    placeholder="Введите название..."
                    style={{
                      width: '100%', padding: '9px 12px', borderRadius: 8,
                      border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', fontFamily: "'Inter', sans-serif",
                      color: '#0d1b4b', background: '#fff'
                    }}
                  />
                </div>
              )}

              <div style={{ marginBottom: 24, maxHeight: 150, overflowY: 'auto' }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 6 }}>
                  Доступ к камерам
                </label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {cameras.map(c => (
                    <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#0d1b4b', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedCameras.includes(c.id)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedCameras([...selectedCameras, c.id])
                          else setSelectedCameras(selectedCameras.filter(id => id !== c.id))
                        }}
                        style={{ cursor: 'pointer' }}
                      />
                      {c.username}
                      {c.id === cameras[0]?.id && selectedCameras.length === 0 && (
                        <span style={{ fontSize: 11, color: '#94a3b8' }}>(По умолчанию)</span>
                      )}
                    </label>
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={() => setShowAddModal(false)}
                  style={{ ...S.miniBtn, flex: 1, padding: '9px', fontSize: 14 }}
                >
                  Отмена
                </button>
                <button
                  onClick={handleAddFace}
                  disabled={addingFace || !newFaceName || (newFaceRole === 'Другое...' && !customRole)}
                  style={{
                    ...S.primaryMiniBtn, flex: 1, padding: '9px', fontSize: 14,
                    opacity: (!newFaceName || addingFace || (newFaceRole === 'Другое...' && !customRole)) ? 0.6 : 1
                  }}
                >
                  {addingFace ? 'Секунду...' : 'Сохранить'}
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* Modal Overlay for Adding Existing Face to Camera */}
      {addExistingFaceModal && canManageCameras && (() => {
        // filter out faces that are already visible in this camera (if expanded) to avoid confusion
        // but if it's not expanded, we just show all users. Or better, just show all users.
        return (
          <div style={{
            position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
            background: 'rgba(0,0,0,0.4)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'modalOverlay 0.2s ease',
          }}>
            <div style={{
              background: '#fff', padding: 28, borderRadius: 16, width: 360,
              boxShadow: '0 10px 40px rgba(0,0,0,0.2)', animation: 'modalBox 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
            }}>
              <h3 style={{ margin: '0 0 4px', fontSize: 18, color: '#0d1b4b' }}>Добавить пользователя</h3>
              <div style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>
                Для камеры: {addExistingFaceModal.username}
              </div>

              <div style={{ marginBottom: 24 }}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: '#64748b', marginBottom: 4 }}>Выберите пользователя из списка</label>
                <select
                  value={selectedFaceToAdd} onChange={e => setSelectedFaceToAdd(e.target.value)}
                  style={{
                    width: '100%', padding: '9px 12px', borderRadius: 8,
                    border: '1px solid #e2e8f0', fontSize: 14, outline: 'none', fontFamily: "'Inter', sans-serif",
                    background: '#fff', color: '#0d1b4b'
                  }}
                >
                  <option value="" disabled>-- Выберите из базы --</option>
                  {faces
                    .filter(f => !f.allowed_cameras?.includes(addExistingFaceModal!.id))
                    .map(f => (
                      <option key={f.id} value={f.id}>{f.full_name} ({f.role})</option>
                    ))
                  }
                </select>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={() => { setAddExistingFaceModal(null); setSelectedFaceToAdd(''); }}
                  style={{ ...S.miniBtn, flex: 1, padding: '9px', fontSize: 14 }}
                >
                  Отмена
                </button>
                <button
                  onClick={handleAddExistingFace}
                  disabled={addingExistingFace || !selectedFaceToAdd}
                  style={{
                    ...S.primaryMiniBtn, flex: 1, padding: '9px', fontSize: 14,
                    opacity: (!selectedFaceToAdd || addingExistingFace) ? 0.6 : 1
                  }}
                >
                  {addingExistingFace ? 'Секунду...' : 'Добавить'}
                </button>
              </div>
            </div>
          </div>
        )
      })()}

      {/* ── EDIT FACE MODAL ─────────────────────────────────────────────────── */}
      {editFaceModal && (
        <div style={S.modalOverlay}>
          <div style={{ ...S.modal, maxWidth: 450 }}>
            <div style={S.modalHeader}>
              <span style={{ fontWeight: 600 }}>Настройка пользователя</span>
              <button style={S.closeBtn} onClick={() => setEditFaceModal(null)}>×</button>
            </div>
            <div style={{ padding: '24px 28px' }}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>ФИО (Login)</div>
                <input
                  value={editName}
                  onChange={e => setEditName(e.target.value)}
                  style={{
                    width: '100%', padding: '10px 14px', borderRadius: 8,
                    border: '1px solid #e2e8f0', fontSize: 14, outline: 'none',
                    background: '#ffffff', color: '#0d1b4b', boxSizing: 'border-box'
                  }}
                />
              </div>

              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Роль</div>
                <select
                  value={editRole}
                  onChange={e => setEditRole(e.target.value)}
                  style={{
                    width: '100%', padding: '10px 14px', borderRadius: 8,
                    border: '1px solid #e2e8f0', fontSize: 14, outline: 'none',
                    background: '#ffffff', color: '#0d1b4b',
                    cursor: 'pointer', appearance: 'none', boxSizing: 'border-box',
                    backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' fill=\'none\' viewBox=\'0 0 24 24\' stroke=\'%23475569\'%3E%3Cpath stroke-linecap=\'round\' stroke-linejoin=\'round\' stroke-width=\'2\' d=\'M19 9l-7 7-7-7\'%3E%3C/path%3E%3C/svg%3E")',
                    backgroundRepeat: 'no-repeat', backgroundPosition: 'right 12px center',
                    backgroundSize: '16px'
                  }}
                >
                  <option value="Студент">Студент</option>
                  <option value="Преподаватель">Преподаватель</option>
                  <option value="Работник">Работник</option>
                  <option value="Гость">Гость</option>
                </select>
              </div>

              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Группы (Камеры)</div>
                <div style={{
                  maxHeight: 120, overflowY: 'auto', border: '1px solid #e2e8f0',
                  borderRadius: 8, padding: 8, background: '#f8fafc'
                }}>
                  {cameras.map(cam => (
                    <label key={cam.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 13, cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={editCams.includes(cam.id)}
                        onChange={e => {
                          if (e.target.checked) setEditCams([...editCams, cam.id])
                          else setEditCams(editCams.filter(id => id !== cam.id))
                        }}
                      />
                      {cam.username}
                    </label>
                  ))}
                  {cameras.length === 0 && <div style={{ fontSize: 12, color: '#94a3b8' }}>Нет доступных камер</div>}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12 }}>
                <button
                  onClick={() => setEditFaceModal(null)}
                  style={{ ...S.miniBtn, flex: 1, padding: '10px', fontSize: 14 }}
                >
                  Отмена
                </button>
                <button
                  onClick={handleUpdateFace}
                  disabled={updatingFace || !editName}
                  style={{
                    ...S.primaryMiniBtn, flex: 1, padding: '10px', fontSize: 14,
                    opacity: (!editName || updatingFace) ? 0.6 : 1
                  }}
                >
                  {updatingFace ? 'Сохранение...' : 'Сохранить изменения'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── CREATE CAMERA MODAL ────────────────────────────────────────────────── */}
      {showAddCamModal && canManageCameras && (
        <div style={S.modalOverlay}>
          <div style={{ ...S.modal, maxWidth: 400 }}>
            <div style={S.modalHeader}>
              <span style={{ fontWeight: 600 }}>Новая камера</span>
              <button style={S.closeBtn} onClick={() => setShowAddCamModal(false)}>×</button>
            </div>
            <div style={{ padding: '24px 28px' }}>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Название камеры (Логин)</div>
                <input
                  placeholder="Напр., Camera-Lobby"
                  value={newCamUser}
                  onChange={e => setNewCamUser(e.target.value)}
                  style={S.settingInput}
                />
              </div>
              <div style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Пароль для доступа камеры</div>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={newCamPass}
                  onChange={e => setNewCamPass(e.target.value)}
                  style={S.settingInput}
                />
              </div>
              <button
                style={{ ...S.primaryBtn, width: '100%' }}
                onClick={handleCreateCamera}
                disabled={creatingCam}
              >
                {creatingCam ? 'Создание...' : 'Создать камеру'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showRequestModal && isSuperAdmin && (
        <div style={S.modalOverlay}>
          <div style={{ ...S.modal, maxWidth: 520 }}>
            <div style={S.modalHeader}>
              <span style={{ fontWeight: 600 }}>Создание Заявки</span>
              <button style={S.closeBtn} onClick={() => { setShowRequestModal(false); setRequestError('') }}>×</button>
            </div>
            <div style={{ padding: '24px 28px' }}>
              <div style={{ marginBottom: 16, fontSize: 13, color: '#64748b' }}>
                Список пользователей с ролью Администрация
              </div>

              <div style={{ maxHeight: 180, overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: 8, marginBottom: 18 }}>
                <table style={S.table}>
                  <thead>
                    <tr>
                      <th style={S.th}>Логин</th>
                      <th style={S.th}>Компания</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminAccounts.map(a => (
                      <tr key={a.id}>
                        <td style={S.td}>{a.username}</td>
                        <td style={S.td}>{a.company_name || '-'}</td>
                      </tr>
                    ))}
                    {adminAccounts.length === 0 && (
                      <tr>
                        <td colSpan={2} style={{ ...S.td, textAlign: 'center', color: '#94a3b8' }}>Администраторы не найдены</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Логин</div>
                <input
                  value={requestLogin}
                  onChange={e => setRequestLogin(e.target.value)}
                  placeholder=""
                  style={S.settingInput}
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#475569', marginBottom: 6 }}>Пароль</div>
                <input
                  type="password"
                  value={requestPassword}
                  onChange={e => setRequestPassword(e.target.value)}
                  placeholder=""
                  style={S.settingInput}
                />
              </div>

              {requestError && (
                <div style={{ marginBottom: 12, fontSize: 12, color: '#dc2626' }}>{requestError}</div>
              )}

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={() => { setShowRequestModal(false); setRequestError('') }}
                  style={{ ...S.miniBtn, flex: 1, padding: '10px', fontSize: 14 }}
                >
                  Отмена
                </button>
                <button
                  onClick={handleCreateRequest}
                  disabled={creatingRequest || !requestLogin || !requestPassword}
                  style={{ ...S.primaryBtn, flex: 1, opacity: (creatingRequest || !requestLogin || !requestPassword) ? 0.6 : 1 }}
                >
                  {creatingRequest ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top bar */}
      <header style={S.topbar}>
        <div style={S.topbarBadge}>AITU</div>
        <span style={S.topbarTitle}>Face Recognition System — Admin Panel</span>
        <div style={S.topbarUser}>
          <div style={S.userAvatar}>{initial}</div>
          <span style={{ fontWeight: 500, color: '#334155' }}>{username}</span>
          <button className="dash-logout" style={S.logoutBtn} onClick={onLogout}>
            Выйти
          </button>
        </div>
      </header>
      <div style={S.topbarStripe} />

      {/* Body */}
      <div style={S.body}>
        {/* Sidebar */}
        <nav style={S.sidebar}>
          <div style={S.sidebarSection}>Главное</div>
          <NavItem icon="📊" label="Обзор" active={page === 'overview'} onClick={() => setPage('overview')} />
          <NavItem icon="👥" label="Пользователи" active={page === 'users'} onClick={() => setPage('users')} />
          <NavItem icon="🔍" label="Лог распознаваний" active={page === 'recognition'} onClick={() => setPage('recognition')} />

          <div style={S.sidebarSection}>Система</div>
          <NavItem icon="📷" label={isSuperAdmin ? 'Список Администраторов' : 'Камеры'} active={page === 'cameras'} onClick={() => setPage('cameras')} />
          <NavItem icon="⚙️" label="Настройки" active={page === 'settings'} onClick={() => setPage('settings')} />
          {canViewHistory && (
            <NavItem icon="📜" label="История" active={page === 'history'} onClick={() => setPage('history')} />
          )}
        </nav>

        {/* Main content */}
        <main style={S.main}>
          <div style={S.pageTitle}>{PAGE_META[page].title}</div>
          <div style={S.pageSubtitle}>{PAGE_META[page].subtitle}</div>
          {dashboardError && (
            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: 8,
              color: '#b91c1c',
              fontSize: 13,
              marginBottom: 16,
              padding: '10px 12px',
            }}>
              {dashboardError}
            </div>
          )}
          {renderPage()}
        </main>
      </div>
    </div>
  )
}

export default Dashboard
