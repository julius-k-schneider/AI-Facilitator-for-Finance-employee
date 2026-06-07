import StatCard from '../components/StatCard'
import ProgressBar from '../components/ProgressBar'
import { getNextMission, getUserDisplayName } from '../utils/progressUtils'
import './Home.css'

const skillTips = [
  'Gib AI immer Kontext, Zielgruppe und gewuenschtes Ausgabeformat mit.',
  'Lasse AI bei Finance-Analysen Annahmen und fehlende Daten explizit markieren.',
  'Verwende fuer interne Daten nur freigegebene Tools und anonymisiere sensible Informationen.',
]

function Home({ user, progressData, onNavigate }) {
  const { stats, progress } = progressData
  const nextMission = getNextMission(progress)
  const tip = skillTips[stats.completedMissions % skillTips.length]

  return (
    <main className="home-dashboard">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">AI Facilitator - Finance Employee</p>
          <h1>Willkommen zurueck, {getUserDisplayName(user)}</h1>
          <p>Build your AI skills through short role-specific finance challenges.</p>
        </div>
        <button className="hero-button" type="button" onClick={() => onNavigate('missions')}>
          <span>{stats.completedMissions > 0 ? 'Continue Learning' : 'Start Learning'}</span>
          <span className="hero-button-icon" aria-hidden="true" />
        </button>
      </section>

      <section className="stats-grid">
        <StatCard label="Gesamtpunkte" value={stats.points} detail="Best scores gespeichert" />
        <StatCard label="Completed Missions" value={`${stats.completedMissions}/${stats.totalMissions}`} />
        <StatCard label="Aktuelles Level" value={stats.level} detail="Level steigt mit Punkten" />
        <StatCard label="Learning Path" value={`${stats.learningProgress}%`} />
      </section>

      <section className="dashboard-grid">
        <article className="content-card recommended-card">
          <p className="eyebrow">Recommended next mission</p>
          <h2>{nextMission.title}</h2>
          <p>{nextMission.description}</p>
          <div className="mission-meta">
            <span>{nextMission.difficulty}</span>
            <span>{nextMission.estimatedTime}</span>
            <span>{nextMission.points} pts</span>
          </div>
          <button className="secondary-action" type="button" onClick={() => onNavigate('missions')}>
            Mission oeffnen
          </button>
        </article>

        <article className="content-card">
          <p className="eyebrow">Today's AI Skill</p>
          <h2>Finance Prompting Tip</h2>
          <p>{tip}</p>
          <ProgressBar value={stats.learningProgress} label="Learning path progress" />
        </article>
      </section>
    </main>
  )
}

export default Home
