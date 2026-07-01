import { choiceDefinition } from './shared'

export default choiceDefinition({
  id: 'compliance_decision', labelKey: 'complianceDecision',
  example: (text) => ({
    id: 'test-compliance', type: 'compliance_decision', title: text('Compliance-Entscheidung', 'Compliance decision'),
    description: text('Bewerte eine typische Datennutzung.', 'Assess a typical use of data.'), max_points: 30, completed: false, score: null,
    content: { question: text('Dürfen offene Marktdaten im freigegebenen Tool zusammengefasst werden?', 'May public market data be summarized in an approved tool?'), options: [text('Ja, grundsätzlich schon', 'Yes, generally'), text('Nein, niemals', 'No, never')] },
    test_solution: {
      correct_indices: [0],
      micro_learning: text('Bei Daten für AI-Tools lohnt sich zuerst die Frage: Sind die Informationen öffentlich, intern, vertraulich oder personenbezogen? Öffentliche Daten können oft einfacher genutzt werden, während vertrauliche Inhalte Schutzmaßnahmen und klare Freigaben brauchen. Diese Einordnung verhindert, dass Bequemlichkeit wichtiger wird als Verantwortung.', 'When using data with AI tools, first ask whether the information is public, internal, confidential, or personal. Public data can often be used more easily, while confidential content needs safeguards and clear approval. This classification keeps convenience from becoming more important than responsibility.'),
    },
  }),
})
