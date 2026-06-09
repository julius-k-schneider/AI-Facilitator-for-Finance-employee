import {
  IconLayoutDashboard,
  IconRoute,
  IconTargetArrow,
  IconChartArcs,
  IconTrophy,
  IconBooks,
  IconUserCircle,
} from '@tabler/icons-react'

// Zentrale Navigations-Definition – wird von Sidebar und Router genutzt.
export const NAV_ITEMS = [
  { value: 'home', label: 'Home', hint: 'Übersicht', icon: IconLayoutDashboard },
  { value: 'learning-path', label: 'Learning Path', hint: 'Deine Lernroute', icon: IconRoute },
  { value: 'missions', label: 'Missions', hint: 'Aufgaben & Punkte', icon: IconTargetArrow },
  { value: 'progress', label: 'Progress', hint: 'Dein Fortschritt', icon: IconChartArcs },
  { value: 'leaderboard', label: 'Leaderboard', hint: 'Ranglisten', icon: IconTrophy },
  { value: 'resources', label: 'Resources', hint: 'Materialien', icon: IconBooks },
  { value: 'profile', label: 'Profile', hint: 'Dein Konto', icon: IconUserCircle },
]

export const NAV_LABELS = Object.fromEntries(
  NAV_ITEMS.map((item) => [item.value, item.label]),
)
