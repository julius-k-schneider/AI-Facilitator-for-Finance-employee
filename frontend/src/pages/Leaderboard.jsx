import { useEffect, useMemo, useState } from 'react'
import {
  Avatar,
  Badge,
  Box,
  Group,
  Loader,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconBolt, IconRosetteDiscountCheck, IconTrophy } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { PROGRESS_EVENT, getUserId } from '../services/progressService'
import PageShell from './PageShell'
import './Leaderboard.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const STAT_CONFIG = [
  { key: 'rank', icon: IconTrophy, color: 'accent' },
  { key: 'points', icon: IconBolt, color: 'brand' },
  { key: 'missions', icon: IconRosetteDiscountCheck, color: 'secondary' },
]

function normalizeEntry(entry, currentUserId) {
  const initials = `${entry.first_name?.[0] || entry.name?.[0] || '?'}${entry.last_name?.[0] || ''}`
  return {
    id: entry.user_id,
    name: entry.name,
    email: entry.email,
    initials: initials.toUpperCase(),
    points: entry.total_points,
    missions: entry.completed_missions,
    level: entry.level,
    isCurrent: String(entry.user_id) === currentUserId,
  }
}

function StatCard({ item }) {
  const { t } = useTranslation()
  const Icon = item.icon
  return (
    <Paper withBorder radius="lg" p="lg" bg="white" className="leaderboard-stat-card">
      <Group justify="space-between" align="center" wrap="nowrap">
        <Stack gap={3}>
          <Text fz="sm" c="dimmed" fw={600}>{t(`pages.leaderboard.stats.${item.key}`)}</Text>
          <Text fz={{ base: 27, sm: 30 }} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">{item.value}</Text>
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={item.color}><Icon size={22} /></ThemeIcon>
      </Group>
    </Paper>
  )
}

function PodiumCard({ employee, rank }) {
  const { t, i18n } = useTranslation()
  const isWinner = rank === 1
  return (
    <Paper withBorder radius="lg" p={0} bg="white" className={`podium-card podium-card--rank-${rank}`}>
      <div className="podium-card__accent" />
      <Stack align="center" gap={8} className="podium-card__content">
        <ThemeIcon size={isWinner ? 40 : 36} radius="xl" variant="filled" className={`podium-card__rank podium-card__rank--${rank}`}>
          <Text fw={800} fz={isWinner ? 'md' : 'sm'} lh={1}>{rank}</Text>
        </ThemeIcon>
        <Avatar size={isWinner ? 68 : 60} radius="xl" className={`podium-card__avatar podium-card__avatar--rank-${rank}`}>{employee.initials}</Avatar>
        <Stack align="center" gap={2}>
          <Text fw={700} fz={isWinner ? 'lg' : 'md'} c="secondary.9" ta="center">{employee.name}</Text>
          <Text fw={800} fz={isWinner ? 24 : 20} c="brand.6" ff="var(--font-display)">{employee.points.toLocaleString(i18n.resolvedLanguage)}</Text>
          <Text fz="xs" c="dimmed" fw={600} tt="uppercase">{t('pages.leaderboard.points')}</Text>
        </Stack>
      </Stack>
    </Paper>
  )
}

function LeaderboardRow({ employee, rank }) {
  const { t, i18n } = useTranslation()
  return (
    <div className={`leaderboard-row${employee.isCurrent ? ' leaderboard-row--current' : ''}`}>
      <Text className="leaderboard-rank" fw={800} c="secondary.7">{rank}</Text>
      <Group gap="sm" wrap="nowrap" className="leaderboard-person">
        <Avatar size={42} radius="xl" className="leaderboard-avatar">{employee.initials}</Avatar>
        <Box>
          <Group gap={8} wrap="nowrap">
            <Text fw={700} c="secondary.9">{employee.name}</Text>
            {employee.isCurrent && <Badge size="sm" variant="light" color="brand" radius="xl" tt="none" className="leaderboard-you-badge">{t('pages.leaderboard.you')}</Badge>}
          </Group>
          <Text fz="xs" c="dimmed" className="leaderboard-mobile-rank">{t('pages.leaderboard.rankLabel', { rank })}</Text>
        </Box>
      </Group>
      <Box className="leaderboard-cell">
        <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">{t('pages.leaderboard.points')}</Text>
        <Text fw={800} c="secondary.9">{employee.points.toLocaleString(i18n.resolvedLanguage)}</Text>
      </Box>
      <Group gap={6} wrap="nowrap" className="leaderboard-cell">
        <IconRosetteDiscountCheck size={17} color="var(--gold)" />
        <Box>
          <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">{t('pages.leaderboard.missions')}</Text>
          <Text fw={600}>{employee.missions}</Text>
        </Box>
      </Group>
      <Box className="leaderboard-cell">
        <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">{t('pages.leaderboard.level')}</Text>
        <Badge color="brand" variant="light">{employee.level}</Badge>
      </Box>
    </div>
  )
}

