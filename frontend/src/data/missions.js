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

export function getMissionById(missionId) {
  return MISSIONS.find((mission) => mission.id === missionId)
}
