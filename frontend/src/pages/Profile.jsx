import { useState } from 'react'
import Badge from '../components/Badge'
import StatCard from '../components/StatCard'
import { getRole } from '../utils/progressUtils'
import './Profile.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function Profile({ user, progressData }) {
  const { stats, badges } = progressData
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordForm, setPasswordForm] = useState({
    old_password: '',
    new_password: '',
  })

  const handlePasswordChange = async (event) => {
    event.preventDefault()
    setPasswordMessage('')
    const response = await fetch(`${API_BASE}/api/auth/change-password/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(passwordForm),
    })

    const data = await response.json()
    if (!response.ok) {
      setPasswordMessage(data.error || 'Could not change password')
      return
    }

    setPasswordMessage('Password updated successfully')
    setPasswordForm({ old_password: '', new_password: '' })
  }

  return (
    <main className="profile">
      <section className="profile-card">
        <h1>Profile</h1>
        <div className="profile-row">
          <div>
            <p className="profile-label">Username</p>
            <p>{user.username}</p>
          </div>
          <div>
            <p className="profile-label">Name</p>
            <p>{user.first_name} {user.last_name}</p>
          </div>
          <div>
            <p className="profile-label">Email</p>
            <p>{user.email}</p>
          </div>
          <div>
            <p className="profile-label">Role</p>
            <p>{getRole(user)}</p>
          </div>
        </div>

        <div className="profile-stats-grid">
          <StatCard label="Points" value={stats.points} />
          <StatCard label="Level" value={stats.level} />
          <StatCard label="Completed Missions" value={stats.completedMissions} />
        </div>

        <div className="profile-badges">
          <p className="profile-label">Badges</p>
          <div className="badge-grid">
            {badges.length ? (
              badges.map((badge) => <Badge key={badge.id} tone="success">{badge.label}</Badge>)
            ) : (
              <p>No badges yet. Complete your first mission to unlock one.</p>
            )}
          </div>
        </div>

        <form className="password-form" onSubmit={handlePasswordChange}>
          <label>
            Current password
            <input
              type="password"
              value={passwordForm.old_password}
              onChange={(event) => setPasswordForm((current) => ({ ...current, old_password: event.target.value }))}
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={passwordForm.new_password}
              onChange={(event) => setPasswordForm((current) => ({ ...current, new_password: event.target.value }))}
            />
          </label>
          <button className="action-button" type="submit">
            Change password
          </button>
          {passwordMessage && <p className="password-message">{passwordMessage}</p>}
        </form>
      </section>
    </main>
  )
}

export default Profile
