import { useEffect, useState } from 'react'
import { AppShell, Box, Burger, Button, Center, Group, Loader, Text, Title } from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { IconLanguage, IconShieldLock } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { PERMISSIONS, hasPermission } from './auth/permissions'
import LoginScreen from './components/LoginScreen'
import Sidebar from './components/Sidebar'
import { NAV_LABEL_KEYS } from './nav'
import Grundlagen from './pages/Grundlagen'
import Home from './pages/Home'
import Leaderboard from './pages/Leaderboard'
import Missions from './pages/Missions'
import Profile from './pages/Profile'
import UserManagement from './pages/UserManagement'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const EMPTY_FORM = { password: '', email: '', first_name: '', last_name: '', role: 'accountant' }

function AccessDenied() {
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={860}>
      <Box bg="white" p={{ base: 'xl', md: 40 }} style={{ border: '1px solid var(--line)', borderRadius: 18 }}>
        <Group gap="md"><IconShieldLock size={28} /><Box><Title order={1}>Kein Zugriff</Title><Text c="dimmed">Du hast keine Berechtigung für diese Seite.</Text></Box></Group>
      </Box>
    </Box>
  )
}

function App() {
  const { t, i18n } = useTranslation()
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')
  const [page, setPage] = useState('home')
  const [pageRenderKey, setPageRenderKey] = useState(0)
  const [startMissionId, setStartMissionId] = useState(null)
  const [mode, setMode] = useState('login')
  const [message, setMessage] = useState('')
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

  const handleChange = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setMessage('')
    const body = { username: form.email, email: form.email, password: form.password }
    if (mode === 'register') {
      body.first_name = form.first_name
      body.last_name = form.last_name
      body.role = form.role
    }

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
    setPage('home')
  }

  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/auth/logout/`, { method: 'POST', credentials: 'include' })
    setUser(null)
    setStatus('guest')
    setPage('home')
    setMode('login')
    setForm(EMPTY_FORM)
  }

  const navigate = (value, options = {}) => {
    setStartMissionId(options.startMissionId || null)
    setPageRenderKey((current) => current + 1)
    setPage(value)
    closeMobile()
  }

  if (status === 'loading') {
    return <Center mih="100vh"><Group><Loader size="sm" /><Text c="dimmed">{t('app.checkingAuth')}</Text></Group></Center>
  }

  if (!user) {
    return <LoginScreen mode={mode} onModeChange={(value) => { setMode(value); setMessage('') }} form={form} onFieldChange={handleChange} onSubmit={handleSubmit} message={message} />
  }

  const renderPage = () => {
    switch (page) {
      case 'profile':
        return <Profile user={user} />
      case 'grundlagen':
        return <Grundlagen user={user} onUserUpdate={setUser} apiBase={API_BASE} />
      case 'missions':
        return <Missions user={user} navigate={navigate} startMissionId={startMissionId} />
      case 'leaderboard':
        return <Leaderboard user={user} />
      case 'user-management':
        return hasPermission(user, PERMISSIONS.MANAGE_USERS)
          ? <UserManagement currentUser={user} onCurrentUserUpdate={setUser} />
          : <AccessDenied />
      default:
        return <Home user={user} navigate={navigate} />
    }
  }

  return (
    <AppShell layout="alt" navbar={{ width: 272, breakpoint: 'sm', collapsed: { mobile: !mobileOpened } }} padding={0}>
      <AppShell.Navbar withBorder={false}><Sidebar page={page} onNavigate={navigate} user={user} onLogout={handleLogout} /></AppShell.Navbar>
      <AppShell.Main style={{ background: 'var(--paper)' }}>
        <Box px={{ base: 'lg', md: 40 }} py="md" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(255,255,255,0.7)', borderBottom: '1px solid var(--line)', position: 'sticky', top: 0, zIndex: 5 }}>
          <Group gap="md"><Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="sm" size="sm" /><Box><Text fz={11} fw={700} c="brand.6">{NAV_LABEL_KEYS[page] ? t(NAV_LABEL_KEYS[page]).toUpperCase() : ''}</Text><Title order={3} fz={18}>{t('app.greeting', { name: user.first_name || user.username })}</Title></Box></Group>
          <Button variant="subtle" color="secondary" size="sm" onClick={() => i18n.changeLanguage(i18n.language === 'de' ? 'en' : 'de')} leftSection={<IconLanguage size={16} />}>{t('language.current')}</Button>
        </Box>
        <Box key={`${page}-${pageRenderKey}-${startMissionId || 'overview'}`} className="fade-up">{renderPage()}</Box>
      </AppShell.Main>
    </AppShell>
  )
}

export default App
