import { useState } from 'react'
import { Alert, Box, Button, Group, Stack, Text, ThemeIcon, UnstyledButton } from '@mantine/core'
import { IconCheck, IconX } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'

/**
 * Datengetriebene Single-Choice-Frage.
 *
 * Props: { question, choices: [], correctIndex, explanation, onAnswered }
 * Nach dem Absenden wird richtig/falsch + Erklärung aufgedeckt und
 * `onAnswered(isCorrect)` aufgerufen. Wird im Onboarding wie später in den
 * Daily Challenges verwendet.
 */
export default function QuizCard({ question, choices = [], correctIndex, explanation, onAnswered }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const isCorrect = selected === correctIndex

  const submit = () => {
    if (selected === null || submitted) return
    setSubmitted(true)
    onAnswered?.(selected === correctIndex)
  }

  const choiceStyle = (index) => {
    const chosen = selected === index
    let borderColor = 'var(--line)'
    let background = '#fff'

    if (submitted) {
      if (index === correctIndex) {
        borderColor = 'var(--mantine-color-green-5)'
        background = 'var(--mantine-color-green-0)'
      } else if (chosen) {
        borderColor = 'var(--mantine-color-red-5)'
        background = 'var(--mantine-color-red-0)'
      }
    } else if (chosen) {
      borderColor = 'var(--mantine-color-brand-5)'
      background = 'var(--mantine-color-brand-0)'
    }

    return {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      width: '100%',
      padding: '13px 16px',
      borderRadius: 12,
      border: `1.5px solid ${borderColor}`,
      background,
      cursor: submitted ? 'default' : 'pointer',
      transition: 'border-color 140ms ease, background 140ms ease',
    }
  }

  const feedbackIcon = (index) => {
    if (!submitted) return null
    if (index === correctIndex) {
      return (
        <ThemeIcon size={22} radius="xl" color="green" variant="filled">
          <IconCheck size={14} />
        </ThemeIcon>
      )
    }
    if (selected === index) {
      return (
        <ThemeIcon size={22} radius="xl" color="red" variant="filled">
          <IconX size={14} />
        </ThemeIcon>
      )
    }
    return null
  }

  return (
    <Stack gap="lg">
      <Text fz={{ base: 17, md: 18 }} fw={600} c="secondary.9" lh={1.4}>
        {question}
      </Text>

      <Stack gap="sm">
        {choices.map((choice, index) => (
          <UnstyledButton
            key={index}
            onClick={() => !submitted && setSelected(index)}
            style={choiceStyle(index)}
          >
            <Box style={{ flex: 1 }}>
              <Text fz={{ base: 15, md: 16 }} c="secondary.9">
                {choice}
              </Text>
            </Box>
            {feedbackIcon(index)}
          </UnstyledButton>
        ))}
      </Stack>

      {!submitted ? (
        <Button color="brand" w="fit-content" disabled={selected === null} onClick={submit}>
          {t('onboarding.checkAnswer')}
        </Button>
      ) : (
        <Alert
          color={isCorrect ? 'green' : 'red'}
          variant="light"
          radius="md"
          icon={isCorrect ? <IconCheck size={18} /> : <IconX size={18} />}
          title={isCorrect ? t('onboarding.correct') : t('onboarding.wrong')}
        >
          {explanation && (
            <Group gap={6} align="flex-start" wrap="nowrap">
              <Text fz="sm" fw={700} c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                {t('onboarding.explanation')}:
              </Text>
              <Text fz="sm" c="secondary.9">
                {explanation}
              </Text>
            </Group>
          )}
        </Alert>
      )}
    </Stack>
  )
}
