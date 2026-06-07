import { useMemo, useState } from 'react'
import MissionCard from '../components/MissionCard'
import { gameCategories, games, getGameById } from '../data/games'
import ComplianceCheckChallenge from '../games/ComplianceCheckChallenge'
import PromptQualityQuiz from '../games/PromptQualityQuiz'

const gameComponents = {
  PromptQualityQuiz,
  ComplianceCheckChallenge,
}

export default function Missions({ progressData, onNavigate }) {
  const { progress, completeGame } = progressData
  const [category, setCategory] = useState('all')
  const [activeGameId, setActiveGameId] = useState(null)
  const activeGame = activeGameId ? getGameById(activeGameId) : null
  const ActiveGameComponent = activeGame?.component ? gameComponents[activeGame.component] : null

  const visibleGames = useMemo(
    () => games.filter((game) => category === 'all' || game.category === category),
    [category],
  )

  if (activeGame && ActiveGameComponent) {
    return (
      <main className="missions">
        <div className="page-container wide-container">
          <ActiveGameComponent
            game={activeGame}
            gameProgress={progress.games?.[activeGame.id]}
            onBack={() => setActiveGameId(null)}
            onComplete={completeGame}
            onProgress={() => onNavigate('progress')}
          />
        </div>
      </main>
    )
  }

  return (
    <main className="missions">
      <div className="page-container wide-container">
        <div className="page-header">
          <div>
            <p className="eyebrow">Gamified challenges</p>
            <h1>Missions</h1>
            <p>Starte kurze AI-Finance-Challenges, sammle Punkte und verbessere deinen Learning Path.</p>
          </div>
        </div>

        <div className="filter-row">
          {gameCategories.map((item) => (
            <button
              className={category === item.id ? 'filter-button active' : 'filter-button'}
              key={item.id}
              onClick={() => setCategory(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="mission-grid">
          {visibleGames.map((game) => (
            <MissionCard
              game={game}
              gameProgress={progress.games?.[game.id]}
              key={game.id}
              onStart={(gameId) => {
                const selected = getGameById(gameId)
                if (selected?.component) setActiveGameId(gameId)
              }}
            />
          ))}
        </div>
      </div>
    </main>
  )
}
