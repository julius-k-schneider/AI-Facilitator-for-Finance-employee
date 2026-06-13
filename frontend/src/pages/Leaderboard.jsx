import {
  Avatar,
  Badge,
  Box,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconBolt,
  IconFlame,
  IconRosetteDiscountCheck,
  IconTrophy,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { LEADERBOARD_DEMO_ENTRIES } from '../data/leaderboardDemoData'
import PageShell from './PageShell'
import './Leaderboard.css'

const STAT_CONFIG = [
  { key: 'rank', icon: IconTrophy, color: 'accent' },
  { key: 'points', icon: IconBolt, color: 'brand' },
  { key: 'streak', suffixKey: 'days', icon: IconFlame, color: 'secondary' },
]

function StatCard({ item }) {
  const { t } = useTranslation()
  const Icon = item.icon

  return (
    <Paper withBorder radius="lg" p="lg" bg="white" className="leaderboard-stat-card">
      <Group justify="space-between" align="center" wrap="nowrap">
        <Stack gap={3}>
          <Text fz="sm" c="dimmed" fw={600}>
            {t(`pages.leaderboard.stats.${item.key}`)}
          </Text>
          <Group gap={7} align="baseline" wrap="nowrap">
            <Text fz={{ base: 27, sm: 30 }} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">
              {item.value}
            </Text>
            {item.suffixKey && (
              <Text fz="sm" c="dimmed" fw={600}>
                {t(`pages.leaderboard.${item.suffixKey}`)}
              </Text>
            )}
          </Group>
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={item.color}>
          <Icon size={22} stroke={1.7} />
        </ThemeIcon>
      </Group>
    </Paper>
  )
}

function PodiumCard({ employee, rank }) {
  const { t, i18n } = useTranslation()
  const isWinner = rank === 1

  return (
    <Paper
      withBorder
      radius="lg"
      p={0}
      bg="white"
      className={`podium-card podium-card--rank-${rank}`}
    >
      <div className="podium-card__accent" />
      <Stack align="center" gap={8} className="podium-card__content">
        <ThemeIcon
          size={isWinner ? 40 : 36}
          radius="xl"
          variant="filled"
          className={`podium-card__rank podium-card__rank--${rank}`}
        >
          <Text fw={800} fz={isWinner ? 'md' : 'sm'} lh={1}>
            {rank}
          </Text>
        </ThemeIcon>

        <Avatar
          size={isWinner ? 68 : 60}
          radius="xl"
          className={`podium-card__avatar podium-card__avatar--rank-${rank}`}
        >
          {employee.initials}
        </Avatar>

        <Stack align="center" gap={2}>
          <Text fw={700} fz={isWinner ? 'lg' : 'md'} c="secondary.9" ta="center">
            {employee.name}
          </Text>
          <Text fw={800} fz={isWinner ? 24 : 20} c="brand.6" ff="var(--font-display)">
            {employee.points.toLocaleString(i18n.resolvedLanguage)}
          </Text>
          <Text fz="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: '0.06em' }}>
            {t('pages.leaderboard.points')}
          </Text>
        </Stack>
      </Stack>
    </Paper>
  )
}

function LeaderboardRow({ employee, rank }) {
  const { t, i18n } = useTranslation()

  return (
    <div className={`leaderboard-row${employee.isCurrent ? ' leaderboard-row--current' : ''}`}>
      <Text className="leaderboard-rank" fw={800} c="secondary.7">
        {rank}
      </Text>

      <Group gap="sm" wrap="nowrap" className="leaderboard-person">
        <Avatar size={42} radius="xl" className="leaderboard-avatar">
          {employee.initials}
        </Avatar>
        <Box>
          <Group gap={8} wrap="nowrap">
            <Text fw={700} c="secondary.9">
              {employee.name}
            </Text>
            {employee.isCurrent && (
              <Badge size="sm" variant="light" color="brand" radius="xl" tt="none" className="leaderboard-you-badge">
                {t('pages.leaderboard.you')}
              </Badge>
            )}
          </Group>
          <Text fz="xs" c="dimmed" className="leaderboard-mobile-rank">
            {t('pages.leaderboard.rankLabel', { rank })}
          </Text>
        </Box>
      </Group>

      <Box className="leaderboard-cell">
        <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">
          {t('pages.leaderboard.points')}
        </Text>
        <Text fw={800} c="secondary.9">
          {employee.points.toLocaleString(i18n.resolvedLanguage)}
        </Text>
      </Box>

      <Group gap={6} wrap="nowrap" className="leaderboard-cell">
        <IconFlame size={17} stroke={1.8} color="var(--gold)" />
        <Box>
          <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">
            {t('pages.leaderboard.streak')}
          </Text>
          <Text fw={600}>{t('pages.leaderboard.streakDays', { count: employee.streak })}</Text>
        </Box>
      </Group>

      <Group gap={6} wrap="nowrap" className="leaderboard-cell">
        <IconRosetteDiscountCheck size={17} stroke={1.8} color="var(--blue)" />
        <Box>
          <Text fz="xs" c="dimmed" className="leaderboard-mobile-label">
            {t('pages.leaderboard.challenges')}
          </Text>
          <Text fw={600}>{employee.challenges}</Text>
        </Box>
      </Group>
    </div>
  )
}

function EmptyLeaderboard() {
  const { t } = useTranslation()

  return (
    <Paper withBorder radius="lg" p={{ base: 'xl', sm: 48 }} bg="white">
      <Stack align="center" gap="md" py="lg">
        <ThemeIcon size={58} radius="xl" variant="light" color="brand">
          <IconTrophy size={28} stroke={1.6} />
        </ThemeIcon>
        <Stack align="center" gap={4}>
          <Text fz="lg" fw={700} c="secondary.9">
            {t('pages.leaderboard.emptyTitle')}
          </Text>
          <Text c="dimmed" ta="center" maw={460}>
            {t('pages.leaderboard.emptyText')}
          </Text>
        </Stack>
      </Stack>
    </Paper>
  )
}

export default function Leaderboard({ entries = LEADERBOARD_DEMO_ENTRIES }) {
  const { t, i18n } = useTranslation()
  const leaderboardEntries = [...entries].sort((a, b) => b.points - a.points)
  const currentIndex = leaderboardEntries.findIndex((entry) => entry.isCurrent)
  const currentEntry = currentIndex >= 0 ? leaderboardEntries[currentIndex] : null
  const topThree = leaderboardEntries.slice(0, 3)
  const podiumEntries = [topThree[1], topThree[0], topThree[2]].filter(Boolean)
  const statItems = STAT_CONFIG.map((item) => {
    if (item.key === 'rank') {
      return { ...item, value: currentEntry ? `#${currentIndex + 1}` : '–' }
    }
    if (item.key === 'points') {
      return {
        ...item,
        value: currentEntry ? currentEntry.points.toLocaleString(i18n.resolvedLanguage) : '–',
      }
    }
    return { ...item, value: currentEntry?.streak?.toString() || '–' }
  })

  return (
    <PageShell
      title={t('pages.leaderboard.title')}
      description={t('pages.leaderboard.description')}
      icon={IconTrophy}
      maxWidth={1320}
    >
      {leaderboardEntries.length === 0 ? (
        <EmptyLeaderboard />
      ) : (
      <Stack gap="xl">
        <SimpleGrid cols={{ base: 1, xs: 3 }} spacing="lg">
          {statItems.map((item) => (
            <StatCard key={item.key} item={item} />
          ))}
        </SimpleGrid>

        <Box>
          <Group justify="space-between" align="flex-end" mb="sm">
            <Box>
              <Text fz="xs" fw={800} c="brand.6" tt="uppercase" style={{ letterSpacing: '0.08em' }}>
                {t('pages.leaderboard.topPerformers')}
              </Text>
              <Title order={2} fz={{ base: 22, sm: 25 }} c="secondary.9">
                {t('pages.leaderboard.podiumTitle')}
              </Title>
            </Box>
          </Group>

          <div className="podium-grid">
            {podiumEntries.map((employee) => {
              const rank = leaderboardEntries.indexOf(employee) + 1
              return <PodiumCard key={employee.id} employee={employee} rank={rank} />
            })}
          </div>
        </Box>

        <Paper withBorder radius="lg" bg="white" className="leaderboard-table">
          <Group justify="space-between" p={{ base: 'lg', sm: 'xl' }} pb="md">
            <Box>
              <Title order={2} fz={{ base: 20, sm: 23 }} c="secondary.9">
                {t('pages.leaderboard.fullRanking')}
              </Title>
              <Text fz="sm" c="dimmed">
                {t('pages.leaderboard.rankingHint')}
              </Text>
            </Box>
            <Badge variant="light" color="secondary" radius="xl" tt="none">
              {t('pages.leaderboard.participants', { count: leaderboardEntries.length })}
            </Badge>
          </Group>

          <div className="leaderboard-table__header">
            <Text>{t('pages.leaderboard.rank')}</Text>
            <Text>{t('pages.leaderboard.employee')}</Text>
            <Text>{t('pages.leaderboard.points')}</Text>
            <Text>{t('pages.leaderboard.streak')}</Text>
            <Text>{t('pages.leaderboard.challenges')}</Text>
          </div>

          <div className="leaderboard-table__body">
            {leaderboardEntries.map((employee, index) => (
              <LeaderboardRow key={employee.id} employee={employee} rank={index + 1} />
            ))}
          </div>
        </Paper>
      </Stack>
      )}
    </PageShell>
  )
}