function EmptyLeaderboard() {
  const { t } = useTranslation()
  return (
    <Paper withBorder radius="lg" p={{ base: 'xl', sm: 48 }} bg="white">
      <Stack align="center" gap="md" py="lg">
        <ThemeIcon size={58} radius="xl" variant="light" color="brand"><IconTrophy size={28} /></ThemeIcon>
        <Stack align="center" gap={4}>
          <Text fz="lg" fw={700}>{t('pages.leaderboard.emptyTitle')}</Text>
          <Text c="dimmed" ta="center" maw={460}>{t('pages.leaderboard.emptyText')}</Text>
        </Stack>
      </Stack>
    </Paper>
  )
}

export default function Leaderboard({ user }) {
  const { t, i18n } = useTranslation()
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
          return data.entries || []
        })
        .then((data) => {
          if (active) {
            setEntries(data)
            setError('')
          }
        })
        .catch((nextError) => active && setError(nextError.message))
        .finally(() => active && setLoading(false))
    }
    load()
    window.addEventListener(PROGRESS_EVENT, load)
    return () => {
      active = false
      window.removeEventListener(PROGRESS_EVENT, load)
    }
  }, [])

  const leaderboardEntries = useMemo(
    () => entries.map((entry) => normalizeEntry(entry, currentUserId)).sort((a, b) => b.points - a.points || b.missions - a.missions || a.name.localeCompare(b.name)),
    [entries, currentUserId],
  )
  const currentIndex = leaderboardEntries.findIndex((entry) => entry.isCurrent)
  const currentEntry = currentIndex >= 0 ? leaderboardEntries[currentIndex] : null
  const topThree = leaderboardEntries.slice(0, 3)
  const podiumEntries = [topThree[1], topThree[0], topThree[2]].filter(Boolean)
  const statItems = STAT_CONFIG.map((item) => ({
    ...item,
    value: item.key === 'rank'
      ? (currentEntry ? `#${currentIndex + 1}` : '-')
      : item.key === 'points'
        ? (currentEntry ? currentEntry.points.toLocaleString(i18n.resolvedLanguage) : '-')
        : (currentEntry?.missions ?? '-'),
  }))

  return (
    <PageShell title={t('pages.leaderboard.title')} description={t('pages.leaderboard.description')} icon={IconTrophy}>
      {loading ? (
        <Paper withBorder radius="lg" p="xl"><Group justify="center"><Loader size="sm" /><Text c="dimmed">Leaderboard wird geladen...</Text></Group></Paper>
      ) : error ? (
        <Paper withBorder radius="lg" p="xl"><Text c="red.7">{error}</Text></Paper>
      ) : leaderboardEntries.length === 0 ? (
        <EmptyLeaderboard />
      ) : (
        <Stack gap="xl">
          <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="lg">{statItems.map((item) => <StatCard key={item.key} item={item} />)}</SimpleGrid>
          <Box>
            <Text fz="xs" fw={800} c="brand.6" tt="uppercase">{t('pages.leaderboard.topPerformers')}</Text>
            <Title order={2} fz={{ base: 22, sm: 25 }} c="secondary.9" mb="sm">{t('pages.leaderboard.podiumTitle')}</Title>
            <div className="podium-grid">{podiumEntries.map((employee) => <PodiumCard key={employee.id} employee={employee} rank={leaderboardEntries.indexOf(employee) + 1} />)}</div>
          </Box>
          <Paper withBorder radius="lg" bg="white" className="leaderboard-table">
            <Group justify="space-between" p={{ base: 'lg', sm: 'xl' }} pb="md">
              <Box><Title order={2} fz={{ base: 20, sm: 23 }}>{t('pages.leaderboard.fullRanking')}</Title><Text fz="sm" c="dimmed">{t('pages.leaderboard.rankingHint')}</Text></Box>
              <Badge variant="light" color="secondary" radius="xl" tt="none">{t('pages.leaderboard.participants', { count: leaderboardEntries.length })}</Badge>
            </Group>
            <div className="leaderboard-table__header"><Text>{t('pages.leaderboard.rank')}</Text><Text>{t('pages.leaderboard.employee')}</Text><Text>{t('pages.leaderboard.points')}</Text><Text>{t('pages.leaderboard.missions')}</Text><Text>{t('pages.leaderboard.level')}</Text></div>
            <div className="leaderboard-table__body">{leaderboardEntries.map((employee, index) => <LeaderboardRow key={employee.id} employee={employee} rank={index + 1} />)}</div>
          </Paper>
        </Stack>
      )}
    </PageShell>
  )
}
