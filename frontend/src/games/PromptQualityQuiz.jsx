import { useMemo, useState } from 'react'

const questions = [
  {
    situation: 'Du musst einen Monatsabschlussbericht zusammenfassen.',
    options: [
      'Mach das besser.',
      'Fasse diesen Monatsabschlussbericht in fuenf Bullet Points zusammen, hebe Abweichungen zum Vormonat hervor und nenne moegliche Ursachen.',
      'Schreibe irgendwas fuer das Management.',
    ],
    correctIndex: 1,
    feedback: 'Ein guter Prompt nennt Aufgabe, Umfang, Vergleichsfokus und erwartetes Format.',
  },
  {
    situation: 'Du willst Auffaelligkeiten in Buchungsdaten finden.',
    options: [
      'Analysiere die Daten und sag mir, was komisch ist.',
      'Pruefe die Buchungen aus Q2 auf ungewoehnliche Betraege, seltene Kostenstellen und Ausreisser je Kreditor. Gib eine Tabelle mit Buchungs-ID, Grund und Prioritaet aus.',
      'Findest du Fehler?',
    ],
    correctIndex: 1,
    feedback: 'Klare Datenbasis, Suchkriterien und Ausgabeformat machen die Analyse nutzbar.',
  },
  {
    situation: 'Du brauchst eine Management-Zusammenfassung.',
    options: [
      'Schreibe eine kurze Executive Summary fuer CFOs, maximal 120 Woerter, mit Fokus auf EBITDA-Abweichung, Cashflow-Risiken und naechste Entscheidungen.',
      'Kurz zusammenfassen.',
      'Bitte nett formulieren.',
    ],
    correctIndex: 0,
    feedback: 'Zielgruppe, Laenge, Ton und Fokus gehoeren in den Prompt.',
  },
  {
    situation: 'Du willst eine AI-Antwort fuer ein Reporting-Deck pruefen.',
    options: [
      'Ist das richtig?',
      'Vergleiche die Antwort mit den angegebenen Zahlen, markiere Annahmen, nenne fehlende Quellen und schlage drei Validierungsfragen vor.',
      'Mach es genauer.',
    ],
    correctIndex: 1,
    feedback: 'Finance-Arbeit braucht Validierung, Quellenklarheit und konkrete Prueffragen.',
  },
]

export default function PromptQualityQuiz({ game, gameProgress, onComplete, onBack, onProgress }) {
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)
  const score = useMemo(
    () => questions.filter((question, index) => answers[index] === question.correctIndex).length,
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
        {questions.map((question, index) => (
          <article className="question-card" key={question.situation}>
            <h2>{index + 1}. {question.situation}</h2>
            <div className="option-list">
              {question.options.map((option, optionIndex) => (
                <label
                  className={`quiz-option ${answers[index] === optionIndex ? 'selected' : ''}`}
                  key={option}
                >
                  <input
                    checked={answers[index] === optionIndex}
                    disabled={submitted}
                    name={`question-${index}`}
                    onChange={() => setAnswers((current) => ({ ...current, [index]: optionIndex }))}
                    type="radio"
                  />
                  <span>{option}</span>
                </label>
              ))}
            </div>
            {submitted && (
              <p className={answers[index] === question.correctIndex ? 'feedback good' : 'feedback'}>
                {question.feedback}
              </p>
            )}
          </article>
        ))}
      </div>

      {submitted ? (
        <div className="result-box">
          <strong>{score} von {questions.length} richtig</strong>
          <p>
            {score >= game.passScore
              ? `Mission bestanden. Dein bester Score wird gespeichert (${gameProgress?.bestScore || score}/${game.maxScore}).`
              : `Noch nicht bestanden. Fuer Completion brauchst du ${game.passScore} richtige Antworten.`}
          </p>
          <div className="button-row">
            <button className="secondary-action" type="button" onClick={onBack}>Zurueck zu Missions</button>
            <button className="action-button inline-action" type="button" onClick={onProgress}>Zu Progress</button>
          </div>
        </div>
      ) : (
        <button
          className="action-button inline-action"
          disabled={Object.keys(answers).length < questions.length}
          onClick={handleSubmit}
          type="button"
        >
          Quiz abschliessen
        </button>
      )}
    </section>
  )
}
