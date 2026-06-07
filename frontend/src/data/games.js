export const gameCategories = [
  { id: 'all', label: 'All' },
  { id: 'ai-basics', label: 'AI Basics' },
  { id: 'prompting', label: 'Prompting' },
  { id: 'data-analysis', label: 'Data Analysis' },
  { id: 'compliance', label: 'Compliance' },
]

export const games = [
  {
    id: 'prompt-quality-quiz',
    title: 'Prompt Quality Quiz',
    description: 'Trainiere, gute Finance-Prompts von schwachen Prompts zu unterscheiden.',
    category: 'prompting',
    difficulty: 'Beginner',
    estimatedTime: '6 min',
    points: 120,
    passScore: 3,
    maxScore: 4,
    learningObjectives: [
      'Prompts mit Kontext, Ziel und Ausgabeformat formulieren',
      'Finance-Situationen klar in AI-Aufgaben übersetzen',
      'Management-orientierte Zusammenfassungen anfordern',
    ],
    tags: ['Prompting', 'Reports', 'Analysis'],
    component: 'PromptQualityQuiz',
  },
  {
    id: 'compliance-check-challenge',
    title: 'Compliance Check Challenge',
    description: 'Entscheide, wann AI-Nutzung mit Unternehmensdaten erlaubt ist.',
    category: 'compliance',
    difficulty: 'Beginner',
    estimatedTime: '5 min',
    points: 100,
    passScore: 3,
    maxScore: 4,
    learningObjectives: [
      'Sensible Daten in AI-Szenarien erkennen',
      'Freigegebene Enterprise-AI-Tools korrekt einordnen',
      'Anonymisierung als Schutzmassnahme anwenden',
    ],
    tags: ['Responsible AI', 'Compliance', 'Data Protection'],
    component: 'ComplianceCheckChallenge',
  },
]

export function getGameById(gameId) {
  return games.find((game) => game.id === gameId)
}

export function getPlayableGames() {
  return games.filter((game) => Boolean(game.component))
}
