import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'prompt_selection', labelKey: 'promptSelection',
  example: (text) => ({
    id: 'test-prompt', type: 'prompt_selection', title: text('Bester Analyse-Prompt', 'Best analysis prompt'),
    description: text('Wähle den präzisesten Arbeitsauftrag.', 'Choose the most precise instruction.'), max_points: 30, completed: false, score: null,
    content: { question: text('Welcher Prompt liefert das nützlichste Ergebnis?', 'Which prompt produces the most useful result?'), options: [text('Analysiere das.', 'Analyze this.'), text('Vergleiche Plan und Ist und nenne die fünf größten Abweichungen als Tabelle.', 'Compare plan and actuals and list the five largest variances in a table.')] },
    test_solution: {
      correct_indices: [1],
      micro_learning: text('Bei Analyseaufgaben hilft es, die gewünschte Denkrichtung vorzugeben: Was soll verglichen werden, welche Kriterien zählen, und in welcher Form soll die Antwort kommen? So wird aus einer offenen Bitte ein prüfbarer Auftrag.', 'For analysis tasks, it helps to define the direction of thinking: what should be compared, which criteria matter, and what format should the answer use? This turns an open request into a checkable task.'),
    },
  }),
})
