import { useEffect, useMemo, useState } from 'react'
import {
  Avatar,
  Badge,
  Box,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconMedal, IconTrophy, IconUsers } from '@tabler/icons-react'
import { PROGRESS_EVENT, getLeaderboard, getUserId } from '../services/progressService'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function initials(entry) {
  const user = entry.user
  const first = user?.first_name?.[0] || entry.name?.[0] || '?'
  const second = user?.last_name?.[0] || ''
  return `${first}${second}`.toUpperCase()
}

function RankBadge({ rank }) {
  if (rank <= 3) {
    return (
      <Badge color="accent" variant="light" leftSection={<IconMedal size={13} />}>
        #{rank}
      </Badge>
    )
  }

  return (
    <Text fw={700} c="secondary.9">
      #{rank}
    </Text>
  )
}

export default function Leaderboard({ user }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshTick, setRefreshTick] = useState(0)
  const currentUserId = getUserId(user)

  useEffect(() => {
    fetch(`${API_BASE}/api/auth/users/`, { credentials: 'include' })
      .then((response) => {
        if (!response.ok) throw new Error('users failed')
        return response.json()
      })
      .then((data) => {
        setUsers(data.users || [])
        setError('')
      })
      .catch(() => setError('Accounts konnten nicht geladen werden.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const refresh = () => setRefreshTick((value) => value + 1)
    window.addEventListener(PROGRESS_EVENT, refresh)
    window.addEventListener('storage', refresh)

    return () => {
      window.removeEventListener(PROGRESS_EVENT, refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [])

  const leaderboard = useMemo(() => {
    void refreshTick
    return getLeaderboard(users)
  }, [users, refreshTick])

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
            'linear-gradient(135deg, var(--mantine-color-secondary-7) 0%, var(--mantine-color-secondary-6) 60%, var(--mantine-color-brand-7) 135%)',
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
            <IconTrophy size={30} stroke={1.7} />
          </ThemeIcon>
          <Stack gap={6}>
            <Title order={1} fz={{ base: 28, md: 36 }}>
              Leaderboard
            </Title>
            <Text c="rgba(255,255,255,0.78)" maw={680}>
              Alle registrierten Accounts mit echten Mission-Punkten. Accounts ohne Abschluss
              starten sauber mit 0 Punkten.
            </Text>
          </Stack>
        </Group>
      </Paper>

      <Paper withBorder radius="lg" p={0} bg="white" style={{ overflow: 'hidden' }}>
        <Group justify="space-between" p="lg" style={{ borderBottom: '1px solid var(--line)' }}>
          <Group gap="sm">
            <ThemeIcon size={40} radius="md" variant="light" color="brand">
              <IconUsers size={22} stroke={1.7} />
            </ThemeIcon>
            <Box>
              <Text fw={700} c="secondary.9">
                Rangliste
              </Text>
              <Text fz="sm" c="dimmed">
                Sortiert nach Punkten und abgeschlossenen Missions
              </Text>
            </Box>
          </Group>
        </Group>

        {loading ? (
          <Group justify="center" py={48}>
            <Loader size="sm" color="brand" />
            <Text c="dimmed">Leaderboard wird geladen...</Text>
          </Group>
        ) : error ? (
          <Text c="red.7" p="lg">
            {error}
          </Text>
        ) : (
          <Table verticalSpacing="md" horizontalSpacing="lg" highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Rang</Table.Th>
                <Table.Th>Account</Table.Th>
                <Table.Th>Punkte</Table.Th>
                <Table.Th>Missions</Table.Th>
                <Table.Th>Level</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {leaderboard.map((entry) => {
                const isCurrent = entry.userId === currentUserId

                return (
                  <Table.Tr
                    key={entry.userId}
                    style={{
                      background: isCurrent ? 'rgba(var(--gold-rgb),0.10)' : undefined,
                    }}
                  >
                    <Table.Td>
                      <RankBadge rank={entry.rank} />
                    </Table.Td>
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
                          {initials(entry)}
                        </Avatar>
                        <Box style={{ minWidth: 0 }}>
                          <Group gap="xs">
                            <Text fw={700} c="secondary.9" truncate>
                              {entry.name}
                            </Text>
                            {isCurrent && (
                              <Badge size="sm" color="accent" variant="light">
                                Du
                              </Badge>
                            )}
                          </Group>
                          {!entry.user.first_name && !entry.user.last_name && (
                            <Text fz="sm" c="dimmed" truncate>
                              {entry.email}
                            </Text>
                          )}
                        </Box>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={800} c="secondary.9" ff="var(--font-display)">
                        {entry.totalPoints}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text c="secondary.9">{entry.completedMissions}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge color="brand" variant="light">
                        {entry.level}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                )
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Box>
  )
}
