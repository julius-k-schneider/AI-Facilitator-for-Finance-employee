import { useMemo, useState } from 'react'
import { Badge, Box, Button, Group, Paper, Progress, Stack, Text, Title } from '@mantine/core'
import { IconArrowLeft, IconArrowRight, IconSparkles } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import InfoView from '../components/learning/InfoView'
import Quiz from '../components/learning/Quiz'
import { ONBOARDING, pickLang } from './content'

/**
 * Onboarding flow embedded in the Basics page. Runs sequentially through the
 * chapters (info → chapter quiz). Once the last chapter is passed, the profile
 * flag is set and the daily challenges are unlocked.
 *
 * Props:
 *   user, apiBase
 *   onProgress(chapterId)  – after a passed chapter (for overview sync)
 *   onComplete()           – after the last chapter has been passed
 *   onExit()               – back to the overview
 *   startAtBeginning       – start the flow from chapter 1 (replay) instead of resuming
 */
export default function OnboardingFlow({
  user,
  apiBase,
  onProgress,
  onComplete,
  onExit,
  startAtBeginning = false,
}) {
  const { t, i18n } = useTranslation()
  const lang = (i18n.language || 'de').split('-')[0]
  const { chapters, passThreshold } = ONBOARDING

  // Resume: find the first chapter that has not been completed yet.
  const initialStep = useMemo(() => {
    if (startAtBeginning) return { index: 0, view: 'info' }
    const completed = new Set(user?.onboarding_progress || [])
    const firstOpen = chapters.findIndex((chapter) => !completed.has(chapter.id))
    // All chapters read but the flag not set yet (legacy: final quiz still open)
    // → resume on the last chapter so passing it completes the onboarding.
    const index = firstOpen === -1 ? chapters.length - 1 : firstOpen
    return { index, view: 'info' }
  }, [chapters, user, startAtBeginning])

  const [step, setStep] = useState(initialStep)

  const post = (path, body) =>
    fetch(`${apiBase}/api/auth/onboarding/${path}/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    }).catch(() => null)

  const startQuiz = () => setStep((s) => ({ ...s, view: 'quiz' }))

  const handleChapterPassed = async (index) => {
    await post('progress', { chapter: chapters[index].id })
    onProgress?.(chapters[index].id)
    if (index + 1 < chapters.length) {
      setStep({ index: index + 1, view: 'info' })
      return
    }
    // Last chapter: the onboarding is done, no separate final quiz.
    await post('complete')
    onComplete?.()
  }

  // --- Display metadata (progress bar, title) --------------------------------
  const totalSteps = chapters.length
  const currentStepNumber = step.index + 1
  const headerLabel = t('onboarding.chapterProgress', {
    current: currentStepNumber,
    total: totalSteps,
  })

  // --- Content ---------------------------------------------------------------
  let content
  if (step.view === 'info') {
    content = (
      <Stack gap="xl">
        <InfoView blocks={pickLang(chapters[step.index].info, lang)} />
        <Group>
          <Button
            color="brand"
            size="md"
            rightSection={<IconArrowRight size={18} />}
            onClick={startQuiz}
          >
            {t('onboarding.startQuiz')}
          </Button>
        </Group>
      </Stack>
    )
  } else {
    content = (
      <Quiz
        key={`chapter-${step.index}`}
        questions={pickLang(chapters[step.index].quiz, lang)}
        passThreshold={passThreshold}
        onPassed={() => handleChapterPassed(step.index)}
        continueLabel={
          step.index + 1 < chapters.length ? t('onboarding.next') : t('onboarding.finish')
        }
      />
    )
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={820} mx="auto">
      {/* Branding header with progress */}
      <Box
        p={{ base: 'lg', md: 'xl' }}
        mb="lg"
        style={{
          borderRadius: 18,
          background:
            'linear-gradient(135deg, var(--mantine-color-secondary-7) 0%, var(--mantine-color-secondary-6) 55%, var(--mantine-color-brand-7) 135%)',
          color: '#fff',
        }}
      >
        <Group justify="space-between" align="center" mb="lg">
          {onExit ? (
            <Button
              variant="white"
              color="dark"
              size="xs"
              radius="md"
              leftSection={<IconArrowLeft size={15} />}
              onClick={onExit}
              styles={{ root: { background: 'rgba(255,255,255,0.14)', color: '#fff' } }}
            >
              {t('onboarding.backToOverview')}
            </Button>
          ) : (
            <span />
          )}
          <Badge
            variant="light"
            size="lg"
            radius="sm"
            leftSection={<IconSparkles size={14} />}
            style={{ background: 'rgba(var(--gold-rgb),0.16)', color: 'var(--gold-soft)' }}
          >
            {t('onboarding.badge')}
          </Badge>
        </Group>
        <Text fz={11} fw={700} style={{ letterSpacing: '0.12em', opacity: 0.7 }}>
          {headerLabel.toUpperCase()}
        </Text>
        <Title order={2} fz={{ base: 22, md: 28 }} fw={600} mt={4} mb="md">
          {t('onboarding.title')}
        </Title>
        <Progress
          value={(currentStepNumber / totalSteps) * 100}
          color="accent"
          size="sm"
          radius="xl"
          styles={{ root: { background: 'rgba(255,255,255,0.15)' } }}
        />
        <Text fz="xs" mt={6} style={{ opacity: 0.7 }}>
          {t('onboarding.stepOf', { current: currentStepNumber, total: totalSteps })}
        </Text>
      </Box>

      {/* Content card */}
      <Paper withBorder radius="lg" p={{ base: 'lg', md: 36 }} bg="white">
        <Box key={`${step.index}-${step.view}`} className="fade-up">
          {content}
        </Box>
      </Paper>
    </Box>
  )
}
