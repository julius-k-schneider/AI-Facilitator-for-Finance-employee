import {
  Alert,
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Progress,
  Stack,
  Text,
  ThemeIcon,
} from '@mantine/core'
import {
  IconArrowRight,
  IconCheck,
  IconCircleDashed,
  IconLock,
  IconPlayerPlay,
  IconRefresh,
  IconRosetteDiscountCheck,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import PageShell from './PageShell'
import { ONBOARDING, pickLang } from '../onboarding/content'
import OnboardingFlow from '../onboarding/OnboardingFlow'

function ChapterRow({ chapter, done, lang }) {
  return (
    <Group gap="md" wrap="nowrap" align="flex-start">
      <ThemeIcon
        size={32}
        radius="xl"
        variant={done ? 'filled' : 'light'}
        color={done ? 'green' : 'gray'}
      >
        {done ? <IconCheck size={18} /> : <IconCircleDashed size={18} />}
      </ThemeIcon>
      <Box style={{ flex: 1, minWidth: 0 }}>
        <Text fw={600} c="secondary.9">
          {pickLang(chapter.title, lang)}
        </Text>
        {chapter.summary && (
          <Text fz="sm" c="dimmed">
            {pickLang(chapter.summary, lang)}
          </Text>
        )}
      </Box>
    </Group>
  )
}

export default function Basics({ user, onUserUpdate, apiBase }) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'de').split('-')[0]
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  // The running flow is a route of its own, so browser Back leaves the flow
  // instead of the whole page, and a reload resumes where the server says.
  const running = location.pathname.endsWith('/onboarding')
  const reviewing = searchParams.get('review') === '1'
  const lockedFrom = location.state?.lockedFrom

  const chapters = ONBOARDING.chapters
  const completed = new Set(user?.onboarding_progress || [])
  const doneCount = chapters.filter((chapter) => completed.has(chapter.id)).length
  const allDone = Boolean(user?.onboarding_completed)
  const started = doneCount > 0
  const totalSteps = chapters.length + 1
  // Completed steps including the final quiz once everything is done.
  const completedSteps = allDone ? totalSteps : doneCount
  const progressValue = (completedSteps / totalSteps) * 100

  const markProgress = (chapterId) =>
    onUserUpdate((current) => ({
      ...current,
      onboarding_progress: Array.from(
        new Set([...(current.onboarding_progress || []), chapterId]),
      ),
    }))

  const finishOnboarding = () => {
    onUserUpdate((current) => ({ ...current, onboarding_completed: true }))
    navigate('/basics', { replace: true })
  }

  if (running) {
    return (
      <OnboardingFlow
        user={user}
        apiBase={apiBase}
        startAtBeginning={reviewing}
        onProgress={markProgress}
        onComplete={finishOnboarding}
        onExit={() => navigate('/basics')}
      />
    )
  }

  const launch = ({ review }) => navigate(`/basics/onboarding${review ? '?review=1' : ''}`)

  const primaryLabel = allDone
    ? t('onboarding.review')
    : started
      ? t('onboarding.continue')
      : t('onboarding.start')

  return (
    <PageShell title={t('pages.basics.title')} description={t('pages.basics.description')}>
      {lockedFrom && (
        <Alert color="accent" variant="light" icon={<IconLock size={18} />} mb="lg" title={t('pages.basics.lockedTitle')}>
          <Text fz="sm">{t('pages.basics.lockedText')}</Text>
        </Alert>
      )}

      <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
        <Group justify="space-between" align="flex-start" mb="lg">
          <Box>
            <Text fw={700} fz="xl" c="secondary.9">
              {t('onboarding.hubTitle')}
            </Text>
            <Text c="dimmed" fz="sm" mt={2}>
              {t('onboarding.hubSubtitle')}
            </Text>
          </Box>
          {allDone && (
            <Badge
              size="lg"
              radius="sm"
              color="green"
              variant="light"
              leftSection={<IconRosetteDiscountCheck size={15} />}
            >
              {t('onboarding.completedBadge')}
            </Badge>
          )}
        </Group>

        {/* Progress */}
        <Box mb="xl">
          <Group justify="space-between" mb={6}>
            <Text fz="sm" fw={600} c="secondary.9">
              {t('onboarding.overviewProgress', { done: completedSteps, total: totalSteps })}
            </Text>
            <Text fz="sm" c="dimmed">
              {Math.round(progressValue)}%
            </Text>
          </Group>
          <Progress value={progressValue} color={allDone ? 'green' : 'brand'} size="md" radius="xl" />
        </Box>

        {/* Chapter list */}
        <Stack gap="lg" mb="xl">
          {chapters.map((chapter) => (
            <ChapterRow
              key={chapter.id}
              chapter={chapter}
              done={completed.has(chapter.id)}
              lang={lang}
            />
          ))}
          {/* Final quiz as the last step */}
          <Group gap="md" wrap="nowrap" align="flex-start">
            <ThemeIcon
              size={32}
              radius="xl"
              variant={allDone ? 'filled' : 'light'}
              color={allDone ? 'green' : 'gray'}
            >
              {allDone ? <IconCheck size={18} /> : <IconCircleDashed size={18} />}
            </ThemeIcon>
            <Box style={{ flex: 1, minWidth: 0 }}>
              <Text fw={600} c="secondary.9">
                {t('onboarding.finalTitle')}
              </Text>
              <Text fz="sm" c="dimmed">
                {t('onboarding.finalSubtitle')}
              </Text>
            </Box>
          </Group>
        </Stack>

        <Group>
          <Button
            color="brand"
            size="md"
            leftSection={
              allDone ? <IconRefresh size={18} /> : started ? <IconArrowRight size={18} /> : <IconPlayerPlay size={18} />
            }
            onClick={() => launch({ review: allDone })}
          >
            {primaryLabel}
          </Button>
        </Group>
      </Paper>
    </PageShell>
  )
}
