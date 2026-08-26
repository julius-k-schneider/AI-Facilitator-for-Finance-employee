import { useState } from 'react'
import { Box, Button, Group, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconArrowRight, IconCheck, IconRefresh, IconX } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import QuizCard from './QuizCard'

/**
 * Runner over a list of single-choice questions.
 *
 * Runs the questions sequentially, counts the correct answers and compares the
 * ratio with `passThreshold` (0..1). On passing, `onPassed()` is invoked via a
 * button, otherwise "Try again" is shown. Reusable for chapter and final
 * quizzes as well as later daily challenges.
 *
 * Props: { questions: [], passThreshold = 0.8, onPassed, continueLabel }
 */
export default function Quiz({ questions = [], passThreshold = 0.8, onPassed, continueLabel, continueLoading = false }) {
  const { t } = useTranslation()
  const [index, setIndex] = useState(0)
  const [correctCount, setCorrectCount] = useState(0)
  const [answered, setAnswered] = useState(false)
  const [finished, setFinished] = useState(false)

  const total = questions.length
  const current = questions[index]
  const isLast = index === total - 1

  const handleAnswered = (isCorrect) => {
    setAnswered(true)
    if (isCorrect) setCorrectCount((count) => count + 1)
  }

  const handleNext = () => {
    if (isLast) {
      setFinished(true)
      return
    }
    setIndex((i) => i + 1)
    setAnswered(false)
  }

  const reset = () => {
    setIndex(0)
    setCorrectCount(0)
    setAnswered(false)
    setFinished(false)
  }

  if (finished) {
    const passed = total > 0 && correctCount / total >= passThreshold
    return (
      <Stack align="center" gap="lg" py="md">
        <ThemeIcon size={72} radius="xl" variant="light" color={passed ? 'green' : 'red'}>
          {passed ? <IconCheck size={38} stroke={1.8} /> : <IconX size={38} stroke={1.8} />}
        </ThemeIcon>
        <Stack align="center" gap={4}>
          <Title order={3} c="secondary.9">
            {passed ? t('onboarding.quizPassed') : t('onboarding.quizFailed')}
          </Title>
          <Text c="dimmed">
            {t('onboarding.score', { correct: correctCount, total })}
          </Text>
        </Stack>
        {passed ? (
          <Button
            color="brand"
            size="md"
            loading={continueLoading}
            rightSection={<IconArrowRight size={18} />}
            onClick={onPassed}
          >
            {continueLabel || t('onboarding.next')}
          </Button>
        ) : (
          <Button
            variant="default"
            size="md"
            leftSection={<IconRefresh size={18} />}
            onClick={reset}
          >
            {t('onboarding.retry')}
          </Button>
        )}
      </Stack>
    )
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="center">
        <Text fz="xs" fw={700} c="brand.6" style={{ letterSpacing: '0.08em' }}>
          {t('onboarding.questionProgress', { current: index + 1, total }).toUpperCase()}
        </Text>
      </Group>

      {/* key forces fresh state per question */}
      <QuizCard
        key={index}
        question={current.question}
        choices={current.choices}
        correctIndex={current.correctIndex}
        explanation={current.explanation}
        onAnswered={handleAnswered}
      />

      {answered && (
        <Box>
          <Button
            color="brand"
            w="fit-content"
            rightSection={<IconArrowRight size={18} />}
            onClick={handleNext}
          >
            {isLast ? t('onboarding.showResult') : t('onboarding.next')}
          </Button>
        </Box>
      )}
    </Stack>
  )
}
