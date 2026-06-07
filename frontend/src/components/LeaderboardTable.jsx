export default function LeaderboardTable({ rows }) {
  return (
    <div className="table-wrap">
      <table className="leaderboard-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Role</th>
            <th>Points</th>
            <th>Missions</th>
            <th>Level</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className={row.isCurrentUser ? 'current-user-row' : undefined}>
              <td>#{row.rank}</td>
              <td>{row.name}</td>
              <td>{row.role}</td>
              <td>{row.points}</td>
              <td>{row.completedMissions}</td>
              <td>{row.level}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
