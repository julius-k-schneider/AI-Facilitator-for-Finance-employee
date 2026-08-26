import { useEffect, useMemo, useState } from 'react'
import {
  Avatar,
  Badge,
  Box,
  Button,
  Checkbox,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconSearch, IconShield, IconTrash, IconUserCog, IconUsers } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import ConfirmModal from '../components/ConfirmModal'
import { RowsSkeleton } from '../components/Skeletons'
import { notifyError, notifySuccess } from '../services/notify'
import { getUserId } from '../services/progressService'
import { ROLE_LABELS, ROLES, getAvailableRoles } from '../auth/permissions'
import {
  deleteUser,
  getAllRegisteredUsers,
  getSkillProgressionSettings,
  updateSkillProgressionSettings,
  updateUserRole,
  updateUserSkillLevel,
} from '../services/userService'

function displayName(user) {
  const name = `${user.first_name || ''} ${user.last_name || ''}`.trim()
  return name || user.username || user.email
}

function initials(user) {
  const first = user.first_name?.[0] || user.username?.[0] || user.email?.[0] || '?'
  const second = user.last_name?.[0] || ''
  return `${first}${second}`.toUpperCase()
}

function roleColor(role) {
  if (role === ROLES.ADMIN) return 'accent'
  if (role === ROLES.CONTENT_CREATOR) return 'brand'
  return 'secondary'
}

function isLastAdmin(users, userId) {
  const admins = users.filter((user) => user.role === ROLES.ADMIN)
  return admins.length === 1 && getUserId(admins[0]) === String(userId)
}

const roleOptions = getAvailableRoles().map((role) => ({
  value: role,
  label: ROLE_LABELS[role],
}))
const skillOptions = ['beginner', 'advanced', 'pro'].map((level) => ({ value: level, label: level }))

