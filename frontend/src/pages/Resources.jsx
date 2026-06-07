import { useMemo, useState } from 'react'
import ResourceCard from '../components/ResourceCard'
import { resourceCategories, resources } from '../data/resources'

export default function Resources() {
  const [category, setCategory] = useState('All')
  const visibleResources = useMemo(
    () => resources.filter((resource) => category === 'All' || resource.category === category),
    [category],
  )

  return (
    <main className="resources">
      <div className="page-container wide-container">
        <div className="page-header">
          <div>
            <p className="eyebrow">Learning materials</p>
            <h1>Resources</h1>
            <p>Kuratierte Materialien fuer Prompting, AI Use Cases, Compliance und interne Tool-Guides.</p>
          </div>
        </div>

        <div className="filter-row">
          {resourceCategories.map((item) => (
            <button
              className={category === item ? 'filter-button active' : 'filter-button'}
              key={item}
              onClick={() => setCategory(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>

        <div className="resource-grid">
          {visibleResources.map((resource) => (
            <ResourceCard key={resource.id} resource={resource} />
          ))}
        </div>
      </div>
    </main>
  )
}
