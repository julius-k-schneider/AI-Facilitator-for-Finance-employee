import { useMemo, useState } from 'react'

const scenarios = [
  {
    text: 'Ein Mitarbeiter kopiert personenbezogene Gehaltsdaten in ein oeffentliches AI-Tool.',
    answer: 'not-allowed',
    feedback: 'Personenbezogene und vertrauliche Daten duerfen nicht in oeffentliche AI-Tools kopiert werden.',
  },
  {
    text: 'Ein Controller nutzt anonymisierte Kostenstellendaten zur Trendanalyse mit einem freigegebenen Enterprise-AI-Tool.',
    answer: 'allowed',
    feedback: 'Anonymisierte Daten in einem freigegebenen Enterprise-Tool sind fuer solche Analysen geeignet.',
  },
  {
    text: 'Eine Mitarbeiterin moechte interne Buchungsdaten ohne Personenbezug in ein zugelassenes internes AI-Tool hochladen.',
    answer: 'allowed',
    feedback: 'Ohne Personenbezug und mit zugelassenem Tool ist die Nutzung grundsaetzlich erlaubt.',
  },
  {
    text: 'Ein Monatsbericht mit vertraulichen Kommentaren wird in ein externes Tool eingefuegt.',
    answer: 'not-allowed',
    feedback: 'Vertrauliche interne Kommentare gehoeren nicht in externe Tools. Erst klaeren, anonymisieren und freigegebene Tools nutzen.',
  },
]

const choices = [
  { id: 'allowed', label: 'Allowed' },
  { id: 'not-allowed', label: 'Not allowed' },
  { id: 'anonymized', label: 'Only with anonymized data' },
]

export default function ComplianceCheckChallenge({ game, gameProgress, onComplete, onBack, onProgress }) {
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const score = useMemo(
    () => scenarios.filter((scenario, index) => answers[index] === scenario.answer).length,
    [answers],
  )

  const handleSubmit = () => {
    setSubmitted(true)
    onComplete(game.id, score)
  }

  return (
    <section className="game-panel">
      <div className="game-header">
        <button className="text-action" type="button" onClick={onBack}>
          Back to Missions
        </button>
        <span>{game.estimatedTime}</span>
      </div>
      <h1>{game.title}</h1>
      <p>{game.description}</p>

      <div className="question-list">
        {scenarios.map((scenario, index) => (
          <article className="question-card" key={scenario.text}>
            <h2>{index + 1}. {scenario.text}</h2>
            <div className="decision-row">
              {choices.map((choice) => (
                <button
                  className={answers[index] === choice.id ? 'decision-button selected' : 'decision-button'}
                  disabled={submitted}
                  key={choice.id}
                  onClick={() => setAnswers((current) => ({ ...current, [index]: choice.id }))}
                  type="button"
                >
                  {choice.label}
                </button>
              ))}
            </div>
            {submitted && (
              <p className={answers[index] === scenario.answer ? 'feedback good' : 'feedback'}>
                {scenario.feedback}
              </p>
            )}
          </article>
        ))}
      </div>

      {submitted ? (
        <div className="result-box">
          <strong>{score} von {scenarios.length} richtig</strong>
          <p>
            {score >= game.passScore
              ? `Challenge bestanden. Dein bester Score wird gespeichert (${gameProgress?.bestScore || score}/${game.maxScore}).`
              : `Noch nicht bestanden. Fuer Completion brauchst du ${game.passScore} richtige Entscheidungen.`}
          </p>
          <div className="button-row">
            <button className="secondary-action" type="button" onClick={onBack}>Zurueck zu Missions</button>
            <button className="action-button inline-action" type="button" onClick={onProgress}>Zu Progress</button>
          </div>
        </div>
      ) : (
        <button
          className="action-button inline-action"
          disabled={Object.keys(answers).length < scenarios.length}
          onClick={handleSubmit}
          type="button"
        >
          Challenge abschliessen
        </button>
      )}
    </section>
  )
}
