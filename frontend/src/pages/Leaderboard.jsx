import { useEffect, useState } from 'react'
import { Avatar, Badge, Box, Group, Loader, Paper, Stack, Table, Text, ThemeIcon, Title } from '@mantine/core'
import { IconMedal, IconTrophy, IconUsers } from '@tabler/icons-react'
import { PROGRESS_EVENT, getUserId } from '../services/progressService'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function initials(entry) {
  return `${entry.first_name?.[0] || entry.name?.[0] || '?'}${entry.last_name?.[0] || ''}`.toUpperCase()
}

function RankBadge({ rank }) {
  if (rank <= 3) {
    return <Badge color="accent" variant="light" leftSection={<IconMedal size={13} />}>#{rank}</Badge>
  }
  return <Text fw={700} c="secondary.9">#{rank}</Text>
}

export default function Leaderboard({ user }) {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const currentUserId = getUserId(user)

  useEffect(() => {
    let active = true
    const load = () => {
      setLoading(true)
      fetch(`${API_BASE}/api/auth/leaderboard/`, { credentials: 'include' })
        .then(async (response) => {
          const data = await response.json().catch(() => ({}))
          if (!response.ok) throw new Error(data.error || 'Leaderboard konnte nicht geladen werden.')
          return data
        })
        .then((data) => {
          if (active) {
            setEntries(data.entries || [])
            setError('')
          }
        })
        .catch((nextError) => {
          if (active) setError(nextError.message)
        })
        .finally(() => {
          if (active) setLoading(false)
        })
    }

    load()
    window.addEventListener(PROGRESS_EVENT, load)
    return () => {
      active = false
      window.removeEventListener(PROGRESS_EVENT, load)
    }
  }, [])

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      <Paper radius="xl" p={{ base: 'xl', md: 38 }} mb="xl" style={{ background: 'linear-gradient(135deg, var(--mantine-color-secondary-7), var(--mantine-color-brand-7))', color: '#fff' }}>
        <Group gap="lg" align="flex-start">
          <ThemeIcon size={54} radius="md" variant="light" color="accent"><IconTrophy size={30} /></ThemeIcon>
          <Stack gap={6}>
            <Title order={1} fz={{ base: 28, md: 36 }}>Leaderboard</Title>
            <Text c="rgba(255,255,255,0.78)">Rangliste aller registrierten Accounts anhand ihrer gespeicherten Missionsergebnisse.</Text>
          </Stack>
        </Group>
      </Paper>

      <Paper withBorder radius="lg" bg="white" style={{ overflow: 'hidden' }}>
        <Group p="lg" style={{ borderBottom: '1px solid var(--line)' }}>
          <ThemeIcon size={40} radius="md" variant="light" color="brand"><IconUsers size={22} /></ThemeIcon>
          <Box>
            <Text fw={700} c="secondary.9">Rangliste</Text>
            <Text fz="sm" c="dimmed">Sortiert nach Punkten und abgeschlossenen Missionen</Text>
          </Box>
        </Group>

        {loading ? (
          <Group justify="center" py={48}><Loader size="sm" /><Text c="dimmed">Leaderboard wird geladen...</Text></Group>
        ) : error ? (
          <Text c="red.7" p="lg">{error}</Text>
        ) : entries.length === 0 ? (
          <Text c="dimmed" p="xl" ta="center">Noch keine registrierten Accounts vorhanden.</Text>
        ) : (
          <Table verticalSpacing="md" horizontalSpacing="lg" highlightOnHover>
            <Table.Thead><Table.Tr><Table.Th>Rang</Table.Th><Table.Th>Account</Table.Th><Table.Th>Punkte</Table.Th><Table.Th>Missionen</Table.Th><Table.Th>Level</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>
              {entries.map((entry) => {
                const isCurrent = String(entry.user_id) === currentUserId
                return (
                  <Table.Tr key={entry.user_id} style={{ background: isCurrent ? 'rgba(var(--gold-rgb),0.10)' : undefined }}>
                    <Table.Td><RankBadge rank={entry.rank} /></Table.Td>
                    <Table.Td>
                      <Group gap="sm" wrap="nowrap">
                        <Avatar radius="xl" size={38} style={{ background: isCurrent ? 'var(--gold)' : 'var(--mantine-color-secondary-0)', color: 'var(--ink)', fontWeight: 700 }}>{initials(entry)}</Avatar>
                        <Box>
                          <Group gap="xs"><Text fw={700}>{entry.name}</Text>{isCurrent && <Badge size="sm" color="accent" variant="light">Du</Badge>}</Group>
                          <Text fz="sm" c="dimmed">{entry.email}</Text>
                        </Box>
                      </Group>
                    </Table.Td>
                    <Table.Td><Text fw={800}>{entry.total_points}</Text></Table.Td>
                    <Table.Td>{entry.completed_missions}</Table.Td>
                    <Table.Td><Badge color="brand" variant="light">{entry.level}</Badge></Table.Td>
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
