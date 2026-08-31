export const ROLES = {
  USER: 'user',
  CONTROLLER: 'controller',
  ACCOUNTANT: 'accountant',
  CONTENT_CREATOR: 'content_creator',
  ADMIN: 'admin',
}

export const ROLE_LABELS = {
  [ROLES.USER]: 'User',
  [ROLES.CONTROLLER]: 'Controller',
  [ROLES.ACCOUNTANT]: 'Accountant',
  [ROLES.CONTENT_CREATOR]: 'Content Creator',
  [ROLES.ADMIN]: 'Admin',
}

export const PERMISSIONS = {
  PLAY_MISSIONS: 'missions:play',
  CREATE_CONTENT: 'content:create',
  MANAGE_USERS: 'users:manage',
  DELETE_USERS: 'users:delete',
  ASSIGN_ROLES: 'roles:assign',
}

const ROLE_PERMISSIONS = {
  [ROLES.USER]: [PERMISSIONS.PLAY_MISSIONS],
  [ROLES.CONTROLLER]: [PERMISSIONS.PLAY_MISSIONS],
  [ROLES.ACCOUNTANT]: [PERMISSIONS.PLAY_MISSIONS],
  [ROLES.CONTENT_CREATOR]: [PERMISSIONS.PLAY_MISSIONS, PERMISSIONS.CREATE_CONTENT],
  [ROLES.ADMIN]: [
    PERMISSIONS.PLAY_MISSIONS,
    PERMISSIONS.CREATE_CONTENT,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.DELETE_USERS,
    PERMISSIONS.ASSIGN_ROLES,
  ],
}

function getUserRole(user) {
  return user?.role && ROLE_PERMISSIONS[user.role] ? user.role : ROLES.USER
}

function getRolePermissions(role) {
  return ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS[ROLES.USER]
}

export function getAvailableRoles() {
  return Object.values(ROLES)
}

export function hasPermission(user, permission) {
  return getRolePermissions(getUserRole(user)).includes(permission)
}
