import {
  IconLayoutDashboard,
  IconSchool,
  IconBooks,
  IconTrophy,
  IconUserCircle,
} from '@tabler/icons-react'

// Zentrale Navigations-Definition – wird von Sidebar und Router genutzt.
// labelKey verweist auf einen i18n-Schlüssel (siehe src/i18n/locales).
export const NAV_ITEMS = [
  { value: 'home', labelKey: 'nav.home', icon: IconLayoutDashboard },
  { value: 'grundlagen', labelKey: 'nav.grundlagen', icon: IconSchool },
  { value: 'bibliothek', labelKey: 'nav.bibliothek', icon: IconBooks },
  { value: 'leaderboard', labelKey: 'nav.leaderboard', icon: IconTrophy },
]

// Profil ist nicht Teil der Hauptnavigation, sondern über die User-Box erreichbar.
export const PROFILE_ITEM = { value: 'profile', labelKey: 'nav.profile', icon: IconUserCircle }

// value -> i18n-Schlüssel, z. B. für die Topbar-Überschrift.
export const NAV_LABEL_KEYS = Object.fromEntries(
  [...NAV_ITEMS, PROFILE_ITEM].map((item) => [item.value, item.labelKey]),
)
