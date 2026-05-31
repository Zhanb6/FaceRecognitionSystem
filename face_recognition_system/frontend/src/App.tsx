import { useState, useRef, useCallback } from 'react'
import type { FC, CSSProperties, ChangeEvent, KeyboardEvent } from 'react'
import aituLogo from './assets/aitu_logo.png'
import Dashboard from './Dashboard'
import { apiRequest, getErrorMessage, toJsonBody } from './api'
import type { AuthResponse, AuthUser } from './types'

// ── Types ────────────────────────────────────────────────────────────────────
type TabType = 'AUTH' | 'REGISTER'

interface AuthFormProps {
  fetchingAuth?: boolean
  setFetchingAuth?: (val: boolean) => void
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S: Record<string, CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#eef1f6',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: "'Inter', 'Segoe UI', sans-serif",
  },
  header: {
    background: '#ffffff',
    borderBottom: '1px solid #dde3ea',
    padding: '0 40px',
    height: 58,
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    boxShadow: '0 1px 6px rgba(0,0,0,0.07)',
    position: 'sticky' as const,
    top: 0,
    zIndex: 100,
  },
  headerStripe: {
    height: 3,
    background: 'linear-gradient(90deg, #0a1f6b 0%, #1a3fd4 45%, #00aaff 75%, #00d4ff 100%)',
  },
  badge: {
    width: 38, height: 38,
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #0a1f6b 0%, #1a3fd4 100%)',
    color: '#fff',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontSize: 10, fontWeight: 700, flexShrink: 0, letterSpacing: '-0.3px',
    boxShadow: '0 2px 8px rgba(26,63,212,0.35)',
  },
  headerTitle: {
    fontSize: 14, fontWeight: 600, color: '#0d1b4b', letterSpacing: '-0.01em',
  },
  main: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 24px',
  },
  card: {
    background: '#fff',
    borderRadius: 20,
    boxShadow: '0 8px 48px rgba(10,31,107,0.11), 0 2px 8px rgba(0,0,0,0.05)',
    display: 'flex',
    overflow: 'hidden',
    width: '100%',
    maxWidth: 800,
    minHeight: 510,
  },
  sidebar: {
    width: 192,
    flexShrink: 0,
    padding: '44px 0',
    borderRight: '1px solid #e8ecf2',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    background: '#f8f9fc',
  },
  panel: {
    flex: 1,
    padding: '50px 58px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  logoRing: {
    width: 92, height: 92,
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #dde8ff 0%, #b8ccff 100%)',
    border: '3px solid rgba(26,63,212,0.12)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    marginBottom: 20,
    boxShadow: '0 6px 28px rgba(26,63,212,0.18)',
    overflow: 'hidden',
  },
  logoImg: {
    width: '100%', height: '100%',
    objectFit: 'cover', borderRadius: '50%',
  },
  title: {
    fontSize: 22, fontWeight: 700, color: '#0d1b4b',
    marginBottom: 5, textAlign: 'center' as const, letterSpacing: '-0.02em',
  },
  subtitle: {
    fontSize: 13, color: '#1a3fd4', fontWeight: 500,
    marginBottom: 30, textAlign: 'center' as const,
  },
  formWrap: { width: '100%', maxWidth: 340 },
  fieldWrap: { position: 'relative' as const, marginBottom: 22 },
  floatLabel: {
    position: 'absolute' as const,
    left: 13, top: -10, zIndex: 10,
    background: '#fff',
    borderRadius: 4, padding: '0 5px',
    fontSize: 11, color: '#5a6a80', fontWeight: 600,
    letterSpacing: '0.02em', textTransform: 'uppercase' as const,
  },
  input: {
    width: '100%',
    height: 46,
    border: '1.5px solid #d0d7e8',
    borderRadius: 10,
    padding: '0 14px',
    fontSize: 14,
    color: '#0d1b4b',
    background: '#fafbfd',
    outline: 'none',
    fontFamily: "'Inter', sans-serif",
    boxSizing: 'border-box' as const,
    transition: 'border-color 0.2s, box-shadow 0.2s',
  },
  alertBox: {
    background: '#fff0f0', border: '1px solid #fcd5d5',
    borderRadius: 9, padding: '10px 14px',
    color: '#b91c1c', fontSize: 13, fontWeight: 500,
    marginBottom: 14, display: 'flex', alignItems: 'center', gap: 7,
  },
  successBox: {
    background: '#eff6ff', border: '1px solid #bdd0ff',
    borderRadius: 9, padding: '10px 14px',
    color: '#1a3fd4', fontSize: 13, fontWeight: 500,
    marginBottom: 14, display: 'flex', alignItems: 'center', gap: 7,
  },
  btnPrimary: {
    width: '100%', height: 46,
    background: 'linear-gradient(135deg, #0a1f6b 0%, #1a3fd4 100%)',
    border: 'none', borderRadius: 23,
    color: '#fff', fontSize: 15, fontWeight: 600,
    cursor: 'pointer',
    boxShadow: '0 4px 18px rgba(26,63,212,0.32)',
    transition: 'opacity 0.18s, transform 0.18s, box-shadow 0.18s',
    fontFamily: "'Inter', sans-serif",
    letterSpacing: '0.01em',
  },
  btnPrimaryDisabled: {
    opacity: 0.45, cursor: 'not-allowed',
    background: '#a0aec0', boxShadow: 'none',
  },
  btnLink: {
    background: 'none', border: 'none',
    color: '#1a3fd4', fontSize: 13, fontWeight: 500,
    cursor: 'pointer', padding: 0,
    fontFamily: "'Inter', sans-serif",
  },
  forgotRow: {
    display: 'flex', justifyContent: 'center', marginTop: 16,
  },
  ecpInfo: {
    textAlign: 'center' as const, color: '#5a6a80', fontSize: 13,
    marginBottom: 18, lineHeight: 1.6,
  },
  cancelRow: {
    display: 'flex', justifyContent: 'center', marginTop: 14,
  },
  pwWrap: {
    position: 'relative' as const,
  },
  pwToggle: {
    position: 'absolute' as const, right: 12, top: '50%',
    transform: 'translateY(-50%)',
    background: 'none', border: 'none', cursor: 'pointer',
    color: '#8a9ab0', fontSize: 16, padding: 0, display: 'flex', alignItems: 'center',
  },
  spinner: {
    display: 'inline-block',
    width: 16, height: 16,
    border: '2.5px solid rgba(255,255,255,0.4)',
    borderTopColor: '#fff',
    borderRadius: '50%',
    animation: 'spin 0.7s linear infinite',
    verticalAlign: 'middle',
    marginRight: 8,
  },
}

