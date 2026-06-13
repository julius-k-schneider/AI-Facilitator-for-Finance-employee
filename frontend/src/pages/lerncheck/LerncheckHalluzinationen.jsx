import { useState } from 'react'
import {
  Box,
  Button,
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Title,
  Badge,
  Divider,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconBook,
  IconChecklist,
  IconRefresh,
  IconTrophy,
} from '@tabler/icons-react'
import { HALLUZINATIONEN_LERNCHECK } from '../../data/lerncheck/halluzinationen'
import { completeMission } from '../../services/progressService'

function TextReader({ lerncheck, onStartQuiz }) {
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={820}>
      <Paper
        radius="xl"
        p={{ base: 'xl', md: 34 }}
        mb="lg"
        style={{
          background:
            'linear-gradient(135deg, var(--mantine-color-secondary-7) 0%, var(--mantine-color-secondary-6) 70%, var(--mantine-color-brand-7) 135%)',
          color: '#fff',
        }}
      >
        <Stack gap="sm">
          <Group gap="xs">
            <Badge color="yellow" variant="light">
              {lerncheck.category}
            </Badge>
            <Badge color="gray" variant="light">
              {lerncheck.difficulty}
            </Badge>
          </Group>
          <Title order={1} fz={{ base: 28, md: 36 }}>
            {lerncheck.title}
          </Title>
          <Text c="rgba(255,255,255,0.78)">
            {lerncheck.description}
          </Text>
        </Stack>
      </Paper>

      <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white" mb="lg">
        <Group gap="sm" mb="md">
          <ThemeIcon size={32} radius="md" variant="light" color="brand">
            <IconBook size={18} />
          </ThemeIcon>
          <Text fw={700} c="secondary.9" fz="lg">
            Lerntext
          </Text>
        </Group>
        <Divider mb="md" />
        <Text c="secondary.9" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {lerncheck.text.replace(/##|###|\*\*/g, '').trim()}
        </Text>
      </Paper>

      <Button
        color="brand"
        size="md"
        rightSection={<IconArrowRight size={18} />}
        onClick={onStartQuiz}
      >
        Zum Quiz
      </Button>
    </Box>
  )
}

function QuizRunner({ lerncheck, userId, progress, onDone, onBack }) {
  const [answers, setAnswers] = useState({})
  const questions = lerncheck.questions
  const answeredCount = Object.keys(answers).length
  const canSubmit = answeredCount === questions.length

  const correctCount = questions.filter(
    (q, i) => answers[i] === q.correctIndex
  ).length
  const score = Math.round((correctCount / questions.length) * lerncheck.maxPoints)

  const submit = () => {
    const nextProgress = completeMission(userId, lerncheck.id, score)
    onDone({ score, correctCount, total: questions.length, progress: nextProgress })
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={820}>
      <Button
        variant="subtle"
        color="secondary"
        leftSection={<IconArrowLeft size={17} />}
        mb="lg"
        onClick={onBack}
      >
        Zurück zum Text
      </Button>

      <Stack gap="lg">
        {questions.map((item, index) => (
          <Paper key={index} withBorder radius="lg" p="lg" bg="white">
            <Stack gap="md">
              <Text fw={700} c="secondary.9">
                Frage {index + 1}
              </Text>
              <Text c="secondary.9">{item.question}</Text>
              <Stack gap="sm">
                {item.options.map((option, optionIndex) => (
                  <Button
                    key={option}
                    fullWidth
                    justify="flex-start"
                    variant={answers[index] === optionIndex ? 'light' : 'default'}
                    color={answers[index] === optionIndex ? 'brand' : 'gray'}
                    radius="md"
                    onClick={() => setAnswers((current) => ({ ...current, [index]: optionIndex }))}
                    styles={{ label: { whiteSpace: 'normal', textAlign: 'left', lineHeight: 1.35 } }}
                  >
                    {option}
                  </Button>
                ))}
              </Stack>
            </Stack>
          </Paper>
        ))}

        <Group justify="space-between">
          <Text c="dimmed" fz="sm">
            {answeredCount}/{questions.length} beantwortet
          </Text>
          <Button
            color="brand"
            disabled={!canSubmit}
            rightSection={<IconTrophy size={17} />}
            onClick={submit}
          >
            Abschliessen
          </Button>
        </Group>
      </Stack>
    </Box>
  )
}

function LerncheckResult({ lerncheck, result, onBack, onReplay }) {
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={820}>
      <Paper withBorder radius="lg" p={{ base: 'xl', md: 36 }} bg="white">
        <Stack gap="lg">
          <ThemeIcon size={58} radius="xl" variant="light" color="accent">
            <IconChecklist size={30} stroke={1.7} />
          </ThemeIcon>
          <Box>
            <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
              Lerncheck abgeschlossen!
            </Title>
            <Text c="dimmed" mt={6}>
              {result.correctCount}/{result.total} Antworten korrekt · {result.score} Punkte
            </Text>
          </Box>
          <Divider />
          <Text c="secondary.9">
            {result.correctCount === result.total
              ? 'Ausgezeichnet! Du hast alle Fragen richtig beantwortet.'
              : result.correctCount >= result.total / 2
              ? 'Gut gemacht! Lies den Text nochmal, um dein Wissen zu vertiefen.'
              : 'Lies den Text nochmal und versuche es erneut.'}
          </Text>
          <Group>
            <Button color="brand" onClick={onBack}>
              Zurück zu Missions
            </Button>
            <Button
              variant="light"
              color="brand"
              leftSection={<IconRefresh size={17} />}
              onClick={onReplay}
            >
              Erneut versuchen
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Box>
  )
}

export default function LerncheckHalluzinationen({ userId, progress, onBack }) {
  const [phase, setPhase] = useState('text')
  const [result, setResult] = useState(null)

  if (result) {
    return (
      <LerncheckResult
        lerncheck={HALLUZINATIONEN_LERNCHECK}
        result={result}
        onBack={onBack}
        onReplay={() => { setPhase('text'); setResult(null) }}
      />
    )
  }

  if (phase === 'quiz') {
    return (
      <QuizRunner
        lerncheck={HALLUZINATIONEN_LERNCHECK}
        userId={userId}
        progress={progress}
        onDone={setResult}
        onBack={() => setPhase('text')}
      />
    )
  }

  return (
    <TextReader
      lerncheck={HALLUZINATIONEN_LERNCHECK}
      onStartQuiz={() => setPhase('quiz')}
    />
  )
}