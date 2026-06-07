import LeaderboardTable from '../components/LeaderboardTable'
import { useLeaderboard } from '../hooks/useLeaderboard'

export default function Leaderboard({ user, progressData }) {
  const rows = useLeaderboard(user, progressData.stats)

  return (
    <main className="leaderboard">
      <div className="page-container wide-container">
        <div className="page-header">
          <div>
            <p className="eyebrow">Team ranking</p>
            <h1>Leaderboard</h1>
            <p>Dein Rang wird aus Punkten und abgeschlossenen Missions berechnet.</p>
          </div>
        </div>
        <LeaderboardTable rows={rows} />
      </div>
    </main>
  )
}
