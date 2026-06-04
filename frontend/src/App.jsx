import { useEffect, useState } from 'react'
import './App.css'
import lufthansaLogo from './assets/Lufthansa_Group_2025.svg.png'
import Home from './pages/Home'
import Profile from './pages/Profile'
import LearningPath from './pages/LearningPath'
import Missions from './pages/Missions'
import Progress from './pages/Progress'
import Leaderboard from './pages/Leaderboard'
import Resources from './pages/Resources'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function App() {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')
  const [page, setPage] = useState('home')
  const [mode, setMode] = useState('login')
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({
    username: '',
    password: '',
    email: '',
    first_name: '',
    last_name: '',
  })

  useEffect(() => {
    fetch(`${API_BASE}/api/auth/user/`, {
      credentials: 'include',
    })
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
    setForm((current) => ({
      ...current,
      [field]: event.target.value,
    }))
  }

  const sendAuth = async (path) => {
    const body = {
      username: form.username,
      password: form.password,
    }

    if (mode === 'register') {
      body.email = form.email
      body.first_name = form.first_name
      body.last_name = form.last_name
    }

    const response = await fetch(`${API_BASE}/api/auth/${path}/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    if (!response.ok) {
      setMessage(data.error || 'Something went wrong')
      return null
    }
    return data
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setMessage('')
    const path = mode === 'login' ? 'login' : 'register'
    const data = await sendAuth(path)
    if (data?.authenticated) {
      setUser(data.user)
      setStatus('ready')
      setPage('home')
      setMessage('')
    }
  }

  const handleLogout = async () => {
    await fetch(`${API_BASE}/api/auth/logout/`, {
      method: 'POST',
      credentials: 'include',
    })
    setUser(null)
    setStatus('guest')
    setPage('home')
    setMode('login')
    setForm({ username: '', password: '', email: '', first_name: '', last_name: '' })
    setMessage('You are logged out.')
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-top">
          <img src={lufthansaLogo} alt="Lufthansa Group Logo" className="logo" />
          <div className="header-actions">
            {user && (
              <button className="logout-button" onClick={handleLogout}>
                Logout
              </button>
            )}
            <button className="language-button">Deutsch</button>
          </div>
        </div>

        {user && (
          <nav className="main-nav">
            <button
              type="button"
              className={page === 'home' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('home')}
            >
              Home
            </button>
            <button
              type="button"
              className={page === 'learning-path' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('learning-path')}
            >
              Learning Path
            </button>
            <button
              type="button"
              className={page === 'missions' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('missions')}
            >
              Missions
            </button>
            <button
              type="button"
              className={page === 'progress' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('progress')}
            >
              Progress
            </button>
            <button
              type="button"
              className={page === 'leaderboard' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('leaderboard')}
            >
              Leaderboard
            </button>
            <button
              type="button"
              className={page === 'resources' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('resources')}
            >
              Resources
            </button>
            <button
              type="button"
              className={page === 'profile' ? 'nav-link active' : 'nav-link'}
              onClick={() => setPage('profile')}
            >
              Profile
            </button>
          </nav>
        )}
      </header>

      {status === 'loading' ? (
        <main>
          <div style={{ textAlign: 'center', paddingTop: '40px' }}>Checking authentication...</div>
        </main>
      ) : user ? (
        page === 'profile' ? (
          <Profile user={user} />
        ) : page === 'learning-path' ? (
          <LearningPath />
        ) : page === 'missions' ? (
          <Missions />
        ) : page === 'progress' ? (
          <Progress />
        ) : page === 'leaderboard' ? (
          <Leaderboard />
        ) : page === 'resources' ? (
          <Resources />
        ) : (
          <Home />
        )
      ) : (
        <main className="auth-page">
          <section className="auth-card">
            <h1>AI facilitator</h1>
            <p className="auth-note">You are not signed in yet.</p>
            <div className="switch-row">
              <button
                className={mode === 'login' ? 'switch-button active' : 'switch-button'}
                onClick={() => {
                  setMode('login')
                  setMessage('')
                }}
                type="button"
              >
                Login
              </button>
              <button
                className={mode === 'register' ? 'switch-button active' : 'switch-button'}
                onClick={() => {
                  setMode('register')
                  setMessage('')
                }}
                type="button"
              >
                Create account
              </button>
            </div>
            <form className="auth-form" onSubmit={handleSubmit}>
              <label>
                Username
                <input value={form.username} onChange={handleChange('username')} />
              </label>
              {mode === 'register' && (
                <>
                  <label>
                    Email
                    <input value={form.email} onChange={handleChange('email')} />
                  </label>
                  <label>
                    First name
                    <input value={form.first_name} onChange={handleChange('first_name')} />
                  </label>
                  <label>
                    Last name
                    <input value={form.last_name} onChange={handleChange('last_name')} />
                  </label>
                </>
              )}
              <label>
                Password
                <input type="password" value={form.password} onChange={handleChange('password')} />
              </label>
              <button className="action-button" type="submit">
                {mode === 'login' ? 'Login' : 'Register'}
              </button>
            </form>
            {message && <p className="auth-error">{message}</p>}
          </section>
        </main>
      )}
    </div>
  )
}

export default App
