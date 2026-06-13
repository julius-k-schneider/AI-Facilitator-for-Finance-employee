import {
  IconLayoutDashboard,
  IconSchool,
  IconTargetArrow,
  IconTrophy,
  IconUserCircle,
  IconUserCog,
} from '@tabler/icons-react'
import { PERMISSIONS } from './auth/permissions'

export const NAV_ITEMS = [
  { value: 'home', label: 'Home', labelKey: 'nav.home', icon: IconLayoutDashboard },
  { value: 'grundlagen', label: 'Grundlagen', labelKey: 'nav.grundlagen', icon: IconSchool },
  { value: 'missions', label: 'Missions', labelKey: 'nav.missions', icon: IconTargetArrow, requiresOnboarding: true },
  { value: 'leaderboard', label: 'Leaderboard', labelKey: 'nav.leaderboard', icon: IconTrophy },
  {
    value: 'user-management',
    label: 'Nutzerverwaltung',
    labelKey: 'nav.userManagement',
    icon: IconUserCog,
    permission: PERMISSIONS.MANAGE_USERS,
  },
]

export const PROFILE_ITEM = {
  value: 'profile',
  label: 'Profil',
  labelKey: 'nav.profile',
  icon: IconUserCircle,
}

export const NAV_LABEL_KEYS = Object.fromEntries(
  [...NAV_ITEMS, PROFILE_ITEM].map((item) => [item.value, item.labelKey]),
)
