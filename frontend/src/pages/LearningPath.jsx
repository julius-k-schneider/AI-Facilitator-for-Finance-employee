import Badge from '../components/Badge'
import ProgressBar from '../components/ProgressBar'
import { learningModules } from '../data/learningPath'
import { getModuleProgress } from '../utils/progressUtils'

export default function LearningPath({ progressData, onNavigate }) {
  const { progress } = progressData

  return (
    <main className="learning-path">
      <div className="page-container wide-container">
        <div className="page-header">
          <div>
            <p className="eyebrow">Role-based enablement</p>
            <h1>Your AI Learning Path</h1>
            <p>Der Pfad besteht aus kurzen Modulen. Missions aktualisieren den Fortschritt automatisch.</p>
          </div>
          <button className="secondary-action" type="button" onClick={() => onNavigate('missions')}>
            Missions ansehen
          </button>
        </div>

        <div className="module-list">
          {learningModules.map((module, index) => {
            const moduleProgress = getModuleProgress(module, progress)
            return (
              <article className="module-card" key={module.id}>
                <div className="module-index">{index + 1}</div>
                <div className="module-body">
                  <div className="module-title-row">
                    <h2>{module.title}</h2>
                    <Badge tone={moduleProgress.status === 'Completed' ? 'success' : 'default'}>
                      {moduleProgress.status}
                    </Badge>
                  </div>
                  <p>{module.description}</p>
                  <ProgressBar value={moduleProgress.percent} label={`${module.title} progress`} />
                  <div className="linked-missions">
                    {moduleProgress.games.map((game) => (
                      <span key={game.id}>{game.title}</span>
                    ))}
                  </div>
                </div>
                <strong>{moduleProgress.percent}%</strong>
              </article>
            )
          })}
        </div>
      </div>
    </main>
  )
}
