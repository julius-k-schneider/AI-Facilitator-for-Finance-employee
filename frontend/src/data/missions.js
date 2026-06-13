export const MISSIONS = [
  {
    id: 'prompt-quality-quiz',
    title: 'Prompt Quality Quiz',
    description: 'Erkenne starke Prompts fuer typische Finance-Aufgaben.',
    category: 'Prompting',
    difficulty: 'Easy',
    estimatedTime: '5 Min.',
    maxPoints: 90,
  },
  {
    id: 'compliance-check-challenge',
    title: 'Compliance Check Challenge',
    description: 'Entscheide, wann AI-Nutzung mit Unternehmensdaten verantwortungsvoll ist.',
    category: 'Compliance',
    difficulty: 'Medium',
    estimatedTime: '7 Min.',
    maxPoints: 120,
  },
]

export const LERNCHECKS = [
  {
    id: 'lerncheck-halluzinationen',
    title: 'Lerncheck: Halluzinationen erkennen',
    description: 'Lies den Text und beantworte die Fragen zum Thema AI-Halluzinationen.',
    category: 'AI Grundlagen',
    difficulty: 'Medium',
    estimatedTime: '8 Min.',
    maxPoints: 100,
  },
]

export function getMissionById(missionId) {
  return MISSIONS.find((mission) => mission.id === missionId)
}

export function getLerncheckById(lerncheckId) {
  return LERNCHECKS.find((lerncheck) => lerncheck.id === lerncheckId)
}