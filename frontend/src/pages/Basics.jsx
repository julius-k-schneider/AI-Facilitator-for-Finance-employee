import { useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Progress,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconArrowRight,
  IconCheck,
  IconCircleDashed,
  IconPlayerPlay,
  IconRefresh,
  IconRosetteDiscountCheck,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
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
  const [running, setRunning] = useState(false)
  const [reviewing, setReviewing] = useState(false)

  const chapters = ONBOARDING.chapters
  const completed = new Set(user?.onboarding_progress || [])
  const doneCount = chapters.filter((chapter) => completed.has(chapter.id)).length
  const allDone = Boolean(user?.onboarding_completed)
  const started = doneCount > 0
  const totalSteps = chapters.length
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
    setRunning(false)
    setReviewing(false)
  }

  if (running) {
    return (
      <OnboardingFlow
        user={user}
        apiBase={apiBase}
        startAtBeginning={reviewing}
        onProgress={markProgress}
        onComplete={finishOnboarding}
        onExit={() => {
          setRunning(false)
          setReviewing(false)
        }}
      />
    )
  }

  const launch = ({ review }) => {
    setReviewing(review)
    setRunning(true)
  }

  const primaryLabel = allDone
    ? t('onboarding.review')
    : started
      ? t('onboarding.continue')
      : t('onboarding.start')

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Stack gap={6} mb="xl">
        <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
          {t('pages.basics.title')}
        </Title>
        <Text fz="lg" c="dimmed" maw={620}>
          {t('pages.basics.description')}
        </Text>
      </Stack>

      <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
        <Group justify="space-between" align="flex-start" mb="lg">
          <Box>
            <Title order={3} c="secondary.9">
              {t('onboarding.hubTitle')}
            </Title>
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
    </Box>
  )
}
