import { useMemo } from 'react'
import {
  canCreateContent,
  canManageUsers,
  getRolePermissions,
  getUserRole,
  hasPermission,
  hasRole,
} from '../auth/permissions'

export function usePermissions(user) {
  return useMemo(() => {
    const role = getUserRole(user)

    return {
      role,
      permissions: getRolePermissions(role),
      hasRole: (value) => hasRole(user, value),
      hasPermission: (value) => hasPermission(user, value),
      canManageUsers: canManageUsers(user),
      canCreateContent: canCreateContent(user),
    }
  }, [user])
}
