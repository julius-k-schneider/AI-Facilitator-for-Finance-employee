import {
  IconLayoutDashboard,
  IconMessageChatbot,
  IconSchool,
  IconTargetArrow,
  IconDeviceGamepad2,
  IconTrophy,
  IconUserCircle,
  IconUserCog,
} from '@tabler/icons-react'
import { PERMISSIONS } from './auth/permissions'

export const NAV_ITEMS = [
  { value: 'home', path: '/', label: 'Home', labelKey: 'nav.home', icon: IconLayoutDashboard },
  { value: 'basics', path: '/basics', label: 'Basics', labelKey: 'nav.basics', icon: IconSchool },
  { value: 'missions', path: '/missions', label: 'Missions', labelKey: 'nav.missions', icon: IconTargetArrow, requiresOnboarding: true },
  { value: 'training', path: '/training', label: 'Training', labelKey: 'nav.training', icon: IconDeviceGamepad2, requiresOnboarding: true },
  { value: 'agent', path: '/agent', label: 'Your Agent', labelKey: 'nav.agent', icon: IconMessageChatbot, requiresOnboarding: true },
  { value: 'leaderboard', path: '/leaderboard', label: 'Leaderboard', labelKey: 'nav.leaderboard', icon: IconTrophy },
  {
    value: 'user-management',
    path: '/user-management',
    label: 'User management',
    labelKey: 'nav.userManagement',
    icon: IconUserCog,
    permission: PERMISSIONS.MANAGE_USERS,
  },
]

export const PROFILE_ITEM = {
  value: 'profile',
  path: '/profile',
  label: 'Profile',
  labelKey: 'nav.profile',
  icon: IconUserCircle,
}

const ALL_ITEMS = [...NAV_ITEMS, PROFILE_ITEM]

// A section owns its sub-routes: /missions/42 still belongs to "Missions", and
// /basics/onboarding still belongs to "Basics". Only "/" has to match exactly,
// otherwise it would swallow every other path.
export function isNavItemActive(item, pathname) {
  if (item.path === '/') return pathname === '/'
  return pathname === item.path || pathname.startsWith(`${item.path}/`)
}

export function navLabelKeyForPath(pathname) {
  const match = ALL_ITEMS
    .filter((item) => isNavItemActive(item, pathname))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return match?.labelKey || ''
}

export const NAV_LABEL_KEYS = Object.fromEntries(
  ALL_ITEMS.map((item) => [item.path, item.labelKey]),
)
