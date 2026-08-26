import { useEffect, useState } from 'react'
import { AppShell, Box, Burger, Group, Loader, SegmentedControl, Text, Title } from '@mantine/core'
import { DatesProvider } from '@mantine/dates'
import { useDisclosure } from '@mantine/hooks'
import dayjs from 'dayjs'
import 'dayjs/locale/de'
import 'dayjs/locale/en'
import { IconShieldLock } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { PERMISSIONS, hasPermission } from './auth/permissions'
import LoginScreen from './components/LoginScreen'
import Sidebar from './components/Sidebar'
import { SUPPORTED_LANGUAGES } from './i18n'
import { navLabelKeyForPath } from './nav'
import YourAgent from './pages/YourAgent'
import Basics from './pages/Basics'
import Home from './pages/Home'
import Leaderboard from './pages/Leaderboard'
import Missions from './pages/Missions'
import Training from './pages/Training'
import Profile from './pages/Profile'
import UserManagement from './pages/UserManagement'
import { PROGRESS_EVENT } from './services/progressService'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const EMPTY_FORM = { password: '', email: '', first_name: '', last_name: '', role: 'accountant' }
export const HEADER_HEIGHT = 64

function AccessDenied() {
  const { t } = useTranslation()
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Box bg="white" p={{ base: 'xl', md: 40 }} style={{ border: '1px solid var(--line)', borderRadius: 18 }}>
        <Group gap="md"><IconShieldLock size={28} /><Box><Title order={1}>{t('app.accessDenied.title')}</Title><Text c="dimmed">{t('app.accessDenied.text')}</Text></Box></Group>
      </Box>
    </Box>
  )
}

// Missions, Training and "Your Agent" only unlock after the onboarding. The
// sidebar hides them, but a bookmark or a typed URL used to walk straight in --
// so the routes enforce the same rule and send the user where they can lift it.
function RequireOnboarding({ user, children }) {
  const location = useLocation()
  const unlocked = Boolean(user?.onboarding_completed) || hasPermission(user, PERMISSIONS.CREATE_CONTENT)
  if (unlocked) return children
  return <Navigate to="/basics" replace state={{ lockedFrom: location.pathname }} />
}

function LanguageSwitch() {
  const { t, i18n } = useTranslation()
  const current = SUPPORTED_LANGUAGES.includes(i18n.resolvedLanguage) ? i18n.resolvedLanguage : 'de'
  return (
    <SegmentedControl
      size="xs"
      radius="md"
      value={current}
      onChange={(value) => i18n.changeLanguage(value)}
      aria-label={t('language.label')}
      data={SUPPORTED_LANGUAGES.map((code) => ({ value: code, label: code.toUpperCase() }))}
    />
  )
}

