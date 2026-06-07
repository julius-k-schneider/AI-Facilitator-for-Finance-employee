import Badge from './Badge'

export default function ResourceCard({ resource }) {
  return (
    <article className="resource-card">
      <Badge>{resource.category}</Badge>
      <h2>{resource.title}</h2>
      <p>{resource.description}</p>
      <div className="resource-footer">
        <span>{resource.readingTime}</span>
        <a className="secondary-action" href={resource.url}>
          Read
        </a>
      </div>
    </article>
  )
}
