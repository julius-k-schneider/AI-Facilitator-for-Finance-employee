import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'prompt_selection', labelKey: 'promptSelection',
  example: (text) => ({
    id: 'test-prompt', type: 'prompt_selection', title: text('Bester Analyse-Prompt', 'Best analysis prompt'),
    description: text('Wähle den präzisesten Arbeitsauftrag.', 'Choose the most precise instruction.'), max_points: 30, completed: false, score: null,
    content: { question: text('Welcher Prompt liefert das nützlichste Ergebnis?', 'Which prompt produces the most useful result?'), options: [text('Analysiere das.', 'Analyze this.'), text('Vergleiche Plan und Ist und nenne die fünf größten Abweichungen als Tabelle.', 'Compare plan and actuals and list the five largest variances in a table.')] },
    test_solution: { correct_indices: [1] },
  }),
})
