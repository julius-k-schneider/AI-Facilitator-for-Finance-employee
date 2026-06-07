import Badge from '../components/Badge'
import ProgressBar from '../components/ProgressBar'
import { games } from '../data/games'
import { learningModules } from '../data/learningPath'
import { getModuleProgress, getNextMission } from '../utils/progressUtils'

export default function Progress({ progressData, onNavigate }) {
  const { progress, stats, badges, completedGames } = progressData
  const nextMissions = games.filter((game) => !progress.games?.[game.id]?.completed).slice(0, 3)
  const activity = progress.activity || []

  return (
    <main className="progress">
      <div className="page-container wide-container">
        <div className="page-header">
          <div>
            <p className="eyebrow">Your progress</p>
            <h1>Progress</h1>
            <p>Verfolge Punkte, Module, abgeschlossene Missions und automatisch freigeschaltete Badges.</p>
          </div>
          <button className="secondary-action" type="button" onClick={() => onNavigate('missions')}>
            Continue Learning
          </button>
        </div>

        <section className="content-card progress-summary">
          <div>
            <h2>Gesamtfortschritt</h2>
            <p>{stats.completedMissions} von {stats.totalMissions} Missions abgeschlossen</p>
          </div>
          <strong>{stats.learningProgress}%</strong>
          <ProgressBar value={stats.learningProgress} label="Overall mission progress" />
        </section>

        <section className="two-column-grid">
          <article className="content-card">
            <h2>Module Progress</h2>
            <div className="compact-list">
              {learningModules.map((module) => {
                const moduleProgress = getModuleProgress(module, progress)
                return (
                  <div className="compact-item" key={module.id}>
                    <div>
                      <strong>{module.title}</strong>
                      <span>{moduleProgress.status}</span>
                    </div>
                    <ProgressBar value={moduleProgress.percent} label={`${module.title} progress`} />
                  </div>
                )
              })}
            </div>
          </article>

          <article className="content-card">
            <h2>Badges</h2>
            <div className="badge-grid">
              {badges.length ? (
                badges.map((badge) => <Badge key={badge.id} tone="success">{badge.label}</Badge>)
              ) : (
                <p>Schliesse deine erste Mission ab, um Badges zu sammeln.</p>
              )}
            </div>
          </article>
        </section>

        <section className="two-column-grid">
          <article className="content-card">
            <h2>Completed Missions</h2>
            <div className="compact-list">
              {completedGames.length ? (
                completedGames.map((game) => (
                  <div className="compact-item" key={game.id}>
                    <strong>{game.title}</strong>
                    <span>{game.points} max pts</span>
                  </div>
                ))
              ) : (
                <p>Noch keine Mission abgeschlossen.</p>
              )}
            </div>
          </article>

          <article className="content-card">
            <h2>Recommended next</h2>
            <div className="compact-list">
              {(nextMissions.length ? nextMissions : [getNextMission(progress)]).map((game) => (
                <div className="compact-item" key={game.id}>
                  <strong>{game.title}</strong>
                  <span>{game.estimatedTime} · {game.points} pts</span>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="content-card">
          <h2>Punkteverlauf</h2>
          <div className="activity-list">
            {activity.length ? (
              activity.slice().reverse().map((item) => {
                const game = games.find((candidate) => candidate.id === item.gameId)
                return (
                  <div className="activity-item" key={`${item.gameId}-${item.date}`}>
                    <span>{game?.title || item.gameId}</span>
                    <strong>{item.score}/{game?.maxScore || 1}</strong>
                  </div>
                )
              })
            ) : (
              <p>Spiele eine Mission, um deinen Verlauf zu sehen.</p>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}