const globalCSS = `
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes shake {
  0%,100%{ transform:translateX(0) }
  20%{ transform:translateX(-7px) }
  40%{ transform:translateX(7px) }
  60%{ transform:translateX(-4px) }
  80%{ transform:translateX(4px) }
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.frs-input:focus {
  border-color: #1a3fd4 !important;
  box-shadow: 0 0 0 3px rgba(26,63,212,0.13) !important;
  background: #fff !important;
}
.frs-input.error-shake {
  animation: shake 0.4s ease both;
  border-color: #f87171 !important;
}
.frs-btn-primary:not(:disabled):hover {
  opacity: 0.88;
  transform: translateY(-1px);
  box-shadow: 0 8px 28px rgba(26,63,212,0.40) !important;
}
.frs-btn-primary:not(:disabled):active {
  transform: translateY(0);
  opacity: 0.95;
}
.frs-tab-btn {
  padding: 13px 30px;
  font-size: 14px;
  font-weight: 500;
  color: #7a8a99;
  cursor: pointer;
  border-right: 3px solid transparent;
  margin-right: -1px;
  user-select: none;
  transition: all 0.2s;
  background: none;
  border-top: none;
  border-bottom: none;
  border-left: none;
  text-align: left;
  width: 100%;
  font-family: 'Inter', sans-serif;
}
.frs-tab-btn:hover {
  color: #1a3fd4;
  background: rgba(26,63,212,0.04);
}
.frs-tab-btn.active {
  color: #1a3fd4;
  font-weight: 600;
  border-right: 3px solid #1a3fd4;
  background: rgba(26,63,212,0.06);
}
.frs-panel-animate {
  animation: fadeIn 0.25s ease both;
}
`

// ── PasswordInput ─────────────────────────────────────────────────────────────
const EyeIcon = ({ open }: { open: boolean }) =>
  open ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )

interface PwInputProps {
  value: string
  placeholder: string
  onChange: (e: ChangeEvent<HTMLInputElement>) => void
  onKeyDown?: (e: KeyboardEvent<HTMLInputElement>) => void
  shake?: boolean
  disabled?: boolean
}

const PasswordInput: FC<PwInputProps> = ({ value, placeholder, onChange, onKeyDown, shake, disabled }) => {
  const [show, setShow] = useState(false)
  return (
    <div style={S.pwWrap}>
      <input
        type={show ? 'text' : 'password'}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        onKeyDown={onKeyDown}
        disabled={disabled}
        className={`frs-input${shake ? ' error-shake' : ''}`}
        style={{ ...S.input, paddingRight: 42 }}
      />
      <button
        type="button"
        style={S.pwToggle}
        tabIndex={-1}
        onMouseDown={(e) => { e.preventDefault(); setShow(v => !v) }}
      >
        <EyeIcon open={show} />
      </button>
    </div>
  )
}

