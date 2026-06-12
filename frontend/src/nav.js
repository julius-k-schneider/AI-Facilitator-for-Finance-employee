import {
  IconLayoutDashboard,
  IconSchool,
  IconBooks,
  IconTrophy,
  IconUserCircle,
} from '@tabler/icons-react'

// Zentrale Navigations-Definition – wird von Sidebar und Router genutzt.
export const NAV_ITEMS = [
  { value: 'home', label: 'Home', hint: 'Übersicht', icon: IconLayoutDashboard },
  { value: 'grundlagen', label: 'Grundlagen', hint: 'AI-Basics', icon: IconSchool },
  { value: 'bibliothek', label: 'Bibliothek', hint: 'Materialien', icon: IconBooks },
  { value: 'leaderboard', label: 'Leaderboard', hint: 'Ranglisten', icon: IconTrophy },
]

// Profil ist nicht Teil der Hauptnavigation, sondern über die User-Box erreichbar.
export const PROFILE_ITEM = { value: 'profile', label: 'Profile', hint: 'Dein Konto', icon: IconUserCircle }

export const NAV_LABELS = Object.fromEntries(
  [...NAV_ITEMS, PROFILE_ITEM].map((item) => [item.value, item.label]),
)
