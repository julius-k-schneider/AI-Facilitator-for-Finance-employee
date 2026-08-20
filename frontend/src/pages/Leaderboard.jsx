import { useEffect, useMemo, useState } from 'react'
import {
  Avatar,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  Paper,
  Select,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import { IconArchive, IconBolt, IconFlame, IconRosetteDiscountCheck, IconTrophy } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { PROGRESS_EVENT, getUserId } from '../services/progressService'
import PageShell from './PageShell'
import './Leaderboard.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const SKILL_DIFFICULTY = { beginner: 'easy', advanced: 'medium', pro: 'hard' }
const DIFFICULTY_SKILL = { easy: 'beginner', medium: 'advanced', hard: 'pro' }

const STAT_CONFIG = [
  { key: 'rank', icon: IconTrophy, color: 'accent' },
  { key: 'points', icon: IconBolt, color: 'brand' },
  { key: 'missions', icon: IconRosetteDiscountCheck, color: 'secondary' },
  { key: 'streak', icon: IconFlame, color: 'orange' },
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
    maxStreak: entry.max_streak || 0,
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

function LeaderboardRow({ employee, rank, showStreak }) {
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
      {showStreak && <Box className="leaderboard-cell">
        <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">{t('pages.leaderboard.streak')}</Text>
        <Group gap={5} wrap="nowrap"><IconFlame size={16} color="var(--mantine-color-orange-6)" /><Text fw={600}>{employee.maxStreak}</Text></Group>
      </Box>}
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
  const [weeklyEntries, setWeeklyEntries] = useState([])
  const [history, setHistory] = useState([])
  const [mode, setMode] = useState('all')
  const [weekRange, setWeekRange] = useState(null)
  const [historyOpened, setHistoryOpened] = useState(false)
  const [selectedHistory, setSelectedHistory] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [difficulty, setDifficulty] = useState(() => SKILL_DIFFICULTY[user?.skill_level] || 'easy')
  const currentUserId = getUserId(user)

  useEffect(() => {
    let active = true
    const load = () => {
      setLoading(true)
      fetch(`${API_BASE}/api/auth/leaderboard/?difficulty=${difficulty}`, { credentials: 'include' })
        .then(async (response) => {
          const data = await response.json().catch(() => ({}))
          if (!response.ok) throw new Error(data.error || t('pages.leaderboard.loadError'))
          return data
        })
        .then((data) => {
          if (active) {
            setEntries(data.entries || [])
            setWeeklyEntries(data.weekly_entries || [])
            setHistory(data.history || [])
            setWeekRange({ start: data.week_start, end: data.week_end })
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
  }, [t, difficulty])

  const leaderboardEntries = useMemo(
    () => {
      const sourceEntries = mode === 'all' ? entries : mode === 'weekly' ? weeklyEntries : selectedHistory?.entries || []
      return sourceEntries.map((entry) => normalizeEntry(entry, currentUserId)).sort((a, b) => b.points - a.points || b.missions - a.missions || a.name.localeCompare(b.name))
    },
    [mode, entries, weeklyEntries, selectedHistory, currentUserId],
  )
  const currentIndex = leaderboardEntries.findIndex((entry) => entry.isCurrent)
  const currentEntry = currentIndex >= 0 ? leaderboardEntries[currentIndex] : null
  const topThree = leaderboardEntries.slice(0, 3)
  const podiumEntries = [topThree[1], topThree[0], topThree[2]].filter(Boolean)
  const showStreak = mode === 'all'
  const activeRange = mode === 'history' ? selectedHistory : weekRange
  const statItems = STAT_CONFIG.filter((item) => showStreak || item.key !== 'streak').map((item) => ({
    ...item,
    value: item.key === 'rank'
      ? (currentEntry ? `#${currentIndex + 1}` : '-')
      : item.key === 'points'
        ? (currentEntry ? currentEntry.points.toLocaleString(i18n.resolvedLanguage) : '-')
        : item.key === 'missions'
          ? (currentEntry?.missions ?? '-')
          : (currentEntry?.maxStreak ?? '-'),
  }))

  const openHistory = async (weekStart) => {
    if (!weekStart) return
    setHistoryLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/auth/leaderboard/history/${weekStart}/?difficulty=${difficulty}`, { credentials: 'include' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || t('pages.leaderboard.historyError'))
      setSelectedHistory(data)
      setMode('history')
      setHistoryOpened(false)
      setError('')
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setHistoryLoading(false)
    }
  }

  const formatRange = (range) => range?.start || range?.week_start
    ? `${new Date(`${range.start || range.week_start}T12:00:00`).toLocaleDateString(i18n.resolvedLanguage)} - ${new Date(`${range.end || range.week_end}T12:00:00`).toLocaleDateString(i18n.resolvedLanguage)}`
    : ''

  return (
    <PageShell title={t('pages.leaderboard.title')} description={t('pages.leaderboard.description')} icon={IconTrophy}>
      <SegmentedControl
        mb="xl"
        value={difficulty}
        onChange={(value) => { setDifficulty(value); setMode('all'); setSelectedHistory(null) }}
        data={['easy', 'medium', 'hard'].map((value) => ({
          value,
          label: t(`skillLevels.${DIFFICULTY_SKILL[value]}`),
        }))}
      />
      <Group justify="space-between" mb="xl">
        <Group gap="xs">
          <Button variant={mode === 'all' ? 'filled' : 'light'} onClick={() => setMode('all')}>{t('pages.leaderboard.allTime')}</Button>
          <Button variant={mode !== 'all' ? 'filled' : 'light'} onClick={() => setMode('weekly')}>{t('pages.leaderboard.weekly')}</Button>
        </Group>
        <Button variant="subtle" color="secondary" leftSection={<IconArchive size={17} />} onClick={() => setHistoryOpened(true)}>{t('pages.leaderboard.history')}</Button>
      </Group>
      {mode !== 'all' && <Text c="dimmed" fz="sm" mb="md">{mode === 'history' ? t('pages.leaderboard.archivedWeek') : t('pages.leaderboard.currentWeek')}: {formatRange(activeRange)}</Text>}
      {loading ? (
        <Paper withBorder radius="lg" p="xl"><Group justify="center"><Loader size="sm" /><Text c="dimmed">{t('pages.leaderboard.loading')}</Text></Group></Paper>
      ) : error ? (
        <Paper withBorder radius="lg" p="xl"><Text c="red.7">{error}</Text></Paper>
      ) : leaderboardEntries.length === 0 ? (
        <EmptyLeaderboard />
      ) : (
        <Stack gap="xl">
          <SimpleGrid cols={{ base: 1, xs: 2, lg: showStreak ? 4 : 3 }} spacing="lg">{statItems.map((item) => <StatCard key={item.key} item={item} />)}</SimpleGrid>
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
            <div className={`leaderboard-table__header${showStreak ? '' : ' leaderboard-table__header--weekly'}`}><Text>{t('pages.leaderboard.rank')}</Text><Text>{t('pages.leaderboard.employee')}</Text><Text>{t('pages.leaderboard.points')}</Text><Text>{t('pages.leaderboard.missions')}</Text>{showStreak && <Text>{t('pages.leaderboard.streak')}</Text>}<Text>{t('pages.leaderboard.level')}</Text></div>
            <div className="leaderboard-table__body">{leaderboardEntries.map((employee, index) => <LeaderboardRow key={employee.id} employee={employee} rank={index + 1} showStreak={showStreak} />)}</div>
          </Paper>
        </Stack>
      )}
      <Modal opened={historyOpened} onClose={() => setHistoryOpened(false)} title={t('pages.leaderboard.historyTitle')} centered>
        <Stack gap="md">
          <Text c="dimmed" fz="sm">{t('pages.leaderboard.historyText')}</Text>
          <Select
            label={t('pages.leaderboard.selectWeek')}
            placeholder={t('pages.leaderboard.selectWeekPlaceholder')}
            data={history.map((item) => ({ value: item.week_start, label: formatRange(item) }))}
            onChange={openHistory}
            disabled={history.length === 0}
          />
          {history.length === 0 && <Text c="dimmed">{t('pages.leaderboard.noHistory')}</Text>}
          {historyLoading && <Group><Loader size="sm" /><Text c="dimmed">{t('pages.leaderboard.loadingHistory')}</Text></Group>}
        </Stack>
      </Modal>
    </PageShell>
  )
}
