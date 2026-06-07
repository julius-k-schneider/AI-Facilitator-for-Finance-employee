export const resources = [
  {
    id: 'prompting-checklist-finance',
    title: 'Prompting Checklist for Finance Reports',
    description: 'Eine kompakte Checkliste fuer Kontext, Rolle, Ziel, Datenbasis und Ausgabeformat.',
    category: 'Prompting Guides',
    readingTime: '4 min',
    url: '#',
  },
  {
    id: 'ask-ai-data-insights',
    title: 'How to Ask AI for Data Insights',
    description: 'Beispiele fuer gute Analysefragen bei Abweichungen, Trends und Kostenstellen.',
    category: 'Finance AI Use Cases',
    readingTime: '6 min',
    url: '#',
  },
  {
    id: 'responsible-ai-basics',
    title: 'Responsible AI Basics',
    description: 'Grundregeln fuer Datenschutz, vertrauliche Informationen und sichere Tool-Nutzung.',
    category: 'Compliance & Responsible AI',
    readingTime: '5 min',
    url: '#',
  },
  {
    id: 'ai-accounting-controlling',
    title: 'AI Use Cases in Accounting and Controlling',
    description: 'Ideen fuer Monatsabschluss, Kommentierung, Forecasting und Plausibilisierung.',
    category: 'Finance AI Use Cases',
    readingTime: '7 min',
    url: '#',
  },
  {
    id: 'internal-tool-placeholder',
    title: 'Lufthansa Enterprise AI Tools',
    description: 'Platzhalter fuer freigegebene interne Tools, Guidelines und Dokumentationen.',
    category: 'Lufthansa/Internal Tools Placeholder',
    readingTime: '3 min',
    url: '#',
  },
]

export const resourceCategories = ['All', ...new Set(resources.map((resource) => resource.category))]
