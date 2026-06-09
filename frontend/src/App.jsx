import { useEffect, useState } from 'react'
import {
  AppShell,
  Box,
  Burger,
  Button,
  Center,
  Group,
  Loader,
  Text,
  Title,
} from '@mantine/core'
import { IconShieldLock } from '@tabler/icons-react'
import { useDisclosure } from '@mantine/hooks'
import Sidebar from './components/Sidebar'
import LoginScreen from './components/LoginScreen'
import { NAV_LABELS } from './nav'
import { PERMISSIONS, hasPermission } from './auth/permissions'
import Home from './pages/Home'
import Profile from './pages/Profile'
import LearningPath from './pages/LearningPath'
import Missions from './pages/Missions'
import Progress from './pages/Progress'
import Leaderboard from './pages/Leaderboard'
import Resources from './pages/Resources'
import UserManagement from './pages/UserManagement'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const PAGES = {
  profile: ({ user }) => <Profile user={user} />,
  'learning-path': () => <LearningPath />,
  missions: ({ user, navigate, startMissionId }) => (
    <Missions user={user} navigate={navigate} startMissionId={startMissionId} />
  ),
  progress: () => <Progress />,
  leaderboard: ({ user }) => <Leaderboard user={user} />,
  'user-management': ({ user, setUser }) => (
    <RequirePermission user={user} permission={PERMISSIONS.MANAGE_USERS}>
      <UserManagement currentUser={user} onCurrentUserUpdate={setUser} />
    </RequirePermission>
  ),
  resources: () => <Resources />,
  home: ({ user, navigate }) => <Home user={user} navigate={navigate} />,
}

function AccessDenied() {
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={860}>
      <Box
        bg="white"
        p={{ base: 'xl', md: 40 }}
        style={{
          border: '1px solid var(--line)',
          borderRadius: 18,
        }}
      >
        <Group gap="md" align="flex-start">
          <Box
            style={{
              width: 48,
              height: 48,
              borderRadius: 14,
              display: 'grid',
              placeItems: 'center',
              background: 'var(--mantine-color-brand-0)',
              color: 'var(--mantine-color-brand-7)',
            }}
          >
            <IconShieldLock size={25} stroke={1.7} />
          </Box>
          <Box>
            <Title order={1} fz={{ base: 26, md: 32 }} c="secondary.9">
              Kein Zugriff
            </Title>
            <Text c="dimmed" mt={6}>
              Du hast keine Berechtigung, diese Seite zu öffnen.
            </Text>
          </Box>
        </Group>
      </Box>
    </Box>
  )
}

function RequirePermission({ user, permission, children }) {
  if (!hasPermission(user, permission)) {
    return <AccessDenied />
  }

  return children
}

const EMPTY_FORM = { password: '', email: '', first_name: '', last_name: '' }

function App() {
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
          return
        }
        setStatus('guest')
      })
      .catch(() => setStatus('guest'))
  }, [])

  const handleChange = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }))
  }

  const sendAuth = async (path) => {
    // E-Mail dient als Login-Kennung; das Backend bildet den Username daraus ab.
    const body = { username: form.email, email: form.email, password: form.password }
    if (mode === 'register') {
      body.first_name = form.first_name
      body.last_name = form.last_name
    }

    const response = await fetch(`${API_BASE}/api/auth/${path}/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    if (!response.ok) {
      setMessage(data.error || 'Etwas ist schiefgelaufen')
      return null
    }
    return data
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setMessage('')
    const data = await sendAuth(mode === 'login' ? 'login' : 'register')
    if (data?.authenticated) {
      setUser(data.user)
      setStatus('ready')
      setPage('home')
      setMessage('')
    }
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
    return (
      <Center mih="100vh">
        <Group gap="sm">
          <Loader color="brand" size="sm" />
          <Text c="dimmed">Authentifizierung wird geprüft…</Text>
        </Group>
      </Center>
    )
  }

  if (!user) {
    return (
      <LoginScreen
        mode={mode}
        onModeChange={(value) => {
          setMode(value)
          setMessage('')
        }}
        form={form}
        onFieldChange={handleChange}
        onSubmit={handleSubmit}
        message={message}
      />
    )
  }

  return (
    <AppShell
      layout="alt"
      navbar={{ width: 272, breakpoint: 'sm', collapsed: { mobile: !mobileOpened } }}
      padding={0}
    >
      <AppShell.Navbar withBorder={false} style={{ border: 'none' }}>
        <Sidebar page={page} onNavigate={navigate} user={user} onLogout={handleLogout} />
      </AppShell.Navbar>

      <AppShell.Main style={{ background: 'var(--paper)' }}>
        {/* Schlanke Topbar mit Kontext + Mobile-Burger */}
        <Box
          px={{ base: 'lg', md: 40 }}
          py="md"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(255,255,255,0.7)',
            backdropFilter: 'blur(8px)',
            borderBottom: '1px solid var(--line)',
            position: 'sticky',
            top: 0,
            zIndex: 5,
          }}
        >
          <Group gap="md">
            <Burger opened={mobileOpened} onClick={toggleMobile} hiddenFrom="sm" size="sm" />
            <Box>
              <Text fz={11} fw={700} c="brand.6" style={{ letterSpacing: '0.12em' }}>
                {NAV_LABELS[page]?.toUpperCase()}
              </Text>
              <Title order={3} fz={18} c="secondary.9" fw={600}>
                Hallo, {user.first_name || user.username} 👋
              </Title>
            </Box>
          </Group>
          <Button variant="subtle" color="secondary" size="sm" radius="md">
            Deutsch
          </Button>
        </Box>

        <Box key={`${page}-${pageRenderKey}-${startMissionId || 'overview'}`} className="fade-up">
          {(PAGES[page] || PAGES.home)({
            user,
            setUser,
            navigate,
            startMissionId,
          })}
        </Box>
      </AppShell.Main>
    </AppShell>
  )
}

export default App
