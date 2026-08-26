import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconArrowRight,
  IconChecklist,
  IconFlame,
  IconLock,
  IconTargetArrow,
  IconTrophy,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import PageShell from './PageShell'
import { StatValueSkeleton } from '../components/Skeletons'
import { useUserProgress } from '../hooks/useUserProgress'
import { PROGRESS_EVENT, getUserId } from '../services/progressService'

const API_BASE = import.meta.env.VITE_API_BASE || ''

function StatCard({ label, value, loading, icon: Icon, color }) {
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text fz="sm" c="dimmed" fw={500}>{label}</Text>
          {loading
            ? <StatValueSkeleton />
            : <Text fz={30} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">{value}</Text>}
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={color}><Icon size={23} /></ThemeIcon>
      </Group>
    </Paper>
  )
}

export default function Home({ user }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { progress, loading: progressLoading } = useUserProgress(user)
  const [weeklyRank, setWeeklyRank] = useState(null)
  const [rankLoading, setRankLoading] = useState(true)
  const onboardingDone = Boolean(user?.onboarding_completed)
  const currentUserId = getUserId(user)

  useEffect(() => {
    let active = true
    const loadRank = () => {
      setRankLoading(true)
      fetch(`${API_BASE}/api/auth/leaderboard/`, { credentials: 'include' })
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((data) => {
          if (!active) return
          const weeklyEntry = (data.weekly_entries || []).find((item) => String(item.user_id) === currentUserId)
          setWeeklyRank(weeklyEntry?.rank ?? null)
        })
        .catch(() => active && setWeeklyRank(null))
        .finally(() => active && setRankLoading(false))
    }

    loadRank()
    window.addEventListener(PROGRESS_EVENT, loadRank)
    return () => {
      active = false
      window.removeEventListener(PROGRESS_EVENT, loadRank)
    }
  }, [currentUserId])

  return (
    <PageShell
      badge={t('home.badge')}
      title={t('home.title', { name: user?.first_name || user?.username || t('home.fallbackName') })}
      description={t('home.subtitle')}
    >
      <Paper withBorder radius="lg" p={{ base: 'xl', md: 40 }} mb="xl" bg="white">
        <Stack gap="xl">
          <Group gap="lg" wrap="nowrap" align="flex-start">
            <ThemeIcon size={64} radius="md" variant="light" color={onboardingDone ? 'brand' : 'accent'}>
              {onboardingDone ? <IconTargetArrow size={34} /> : <IconLock size={34} />}
            </ThemeIcon>
            <Box>
              <Title order={3} fz={{ base: 22, md: 26 }} c="secondary.9">
                {onboardingDone ? t('home.actions.dailyMissionsTitle') : t('home.locked.title')}
              </Title>
              <Text c="dimmed" mt={4} maw={640}>
                {onboardingDone ? t('home.actions.dailyMissionsText') : t('home.locked.text')}
              </Text>
            </Box>
          </Group>
          <Button
            size="md"
            color={onboardingDone ? 'brand' : 'accent'}
            rightSection={<IconArrowRight size={18} />}
            onClick={() => navigate(onboardingDone ? '/missions' : '/basics')}
            w="fit-content"
          >
            {onboardingDone ? t('home.actions.openMissions') : t('home.locked.cta')}
          </Button>
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
        <StatCard label={t('home.stats.missions')} value={progress.completedMissionCount} loading={progressLoading} icon={IconChecklist} color="accent" />
        <StatCard label={t('home.stats.streak')} value={progress.currentStreak} loading={progressLoading} icon={IconFlame} color="orange" />
        <StatCard label={t('home.stats.weeklyRank')} value={weeklyRank ? `#${weeklyRank}` : '—'} loading={rankLoading} icon={IconTrophy} color="secondary" />
      </SimpleGrid>
    </PageShell>
  )
}
