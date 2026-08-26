import { useMemo, useState } from 'react'
import { Alert, Badge, Box, Button, Group, Paper, Progress, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle, IconArrowLeft, IconArrowRight, IconSparkles } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import InfoView from '../components/learning/InfoView'
import Quiz from '../components/learning/Quiz'
import { ONBOARDING, pickLang } from './content'

/**
 * Onboarding flow embedded in the Basics page. Runs sequentially through the
 * chapters (info -> chapter quiz) and finally through the final quiz.
 * Only afterwards is the profile flag set and the daily challenges unlocked.
 *
 * Props:
 *   user, apiBase
 *   onProgress(chapterId)  - after a passed chapter (for overview sync)
 *   onComplete()           - after a passed final quiz
 *   onExit()               - back to the overview
 *   startAtBeginning       - start the flow from chapter 1 (replay) instead of resuming
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
  const { chapters, finalQuiz, passThreshold } = ONBOARDING

  // Resume: find the first chapter that has not been completed yet.
  const initialStep = useMemo(() => {
    if (startAtBeginning) return { kind: 'chapter', index: 0, view: 'info' }
    const completed = new Set(user?.onboarding_progress || [])
    const firstOpen = chapters.findIndex((chapter) => !completed.has(chapter.id))
    if (firstOpen === -1) return { kind: 'final' }
    return { kind: 'chapter', index: firstOpen, view: 'info' }
  }, [chapters, user, startAtBeginning])

  const [step, setStep] = useState(initialStep)
  const [saveError, setSaveError] = useState('')
  const [saving, setSaving] = useState(false)

  // Progress only counts once the server has confirmed it. The previous version
  // swallowed every failure and advanced anyway, so a passed chapter could be
  // gone after the next reload without the user ever seeing a warning.
  const post = async (path, body) => {
    let response
    try {
      response = await fetch(`${apiBase}/api/auth/onboarding/${path}/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      })
    } catch {
      throw new Error(t('onboarding.saveNetworkError'))
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.error || t('onboarding.saveError'))
    }
  }

  const startQuiz = () => setStep((s) => ({ ...s, view: 'quiz' }))

  const handleChapterPassed = async (index) => {
    setSaveError('')
    setSaving(true)
    try {
      await post('progress', { chapter: chapters[index].id })
      onProgress?.(chapters[index].id)
      if (index + 1 < chapters.length) {
        setStep({ kind: 'chapter', index: index + 1, view: 'info' })
      } else {
        setStep({ kind: 'final' })
      }
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleFinalPassed = async () => {
    setSaveError('')
    setSaving(true)
    try {
      await post('complete')
      onComplete?.()
    } catch (error) {
      setSaveError(error.message)
    } finally {
      setSaving(false)
    }
  }

  // --- Display metadata (progress bar, title) --------------------------------
  const totalSteps = chapters.length + 1
  const isFinal = step.kind === 'final'
  const currentStepNumber = isFinal ? totalSteps : step.index + 1
  const headerLabel = isFinal
    ? t('onboarding.finalTitle')
    : t('onboarding.chapterProgress', { current: step.index + 1, total: chapters.length })
  // The big heading names the chapter you are actually in. It used to be a
  // static string, so "Willkommen an Bord" sat above every chapter.
  const headerTitle = isFinal
    ? t('onboarding.finalHeading')
    : pickLang(chapters[step.index].title, lang)

  // --- Content ---------------------------------------------------------------
  let content
  if (isFinal) {
    content = (
      <Stack gap="lg">
        <Stack gap={4}>
          <Title order={3} c="secondary.9">
            {t('onboarding.finalHeading')}
          </Title>
          <Text c="dimmed">{t('onboarding.finalSubtitle')}</Text>
        </Stack>
        <Quiz
          questions={pickLang(finalQuiz, lang)}
          passThreshold={passThreshold}
          onPassed={handleFinalPassed}
          continueLoading={saving}
          continueLabel={t('onboarding.finish')}
        />
      </Stack>
    )
  } else if (step.view === 'info') {
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
        continueLoading={saving}
        continueLabel={
          step.index + 1 < chapters.length ? t('onboarding.next') : t('onboarding.toFinal')
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
          {headerTitle}
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

      {saveError && (
        <Alert color="red" icon={<IconAlertTriangle size={18} />} title={t('onboarding.saveErrorTitle')} mb="lg">
          <Text fz="sm">{saveError}</Text>
        </Alert>
      )}

      {/* Content card */}
      <Paper withBorder radius="lg" p={{ base: 'lg', md: 36 }} bg="white">
        <Box key={`${step.kind}-${step.index}-${step.view}`} className="fade-up">
          {content}
        </Box>
      </Paper>
    </Box>
  )
}
