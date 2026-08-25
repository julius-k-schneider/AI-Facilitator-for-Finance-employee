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

export const NAV_LABEL_KEYS = Object.fromEntries(
  [...NAV_ITEMS, PROFILE_ITEM].map((item) => [item.path, item.labelKey]),
)