// ── AuthForm ──────────────────────────────────────────────────────────────────
const AuthForm: FC<AuthFormProps> = ({
  fetchingAuth = false,
  setFetchingAuth = () => {},
}) => {
  const [isLoggedIn, setIsLoggedIn] = useState(() => !!localStorage.getItem('access'))
  const [user, setUser] = useState<AuthUser | null>(() => {
    const saved = localStorage.getItem('user_data')
    if (!saved) return null
    try {
      return JSON.parse(saved) as AuthUser
    } catch {
      localStorage.removeItem('user_data')
      return null
    }
  })
  const [loggedUsername, setLoggedUsername] = useState(() => localStorage.getItem('username') || 'Admin')
  const [tab, setTab] = useState<TabType>('AUTH')
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [authStatus, setAuthStatus] = useState<boolean | null>(null)
  const [authError, setAuthError] = useState('Неверный логин или пароль')
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [loginShake, setLoginShake] = useState(false)
  const [passwordShake, setPasswordShake] = useState(false)

  const [regUsername, setRegUsername] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regPassword2, setRegPassword2] = useState('')
  const [regError, setRegError] = useState<string | null>(null)
  const [regSuccess, setRegSuccess] = useState<string | null>(null)
  const [regLoading, setRegLoading] = useState(false)

  const loginRef = useRef<HTMLInputElement>(null)

  const shake = (field: 'login' | 'password') => {
    if (field === 'login') {
      setLoginShake(true); setTimeout(() => setLoginShake(false), 500)
    } else {
      setPasswordShake(true); setTimeout(() => setPasswordShake(false), 500)
    }
  }

  const handleLogin = useCallback(async () => {
    if (fetchingAuth) return
    const loginValue = login.trim()
    if (!loginValue) { loginRef.current?.focus(); shake('login'); return }
    try {
      setFetchingAuth(true)
      setAuthStatus(null)
      setAuthError('Неверный логин, название камеры или пароль')
      setSuccessMsg(null)
      const data = await apiRequest<AuthResponse>('/api/auth/login/', {
        method: 'POST',
        body: toJsonBody({ login: loginValue, password }),
      })
      localStorage.setItem('access', data.tokens.access)
      localStorage.setItem('refresh', data.tokens.refresh)
      localStorage.setItem('user_data', JSON.stringify(data.user))
      const uname = data.user?.username || loginValue
      localStorage.setItem('username', uname)
      setUser(data.user)
      setLoggedUsername(uname)
      setAuthStatus(true)
      setSuccessMsg('Вход выполнен успешно!')
      setTimeout(() => setIsLoggedIn(true), 600)
    } catch (error) {
      console.error('Login failed:', error)
      setAuthError(getErrorMessage(error, 'Неверный логин, название камеры или пароль'))
      setAuthStatus(false)
    } finally {
      setFetchingAuth(false)
    }
  }, [fetchingAuth, login, password, setFetchingAuth])

  const handleRegister = async () => {
    setRegError(null); setRegSuccess(null)
    if (regPassword !== regPassword2) { setRegError('Пароли не совпадают'); return }
    setRegLoading(true)
    try {
      const data = await apiRequest<AuthResponse>('/api/auth/register/', {
        method: 'POST',
        body: toJsonBody({ username: regUsername, email: regEmail, password: regPassword, password_confirm: regPassword2 }),
      })
      localStorage.setItem('access', data.tokens.access)
      localStorage.setItem('refresh', data.tokens.refresh)
      localStorage.setItem('user_data', JSON.stringify(data.user))
      const uname = data.user?.username || regUsername
      localStorage.setItem('username', uname)
      setUser(data.user)
      setLoggedUsername(uname)
      setRegSuccess('Регистрация прошла успешно!')
      setTimeout(() => setIsLoggedIn(true), 800)
    } catch (error) {
      console.error('Registration failed:', error)
      setRegError(getErrorMessage(error, 'Ошибка соединения с сервером'))
    } finally {
      setRegLoading(false)
    }
  }

  const resetToLogin = () => {
    setLogin(''); setPassword('')
    setAuthStatus(null); setSuccessMsg(null)
  }

  const onKeyEnter = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleLogin()
  }

  const isLoginReady = Boolean(login.trim())
  const isRegReady = regUsername && regEmail && regPassword && regPassword2

  if (isLoggedIn) {
    return (
      <Dashboard
        username={loggedUsername}
        user={user}
        onLogout={() => {
          localStorage.removeItem('access')
          localStorage.removeItem('refresh')
          localStorage.removeItem('username')
          localStorage.removeItem('user_data')
          setIsLoggedIn(false)
          setUser(null)
        }}
      />
    )
  }

  return (
    <div style={S.page}>
      <style>{globalCSS}</style>

      {/* Header */}
      <header style={S.header}>
        <div style={S.badge}>FRS</div>
        <span style={S.headerTitle}>Face Recognition System</span>
      </header>
      <div style={S.headerStripe} />

      {/* Main */}
      <main style={S.main}>
        <div style={S.card}>

          {/* Sidebar nav */}
          <nav style={S.sidebar}>
            {(['AUTH', 'REGISTER'] as const).map(t => (
              <button
                key={t}
                className={`frs-tab-btn${tab === t ? ' active' : ''}`}
                onClick={() => {
                  setTab(t); resetToLogin()
                  setRegError(null); setRegSuccess(null)
                }}
              >
                {t === 'AUTH' ? 'Авторизация' : 'Регистрация'}
              </button>
            ))}
          </nav>

          {/* Panel */}
          <div style={S.panel}>
            <div style={S.logoRing}>
              <img src={aituLogo} alt="AITU Face Recognition" style={S.logoImg} />
            </div>

            <div style={S.title}>
              {tab === 'AUTH' ? 'Вход в систему' : 'Регистрация'}
            </div>
            <div style={S.subtitle}>
              {tab === 'AUTH'
                ? 'Система распознавания лиц'
                : 'Создайте учётную запись'}
            </div>

            <div style={S.formWrap}>

              {/* ── AUTH TAB ─────────────────────────────── */}
              {tab === 'AUTH' && (
                <div className="frs-panel-animate">
                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Логин</span>
                    <input
                      ref={loginRef}
                      className={`frs-input${loginShake ? ' error-shake' : ''}`}
                      style={S.input}
                      type="text"
                      value={login}
                      placeholder="Введите имя пользователя"
                      disabled={fetchingAuth}
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setLogin(e.target.value)}
                      onKeyDown={onKeyEnter}
                    />
                  </div>

                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Пароль (для камер не нужен)</span>
                    <PasswordInput
                      value={password}
                      placeholder="Введите пароль или оставьте пустым для камеры"
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyDown={onKeyEnter}
                      shake={passwordShake}
                      disabled={fetchingAuth}
                    />
                  </div>

                  {authStatus === false && (
                    <div style={S.alertBox}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {authError}
                    </div>
                  )}
                  {successMsg && (
                    <div style={S.successBox}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {successMsg}
                    </div>
                  )}

                  <button
                    className="frs-btn-primary"
                    style={{
                      ...S.btnPrimary,
                      ...((!isLoginReady || fetchingAuth) ? S.btnPrimaryDisabled : {}),
                    }}
                    disabled={!isLoginReady || fetchingAuth}
                    onClick={handleLogin}
                  >
                    {fetchingAuth && <span style={S.spinner} />}
                    Войти
                  </button>

                  <div style={S.forgotRow}>
                    <button
                      style={{ ...S.btnLink, opacity: 0.5, cursor: 'not-allowed' }}
                      disabled
                      title="Восстановление пароля пока не реализовано на сервере"
                    >
                      Забыли пароль?
                    </button>
                  </div>
                </div>
              )}

              {/* ── REGISTER TAB ──────────────────────────── */}
              {tab === 'REGISTER' && (
                <div className="frs-panel-animate">
                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Имя пользователя</span>
                    <input
                      className="frs-input"
                      style={S.input}
                      type="text"
                      value={regUsername}
                      placeholder="Введите логин"
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setRegUsername(e.target.value)}
                    />
                  </div>
                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Email</span>
                    <input
                      className="frs-input"
                      style={S.input}
                      type="email"
                      value={regEmail}
                      placeholder="example@aitu.edu.kz"
                      onChange={(e: ChangeEvent<HTMLInputElement>) => setRegEmail(e.target.value)}
                    />
                  </div>
                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Пароль</span>
                    <PasswordInput
                      value={regPassword}
                      placeholder="Введите пароль"
                      onChange={(e) => setRegPassword(e.target.value)}
                    />
                  </div>
                  <div style={S.fieldWrap}>
                    <span style={S.floatLabel}>Подтвердите пароль</span>
                    <PasswordInput
                      value={regPassword2}
                      placeholder="Повторите пароль"
                      onChange={(e) => setRegPassword2(e.target.value)}
                    />
                  </div>

                  {regError && (
                    <div style={S.alertBox}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                      </svg>
                      {regError}
                    </div>
                  )}
                  {regSuccess && (
                    <div style={S.successBox}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                      {regSuccess}
                    </div>
                  )}

                  <button
                    className="frs-btn-primary"
                    style={{
                      ...S.btnPrimary,
                      ...(!isRegReady || regLoading ? S.btnPrimaryDisabled : {}),
                    }}
                    disabled={!isRegReady || regLoading}
                    onClick={handleRegister}
                  >
                    {regLoading && <span style={S.spinner} />}
                    Зарегистрироваться
                  </button>
                </div>
              )}

            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default AuthForm