function App() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')
  const [mode, setMode] = useState('login')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [mobileOpened, { toggle: toggleMobile, close: closeMobile }] = useDisclosure(false)

  useEffect(() => {
    fetch(`${API_BASE}/api/auth/user/`, { credentials: 'include' })
      .then((response) => response.ok && response.json())
      .then((data) => {
        if (data?.authenticated) {
          setUser(data.user)
          setStatus('ready')
        } else {
          setStatus('guest')
        }
      })
      .catch(() => setStatus('guest'))
  }, [])

  useEffect(() => {
    const refreshUser = () => {
      fetch(`${API_BASE}/api/auth/user/`, { credentials: 'include' })
        .then((response) => response.ok && response.json())
        .then((data) => { if (data?.authenticated) setUser(data.user) })
        .catch(() => {})
    }
    window.addEventListener(PROGRESS_EVENT, refreshUser)
    return () => window.removeEventListener(PROGRESS_EVENT, refreshUser)
  }, [])

  useEffect(() => {
    closeMobile()
  }, [location.pathname, closeMobile])

  const handleChange = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setMessage('')
    setSubmitting(true)
    const body = { username: form.email, email: form.email, password: form.password }
    if (mode === 'register') {
      body.first_name = form.first_name
      body.last_name = form.last_name
      body.role = form.role
    }

    try {
      const response = await fetch(`${API_BASE}/api/auth/${mode === 'login' ? 'login' : 'register'}/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setMessage(data.error || t('app.genericError'))
        return
      }
      setUser(data.user)
      setStatus('ready')
      navigate('/', { replace: true })
    } catch {
      // Aborted request, server unreachable, DNS failure -- without this the
      // promise rejected silently and the form simply did nothing.
      setMessage(t('app.networkError'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/auth/logout/`, { method: 'POST', credentials: 'include' }).catch(() => {})
    setUser(null)
    setStatus('guest')
    navigate('/', { replace: true })
    setMode('login')
    setForm(EMPTY_FORM)
  }

  if (status === 'loading') {
    return <Box mih="100vh" style={{ display: 'grid', placeItems: 'center' }}><Group><Loader size="sm" /><Text c="dimmed">{t('app.checkingAuth')}</Text></Group></Box>
  }

  if (!user) {
    return (
      <LoginScreen
        mode={mode}
        onModeChange={(value) => { setMode(value); setMessage('') }}
        form={form}
        onFieldChange={handleChange}
        onSubmit={handleSubmit}
        submitting={submitting}
        message={message}
        languageSwitch={<LanguageSwitch />}
      />
    )
  }

  const pageLabelKey = navLabelKeyForPath(location.pathname)
  // Fade between top-level sections only -- keying on the full pathname would
  // remount the page when opening a mission detail route and lose its state.
  const sectionKey = `/${location.pathname.split('/')[1] || ''}`

  return (
    <AppShell
      layout="alt"
      header={{ height: HEADER_HEIGHT }}
      navbar={{ width: 272, breakpoint: 'sm', collapsed: { mobile: !mobileOpened } }}
      padding={0}
    >
      <AppShell.Header withBorder={false} className="app-header">
        <Group h="100%" px={{ base: 'lg', md: 40 }} justify="space-between" wrap="nowrap">
          <Group gap="md" wrap="nowrap" style={{ minWidth: 0 }}>
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="sm" size="sm" />
            <Title
              order={1}
              fz={{ base: 17, md: 19 }}
              c="secondary.9"
              lh={1.2}
              style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
            >
              {pageLabelKey ? t(pageLabelKey) : ''}
            </Title>
          </Group>
          <LanguageSwitch />
        </Group>
      </AppShell.Header>
      <AppShell.Navbar withBorder={false}><Sidebar user={user} onLogout={handleLogout} /></AppShell.Navbar>
      <AppShell.Main style={{ background: 'var(--paper)' }}>
        <Box key={sectionKey} className="fade-up">
          <Routes>
            <Route path="/" element={<Home user={user} />} />
            <Route path="/basics" element={<Basics user={user} onUserUpdate={setUser} apiBase={API_BASE} />} />
            <Route path="/basics/onboarding" element={<Basics user={user} onUserUpdate={setUser} apiBase={API_BASE} />} />
            <Route path="/missions" element={<RequireOnboarding user={user}><Missions user={user} /></RequireOnboarding>} />
            <Route path="/missions/:missionId" element={<RequireOnboarding user={user}><Missions user={user} /></RequireOnboarding>} />
            <Route path="/training" element={<RequireOnboarding user={user}><Training /></RequireOnboarding>} />
            <Route path="/agent" element={<RequireOnboarding user={user}><YourAgent /></RequireOnboarding>} />
            <Route path="/leaderboard" element={<Leaderboard user={user} />} />
            <Route path="/profile" element={<Profile user={user} />} />
            <Route
              path="/user-management"
              element={hasPermission(user, PERMISSIONS.MANAGE_USERS)
                ? <UserManagement currentUser={user} onCurrentUserUpdate={setUser} />
                : <AccessDenied />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </AppShell.Main>
    </AppShell>
  )
}

// The date pickers render month and weekday names through dayjs, so they need
// the same language the rest of the app is running in.
function AppWithDates() {
  const { i18n } = useTranslation()
  const locale = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  dayjs.locale(locale)
  return (
    <DatesProvider settings={{ locale, firstDayOfWeek: 1, weekendDays: [0, 6] }}>
      <App />
    </DatesProvider>
  )
}

export default AppWithDates
