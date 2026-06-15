import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'compliance_decision', labelKey: 'complianceDecision',
  example: (text) => ({
    id: 'test-compliance', type: 'compliance_decision', title: text('Compliance-Entscheidung', 'Compliance decision'),
    description: text('Bewerte eine typische Datennutzung.', 'Assess a typical use of data.'), max_points: 30, completed: false, score: null,
    content: { question: text('Dürfen offene Marktdaten im freigegebenen Tool zusammengefasst werden?', 'May public market data be summarized in an approved tool?'), options: [text('Ja, grundsätzlich schon', 'Yes, generally'), text('Nein, niemals', 'No, never')] },
    test_solution: { correct_indices: [0] },
  }),
})
