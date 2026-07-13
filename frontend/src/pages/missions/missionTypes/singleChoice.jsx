import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'single_choice',
  labelKey: 'singleChoice',
  example: (text) => ({
    id: 'test-single', type: 'single_choice', title: text('Sichere Dateneingabe', 'Safe data input'),
    description: text('Erkenne eine sichere Eingabe für ein Enterprise-AI-Tool.', 'Identify safe input for an enterprise AI tool.'),
    max_points: 30, completed: false, score: null,
    content: { question: text('Welche Daten eignen sich am besten?', 'Which data is most suitable?'), options: [text('Anonymisierte Summen', 'Anonymized totals'), text('Personenbezogene Gehaltsdaten', 'Personal salary data'), text('Kundenpasswörter', 'Customer passwords')] },
    test_solution: {
      correct_indices: [0],
      micro_learning: text('Bevor Daten in ein AI-Tool eingegeben werden, zählt nicht nur der Zweck, sondern auch der Detailgrad. Je weniger eine Eingabe auf einzelne Personen, Kunden oder Verträge zurückführbar ist, desto geringer ist das Risiko.', 'Before entering data into an AI tool, both the purpose and the level of detail matter. The less an input can be traced back to individual people, customers, or contracts, the lower the risk.'),
    },
  }),
})
