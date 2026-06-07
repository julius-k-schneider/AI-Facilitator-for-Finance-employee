import Badge from './Badge'

export default function MissionCard({ game, gameProgress, onStart }) {
  const isCompleted = Boolean(gameProgress?.completed)

  return (
    <article className="mission-card">
      <div className="mission-card-top">
        <Badge tone={isCompleted ? 'success' : 'default'}>{isCompleted ? 'Completed' : 'Not started'}</Badge>
        <span>{game.points} pts</span>
      </div>
      <h2>{game.title}</h2>
      <p>{game.description}</p>
      <div className="mission-meta">
        <span>{game.difficulty}</span>
        <span>{game.estimatedTime}</span>
        <span>{game.category}</span>
      </div>
      <div className="tag-row">
        {game.tags.map((tag) => (
          <Badge key={tag}>{tag}</Badge>
        ))}
      </div>
      <button className="secondary-action" type="button" onClick={() => onStart(game.id)}>
        {isCompleted ? 'Replay' : 'Start'}
      </button>
    </article>
  )
}
