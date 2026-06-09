import { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Avatar,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
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
import { deleteUserProgress, getUserProgress } from '../services/progressService'
import { getUserId } from '../services/progressService'
import { ROLE_LABELS, ROLES, getAvailableRoles } from '../auth/permissions'
import { deleteUser, getAllRegisteredUsers, updateUserRole } from '../services/userService'

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

export default function UserManagement({ currentUser, onCurrentUserUpdate }) {
  const [users, setUsers] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const currentUserId = getUserId(currentUser)

  useEffect(() => {
    let isActive = true

    getAllRegisteredUsers()
      .then((nextUsers) => {
        if (!isActive) return
        setUsers(nextUsers)
        setMessage(null)
      })
      .catch((error) => {
        if (!isActive) return
        setMessage({ type: 'error', text: error.message || 'Nutzer konnten nicht geladen werden.' })
      })
      .finally(() => {
        if (isActive) setLoading(false)
      })

    return () => {
      isActive = false
    }
  }, [])

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
      setMessage({ type: 'error', text: 'Der letzte Admin kann nicht degradiert werden.' })
      return
    }

    try {
      const updatedUser = await updateUserRole(target.id, role)
      setUsers((current) => current.map((user) => (user.id === updatedUser.id ? updatedUser : user)))
      if (String(updatedUser.id) === currentUserId) {
        onCurrentUserUpdate(updatedUser)
      }
      setMessage({ type: 'success', text: 'Rolle wurde aktualisiert.' })
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Rolle konnte nicht aktualisiert werden.' })
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (String(deleteTarget.id) === currentUserId) {
      setMessage({ type: 'error', text: 'Du kannst deinen eigenen Account hier nicht löschen.' })
      setDeleteTarget(null)
      return
    }
    if (isLastAdmin(users, deleteTarget.id)) {
      setMessage({ type: 'error', text: 'Der letzte Admin kann nicht gelöscht werden.' })
      setDeleteTarget(null)
      return
    }

    try {
      await deleteUser(deleteTarget.id)
      deleteUserProgress(deleteTarget.id)
      setUsers((current) => current.filter((user) => user.id !== deleteTarget.id))
      setDeleteTarget(null)
      setMessage({ type: 'success', text: 'Nutzer wurde gelöscht.' })
    } catch (error) {
      setMessage({ type: 'error', text: error.message || 'Nutzer konnte nicht gelöscht werden.' })
    }
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
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
              Nutzerverwaltung
            </Title>
            <Text c="rgba(255,255,255,0.78)" maw={680}>
              Verwalte registrierte Nutzer, Rollen und Zugriffsrechte.
            </Text>
          </Stack>
        </Group>
      </Paper>

      <Paper withBorder radius="lg" bg="white" style={{ overflow: 'hidden' }}>
        <Group justify="space-between" p="lg" style={{ borderBottom: '1px solid var(--line)' }}>
          <Group gap="sm">
            <ThemeIcon size={40} radius="md" variant="light" color="brand">
              <IconUsers size={22} stroke={1.7} />
            </ThemeIcon>
            <Box>
              <Text fw={700} c="secondary.9">
                Registrierte Nutzer
              </Text>
              <Text fz="sm" c="dimmed">
                Suche, Rollen und Zugriffspflege
              </Text>
            </Box>
          </Group>
          <TextInput
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Suchen..."
            leftSection={<IconSearch size={16} />}
            w={{ base: '100%', sm: 280 }}
          />
        </Group>

        {message && (
          <Alert color={message.type === 'error' ? 'red' : 'green'} variant="light" radius={0}>
            {message.text}
          </Alert>
        )}

        {loading ? (
          <Group justify="center" py={48}>
            <Loader size="sm" color="brand" />
            <Text c="dimmed">Nutzer werden geladen...</Text>
          </Group>
        ) : (
          <Table verticalSpacing="md" horizontalSpacing="lg" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Nutzer</Table.Th>
                <Table.Th>Rolle</Table.Th>
                <Table.Th>Punkte</Table.Th>
                <Table.Th>Missions</Table.Th>
                <Table.Th>Aktionen</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {filteredUsers.map((user) => {
                const userId = getUserId(user)
                const progress = getUserProgress(userId)
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
                                Du
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
                        aria-label={`Rolle fuer ${displayName(user)}`}
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
                        {progress.totalPoints}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text c="secondary.9">{progress.completedMissions.length}</Text>
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
                        Löschen
                      </Button>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>

      <Modal
        opened={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        title="Nutzer löschen"
        centered
      >
        <Stack gap="md">
          <Text c="secondary.9">
            Soll der Account {deleteTarget ? displayName(deleteTarget) : ''} wirklich gelöscht werden?
          </Text>
          <Text fz="sm" c="dimmed">
            Der Nutzer verschwindet aus Nutzerverwaltung und Leaderboard. Lokale Progress-Daten
            werden in diesem Browser ebenfalls entfernt.
          </Text>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeleteTarget(null)}>
              Abbrechen
            </Button>
            <Button color="red" leftSection={<IconTrash size={16} />} onClick={handleDelete}>
              Löschen
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Box>
  )
}