export default function UserManagement({ currentUser, onCurrentUserUpdate }) {
  const { t } = useTranslation()
  const [users, setUsers] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [settings, setSettings] = useState(null)
  const [savingSettings, setSavingSettings] = useState(false)
  const currentUserId = getUserId(currentUser)

  useEffect(() => {
    let isActive = true

    Promise.all([getAllRegisteredUsers(), getSkillProgressionSettings()])
      .then(([nextUsers, nextSettings]) => {
        if (!isActive) return
        setUsers(nextUsers)
        setSettings(nextSettings)
      })
      .catch((error) => {
        if (!isActive) return
        notifyError(error.message || t('userManagement.errors.loadFailed'))
      })
      .finally(() => {
        if (isActive) setLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [t])

  const filteredUsers = useMemo(() => {
    const needle = query.trim().toLowerCase()
    if (!needle) return users

    return users.filter((user) => {
      const roleLabel = ROLE_LABELS[user.role || ROLES.USER] || user.role
      return [displayName(user), user.username, user.email, roleLabel, user.role]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(needle))
    })
  }, [query, users])

  const handleRoleChange = async (target, role) => {
    if (!role || role === target.role) return
    if (isLastAdmin(users, target.id) && role !== ROLES.ADMIN) {
      notifyError(t('userManagement.errors.lastAdminDowngrade'))
      return
    }

    try {
      const updatedUser = await updateUserRole(target.id, role)
      setUsers((current) => current.map((user) => (user.id === updatedUser.id ? updatedUser : user)))
      if (String(updatedUser.id) === currentUserId) {
        onCurrentUserUpdate(updatedUser)
      }
      notifySuccess(t('userManagement.success.roleUpdated'))
    } catch (error) {
      notifyError(error.message || t('userManagement.errors.roleUpdateFailed'))
    }
  }

  const handleSkillChange = async (target, skillLevel) => {
    if (!skillLevel || skillLevel === target.skill_level) return
    try {
      const updatedUser = await updateUserSkillLevel(target.id, skillLevel)
      setUsers((current) => current.map((user) => (user.id === updatedUser.id ? updatedUser : user)))
      if (String(updatedUser.id) === currentUserId) onCurrentUserUpdate(updatedUser)
      notifySuccess(t('userManagement.success.skillUpdated'))
    } catch (error) {
      notifyError(error.message || t('userManagement.errors.skillUpdateFailed'))
    }
  }

  const saveSettings = async () => {
    if (!settings) return
    setSavingSettings(true)
    try {
      const updated = await updateSkillProgressionSettings(settings)
      setSettings(updated)
      notifySuccess(t('userManagement.success.settingsUpdated'))
    } catch (error) {
      notifyError(error.message || t('userManagement.errors.settingsUpdateFailed'))
    } finally {
      setSavingSettings(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (String(deleteTarget.id) === currentUserId) {
      notifyError(t('userManagement.errors.selfDelete'))
      setDeleteTarget(null)
      return
    }
    if (isLastAdmin(users, deleteTarget.id)) {
      notifyError(t('userManagement.errors.lastAdminDelete'))
      setDeleteTarget(null)
      return
    }

    setDeleting(true)
    try {
      await deleteUser(deleteTarget.id)
      setUsers((current) => current.filter((user) => user.id !== deleteTarget.id))
      setDeleteTarget(null)
      notifySuccess(t('userManagement.success.deleted'))
    } catch (error) {
      notifyError(error.message || t('userManagement.errors.deleteFailed'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Paper
        radius="xl"
        p={{ base: 'xl', md: 38 }}
        mb="xl"
        style={{
          position: 'relative',
          overflow: 'hidden',
          background:
            'linear-gradient(135deg, var(--mantine-color-secondary-7) 0%, var(--mantine-color-secondary-6) 62%, var(--mantine-color-brand-7) 135%)',
          color: '#fff',
        }}
      >
        <Box
          style={{
            position: 'absolute',
            top: '-45%',
            right: '-8%',
            width: 320,
            height: 320,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(var(--gold-rgb),0.22) 0%, rgba(var(--gold-rgb),0) 68%)',
          }}
        />
        <Group gap="lg" style={{ position: 'relative' }} align="flex-start">
          <ThemeIcon size={54} radius="md" variant="light" color="accent">
            <IconUserCog size={30} stroke={1.7} />
          </ThemeIcon>
          <Stack gap={6}>
            <Title order={1} fz={{ base: 28, md: 36 }}>
              {t('userManagement.title')}
            </Title>
            <Text c="rgba(255,255,255,0.78)" maw={680}>
              {t('userManagement.subtitle')}
            </Text>
          </Stack>
        </Group>
      </Paper>

      {settings && <Paper withBorder radius="lg" bg="white" p="lg" mb="xl">
        <Title order={2} fz="lg" mb="xs">{t('userManagement.progressionSettings.title')}</Title>
        <Text c="dimmed" fz="sm" mb="md">{t('userManagement.progressionSettings.description')}</Text>
        <Group align="flex-end">
          <Checkbox
            checked={settings.automatic_progression_enabled}
            onChange={(event) => setSettings((current) => ({ ...current, automatic_progression_enabled: event.currentTarget.checked }))}
            label={t('userManagement.progressionSettings.enabled')}
            mb={8}
          />
          {['evaluation_window', 'minimum_missions', 'promotion_threshold', 'demotion_threshold'].map((field) => <NumberInput
            key={field}
            label={t(`userManagement.progressionSettings.${field}`)}
            value={settings[field]}
            min={field.includes('threshold') ? 0 : 1}
            max={field.includes('threshold') ? 100 : undefined}
            onChange={(value) => setSettings((current) => ({ ...current, [field]: Number(value) }))}
            w={180}
          />)}
          <Button loading={savingSettings} onClick={saveSettings}>{t('userManagement.progressionSettings.save')}</Button>
        </Group>
      </Paper>}

      <Paper withBorder radius="lg" bg="white" style={{ overflow: 'hidden' }}>
        <Group justify="space-between" p="lg" style={{ borderBottom: '1px solid var(--line)' }}>
          <Group gap="sm">
            <ThemeIcon size={40} radius="md" variant="light" color="brand">
              <IconUsers size={22} stroke={1.7} />
            </ThemeIcon>
            <Box>
              <Text fw={700} c="secondary.9">
                {t('userManagement.registeredTitle')}
              </Text>
              <Text fz="sm" c="dimmed">
                {t('userManagement.registeredSubtitle')}
              </Text>
            </Box>
          </Group>
          <TextInput
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t('userManagement.searchPlaceholder')}
            leftSection={<IconSearch size={16} />}
            w={{ base: '100%', sm: 280 }}
          />
        </Group>

        {loading ? (
          <Box p="lg"><RowsSkeleton count={4} /></Box>
        ) : (
          /* The table is ~940px wide because of the two selects. Without a
             scroll container the surrounding Paper simply cut the last columns
             off on narrow viewports, with no way to reach them. */
          <Table.ScrollContainer minWidth={940} type="native">
          <Table verticalSpacing="md" horizontalSpacing="lg" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t('userManagement.columnUser')}</Table.Th>
                <Table.Th>{t('userManagement.columnSkill')}</Table.Th>
                <Table.Th>{t('userManagement.columnRole')}</Table.Th>
                <Table.Th>{t('userManagement.columnPoints')}</Table.Th>
                <Table.Th>{t('userManagement.columnMissions')}</Table.Th>
                <Table.Th>{t('userManagement.columnActions')}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {filteredUsers.map((user) => {
                const userId = getUserId(user)
                const progress = user.progress || {}
                const lastAdmin = isLastAdmin(users, user.id)
                const isCurrent = userId === currentUserId

                return (
                  <Table.Tr key={user.id}>
                    <Table.Td>
                      <Group gap="sm" wrap="nowrap">
                        <Avatar
                          radius="xl"
                          size={38}
                          style={{
                            background: isCurrent ? 'var(--gold)' : 'var(--mantine-color-secondary-0)',
                            color: isCurrent ? 'var(--ink)' : 'var(--mantine-color-secondary-7)',
                            fontWeight: 700,
                          }}
                        >
                          {initials(user)}
                        </Avatar>
                        <Box style={{ minWidth: 0 }}>
                          <Group gap="xs">
                            <Text fw={700} c="secondary.9" truncate>
                              {displayName(user)}
                            </Text>
                            {isCurrent && (
                              <Badge size="sm" color="accent" variant="light">
                                {t('userManagement.youBadge')}
                              </Badge>
                            )}
                          </Group>
                          <Text fz="sm" c="dimmed" truncate>
                            {user.email}
                          </Text>
                        </Box>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Select
                        data={skillOptions.map((option) => ({ ...option, label: t(`skillLevels.${option.value}`) }))}
                        value={user.skill_level || 'beginner'}
                        onChange={(level) => handleSkillChange(user, level)}
                        w={150}
                      />
                      <Text fz="xs" c="dimmed" mt={6}>
                        {t('userManagement.evaluationProgress', {
                          count: user.skill_progression?.relevant_completed_missions || 0,
                          minimum: user.skill_progression?.minimum_missions || settings?.minimum_missions || 10,
                        })}
                      </Text>
                      <Text fz="xs" c="dimmed">
                        {t('userManagement.currentAverage', { average: user.skill_progression?.current_average ?? '-' })}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Select
                        aria-label={t('userManagement.roleSelectAria', { name: displayName(user) })}
                        data={roleOptions}
                        value={user.role || ROLES.USER}
                        onChange={(role) => handleRoleChange(user, role)}
                        disabled={lastAdmin}
                        w={190}
                        leftSection={<IconShield size={16} />}
                      />
                      <Badge mt={6} color={roleColor(user.role)} variant="light">
                        {ROLE_LABELS[user.role || ROLES.USER]}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={800} c="secondary.9" ff="var(--font-display)">
                        {progress.total_points ?? progress.totalPoints ?? 0}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text c="secondary.9">
                        {progress.completed_mission_count ?? progress.completedMissionCount ?? 0}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Button
                        variant="subtle"
                        color="red"
                        size="compact-sm"
                        leftSection={<IconTrash size={16} />}
                        disabled={lastAdmin || isCurrent}
                        onClick={() => setDeleteTarget(user)}
                      >
                        {t('userManagement.delete')}
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>
          </Table.ScrollContainer>
        )}
      </Paper>

      <ConfirmModal
        opened={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        loading={deleting}
        title={t('userManagement.deleteModalTitle')}
        text={t('userManagement.deleteConfirm', { name: deleteTarget ? displayName(deleteTarget) : '' })}
        hint={t('userManagement.deleteHint')}
        confirmLabel={t('userManagement.delete')}
      />
    </Box>
  )
}
