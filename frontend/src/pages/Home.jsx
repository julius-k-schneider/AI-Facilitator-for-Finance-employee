import { useEffect, useState } from 'react'
import {
  Badge,
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
  IconBolt,
  IconBooks,
  IconChecklist,
  IconLock,
  IconTargetArrow,
  IconTrophy,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useUserProgress } from '../hooks/useUserProgress'
import { PROGRESS_EVENT, getUserId } from '../services/progressService'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text fz="sm" c="dimmed" fw={500}>{label}</Text>
          <Text fz={30} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">{value}</Text>
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={color}><Icon size={23} /></ThemeIcon>
      </Group>
    </Paper>
  )
}

function ActionCard({ icon: Icon, title, text, action, onClick, color = 'brand', disabled = false }) {
  return (
    <Paper withBorder radius="lg" p="xl" bg="white">
      <Stack gap="lg" h="100%" justify="space-between">
        <Group gap="md" wrap="nowrap" align="flex-start">
          <ThemeIcon size={48} radius="md" variant="light" color={color}><Icon size={25} /></ThemeIcon>
          <Box>
            <Text fw={700} fz="lg" c="secondary.9">{title}</Text>
            <Text fz="sm" c="dimmed" mt={4}>{text}</Text>
          </Box>
        </Group>
        <Button
          variant="light"
          color={color}
          rightSection={<IconArrowRight size={17} />}
          onClick={onClick}
          disabled={disabled}
          w="fit-content"
        >
          {action}
        </Button>
      </Stack>
    </Paper>
  )
}

export default function Home({ user, navigate }) {
  const { t } = useTranslation()
  const { progress } = useUserProgress(user)
  const [rank, setRank] = useState(null)
  const onboardingDone = Boolean(user?.onboarding_completed)
  const currentUserId = getUserId(user)

  useEffect(() => {
    let active = true
    const loadRank = () => {
      fetch(`${API_BASE}/api/auth/leaderboard/`, { credentials: 'include' })
        .then((response) => response.ok ? response.json() : Promise.reject())
        .then((data) => {
          if (!active) return
          const entry = (data.entries || []).find((item) => String(item.user_id) === currentUserId)
          setRank(entry?.rank ?? null)
        })
        .catch(() => active && setRank(null))
    }

    loadRank()
    window.addEventListener(PROGRESS_EVENT, loadRank)
    return () => {
      active = false
      window.removeEventListener(PROGRESS_EVENT, loadRank)
    }
  }, [currentUserId])

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Stack gap={4} mb="xl">
        <Badge variant="light" color="brand" w="fit-content">{t('home.badge')}</Badge>
        <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
          {t('home.title', { name: user?.first_name || user?.username || t('home.fallbackName') })}
        </Title>
        <Text fz="lg" c="dimmed" maw={700}>{t('home.subtitle')}</Text>
      </Stack>

      {!onboardingDone && (
        <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} mb="xl" bg="white">
          <Group justify="space-between" align="center" wrap="wrap" gap="md">
            <Group gap="md" wrap="nowrap" align="flex-start">
              <ThemeIcon size={44} radius="md" variant="light" color="accent"><IconLock size={22} /></ThemeIcon>
              <Box>
                <Text fw={700} c="secondary.9">{t('home.locked.title')}</Text>
                <Text fz="sm" c="dimmed" maw={520}>{t('home.locked.text')}</Text>
              </Box>
            </Group>
            <Button color="brand" rightSection={<IconArrowRight size={18} />} onClick={() => navigate('grundlagen')}>
              {t('home.locked.cta')}
            </Button>
          </Group>
        </Paper>
      )}

      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" mb="xl">
        <StatCard label={t('home.stats.points')} value={progress.totalPoints} icon={IconBolt} color="brand" />
        <StatCard label={t('home.stats.missions')} value={progress.completedMissionCount} icon={IconChecklist} color="accent" />
        <StatCard label={t('home.stats.rank')} value={rank ? `#${rank}` : '-'} icon={IconTrophy} color="secondary" />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <ActionCard
          icon={onboardingDone ? IconTargetArrow : IconLock}
          title={onboardingDone ? t('home.actions.dailyMissionsTitle') : t('home.actions.onboardingTitle')}
          text={onboardingDone ? t('home.actions.dailyMissionsText') : t('home.actions.onboardingText')}
          action={onboardingDone ? t('home.actions.openMissions') : t('home.locked.cta')}
          onClick={() => onboardingDone ? navigate('missions') : navigate('grundlagen')}
          color={onboardingDone ? 'brand' : 'accent'}
        />
        <ActionCard
          icon={IconBooks}
          title={t('home.actions.libraryTitle')}
          text={t('home.actions.libraryText')}
          action={t('home.actions.openLibrary')}
          onClick={() => navigate('bibliothek')}
          color="secondary"
        />
      </SimpleGrid>
    </Box>
  )
}
