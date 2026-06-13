import { useMemo, useState } from 'react'
import {
  Badge,
  Box,
  Button,
  Divider,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconArrowLeft,
  IconArrowRight,
  IconChecklist,
  IconClock,
  IconRefresh,
  IconTargetArrow,
  IconTrophy,
} from '@tabler/icons-react'
import { MISSIONS, getMissionById } from '../data/missions'
import { useUserProgress } from '../hooks/useUserProgress'
import { completeMission } from '../services/progressService'

const PROMPT_QUESTIONS = [
  {
    question: 'Du moechtest einen Monatsabschlussbericht mit AI zusammenfassen. Welche Prompt-Variante ist am besten?',
    options: [
      'Fasse diesen Monatsabschlussbericht kurz zusammen.',
      'Fasse diesen Monatsabschlussbericht in fuenf Bullet Points zusammen, hebe Abweichungen zum Vormonat hervor und nenne moegliche Ursachen.',
      'Welche Zahlen sind wichtig?',
    ],
    correct: 1,
  },
  {
    question: 'Du moechtest Buchungsdaten auf Auffaelligkeiten pruefen. Welche Anfrage ist am staerksten?',
    options: [
      'Pruefe diese Buchungen.',
      'Analysiere die Buchungsdaten auf ungewoehnliche Muster, nutze Betrag, Konto, Kostenstelle und Buchungsdatum als Kontext und gib die Top 5 Auffaelligkeiten als Tabelle aus.',
      'Finde Fehler in der Datei.',
    ],
    correct: 1,
  },
  {
    question: 'Du brauchst eine Management Summary fuer Finance Leads. Welche Variante passt am besten?',
    options: [
      'Schreibe eine Summary fuer das Management.',
      'Erstelle eine sachliche Management Summary fuer Finance Leads mit maximal 120 Woertern, Fokus auf Ergebnisabweichungen, Risiken und naechste Entscheidungen.',
      'Mach den Text kuerzer und professionell.',
    ],
    correct: 1,
  },
]

const COMPLIANCE_SCENARIOS = [
  {
    text: 'Ein Mitarbeiter kopiert personenbezogene Gehaltsdaten in ein oeffentliches AI-Tool.',
    correct: 'Nicht erlaubt',
    feedback: 'Personenbezogene und vertrauliche Daten gehoeren nicht in oeffentliche AI-Tools.',
  },
  {
    text: 'Ein Controller nutzt anonymisierte Kostenstellendaten zur Trendanalyse mit einem freigegebenen Enterprise-AI-Tool.',
    correct: 'Erlaubt',
    feedback: 'Anonymisierte Daten in einem freigegebenen Enterprise-Tool sind fuer diese Analyse geeignet.',
  },
  {
    text: 'Eine Mitarbeiterin moechte interne Buchungsdaten ohne Personenbezug in ein zugelassenes internes AI-Tool hochladen.',
    correct: 'Erlaubt',
    feedback: 'Ein zugelassenes internes Tool und Daten ohne Personenbezug sind hier entscheidend.',
  },
  {
    text: 'Ein Monatsbericht mit vertraulichen Kommentaren wird in ein externes oeffentliches AI-Tool eingefuegt.',
    correct: 'Nicht erlaubt',
    feedback: 'Vertrauliche interne Kommentare duerfen nicht in ein oeffentliches Tool uebertragen werden.',
  },
]

const COMPLIANCE_OPTIONS = ['Erlaubt', 'Nicht erlaubt', 'Nur mit anonymisierten Daten']

function MissionCard({ mission, progress, onStart }) {
  const isCompleted = progress.completedMissions.includes(mission.id)
  const bestScore = progress.missionScores[mission.id] || 0

  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Stack gap="md" h="100%">
        <Group justify="space-between" align="flex-start">
          <ThemeIcon size={46} radius="md" variant="light" color="brand">
            <IconTargetArrow size={24} stroke={1.7} />
          </ThemeIcon>
          <Badge color={isCompleted ? 'green' : 'secondary'} variant="light">
            {isCompleted ? 'Abgeschlossen' : 'Offen'}
          </Badge>
        </Group>

        <Box style={{ flex: 1 }}>
          <Text fw={700} c="secondary.9" fz="lg">
            {mission.title}
          </Text>
          <Text c="dimmed" fz="sm" mt={4}>
            {mission.description}
          </Text>
        </Box>

        <Group gap="xs">
          <Badge color="brand" variant="light">
            {mission.category}
          </Badge>
          <Badge color="secondary" variant="light">
            {mission.difficulty}
          </Badge>
        </Group>

        <Group justify="space-between" c="dimmed">
          <Group gap={6}>
            <IconClock size={16} stroke={1.8} />
            <Text fz="sm">{mission.estimatedTime}</Text>
          </Group>
          <Text fz="sm" fw={600}>
            {bestScore}/{mission.maxPoints} Punkte
          </Text>
        </Group>

        <Button
          color="brand"
          variant={isCompleted ? 'light' : 'filled'}
          rightSection={isCompleted ? <IconRefresh size={17} /> : <IconArrowRight size={17} />}
          onClick={() => onStart(mission.id)}
        >
          {isCompleted ? 'Erneut spielen' : 'Starten'}
        </Button>
      </Stack>
    </Paper>
  )
}

function AnswerButton({ selected, correct, showResult, children, onClick }) {
  const color = showResult && correct ? 'green' : selected ? 'brand' : 'gray'

  return (
    <Button
      fullWidth
      justify="flex-start"
      variant={selected ? 'light' : 'default'}
      color={color}
      radius="md"
      onClick={onClick}
      styles={{ label: { whiteSpace: 'normal', textAlign: 'left', lineHeight: 1.35 } }}
    >
      {children}
    </Button>
  )
}

function PromptQualityQuiz({ mission, userId, progress, onDone, onBack }) {
  const [answers, setAnswers] = useState({})

  const answeredCount = Object.keys(answers).length
  const correctCount = PROMPT_QUESTIONS.filter((item, index) => answers[index] === item.correct).length
  const score = Math.round((correctCount / PROMPT_QUESTIONS.length) * mission.maxPoints)
  const canSubmit = answeredCount === PROMPT_QUESTIONS.length

  const submit = () => {
    const nextProgress = completeMission(userId, mission.id, score)
    onDone({ score, correctCount, total: PROMPT_QUESTIONS.length, progress: nextProgress })
  }

  return (
    <MissionRunnerShell mission={mission} onBack={onBack}>
      {PROMPT_QUESTIONS.map((item, index) => (
        <Paper key={item.question} withBorder radius="lg" p="lg" bg="white">
          <Stack gap="md">
            <Text fw={700} c="secondary.9">
              Frage {index + 1}
            </Text>
            <Text c="secondary.9">{item.question}</Text>
            <Stack gap="sm">
              {item.options.map((option, optionIndex) => (
                <AnswerButton
                  key={option}
                  selected={answers[index] === optionIndex}
                  onClick={() => setAnswers((current) => ({ ...current, [index]: optionIndex }))}
                >
                  {option}
                </AnswerButton>
              ))}
            </Stack>
          </Stack>
        </Paper>
      ))}

      <Group justify="space-between">
        <Text c="dimmed" fz="sm">
          {answeredCount}/{PROMPT_QUESTIONS.length} beantwortet · Best Score:{' '}
          {progress.missionScores[mission.id] || 0}
        </Text>
        <Button color="brand" disabled={!canSubmit} rightSection={<IconTrophy size={17} />} onClick={submit}>
          Abschliessen
        </Button>
      </Group>
    </MissionRunnerShell>
  )
}

function ComplianceChallenge({ mission, userId, progress, onDone, onBack }) {
  const [answers, setAnswers] = useState({})

  const answeredCount = Object.keys(answers).length
  const correctCount = COMPLIANCE_SCENARIOS.filter((item, index) => answers[index] === item.correct).length
  const score = Math.round((correctCount / COMPLIANCE_SCENARIOS.length) * mission.maxPoints)
  const canSubmit = answeredCount === COMPLIANCE_SCENARIOS.length

  const submit = () => {
    const nextProgress = completeMission(userId, mission.id, score)
    onDone({ score, correctCount, total: COMPLIANCE_SCENARIOS.length, progress: nextProgress })
  }

  return (
    <MissionRunnerShell mission={mission} onBack={onBack}>
      {COMPLIANCE_SCENARIOS.map((item, index) => {
        const selected = answers[index]
        const showFeedback = Boolean(selected)

        return (
          <Paper key={item.text} withBorder radius="lg" p="lg" bg="white">
            <Stack gap="md">
              <Text fw={700} c="secondary.9">
                Szenario {index + 1}
              </Text>
              <Text c="secondary.9">{item.text}</Text>
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
                {COMPLIANCE_OPTIONS.map((option) => (
                  <AnswerButton
                    key={option}
                    selected={selected === option}
                    correct={option === item.correct}
                    showResult={showFeedback}
                    onClick={() => setAnswers((current) => ({ ...current, [index]: option }))}
                  >
                    {option}
                  </AnswerButton>
                ))}
              </SimpleGrid>
              {showFeedback && (
                <Text fz="sm" c={selected === item.correct ? 'green.7' : 'red.7'}>
                  {selected === item.correct ? 'Richtig. ' : 'Nicht ganz. '}
                  {item.feedback}
                </Text>
              )}
            </Stack>
          </Paper>
        )
      })}

      <Group justify="space-between">
        <Text c="dimmed" fz="sm">
          {answeredCount}/{COMPLIANCE_SCENARIOS.length} beantwortet · Best Score:{' '}
          {progress.missionScores[mission.id] || 0}
        </Text>
        <Button color="brand" disabled={!canSubmit} rightSection={<IconTrophy size={17} />} onClick={submit}>
          Abschliessen
        </Button>
      </Group>
    </MissionRunnerShell>
  )
}

function MissionRunnerShell({ mission, onBack, children }) {
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={960}>
      <Button variant="subtle" color="secondary" leftSection={<IconArrowLeft size={17} />} mb="lg" onClick={onBack}>
        Zurueck zu Missions
      </Button>
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
            <Badge color="yellow" variant="light" style={{ background: 'rgba(var(--gold-rgb),0.16)', color: 'var(--gold-soft)' }}>
              {mission.category}
            </Badge>
            <Badge color="gray" variant="light">
              {mission.difficulty}
            </Badge>
          </Group>
          <Title order={1} fz={{ base: 28, md: 36 }}>
            {mission.title}
          </Title>
          <Text c="rgba(255,255,255,0.78)" maw={680}>
            {mission.description}
          </Text>
        </Stack>
      </Paper>
      <Stack gap="lg">{children}</Stack>
    </Box>
  )
}

function MissionResult({ mission, result, navigate, onBack, onReplay }) {
  const previousBest = result.progress.missionScores[mission.id] || 0
  const improved = result.score >= previousBest

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={820}>
      <Paper withBorder radius="lg" p={{ base: 'xl', md: 36 }} bg="white">
        <Stack gap="lg">
          <ThemeIcon size={58} radius="xl" variant="light" color="accent">
            <IconChecklist size={30} stroke={1.7} />
          </ThemeIcon>
          <Box>
            <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
              Mission abgeschlossen
            </Title>
            <Text c="dimmed" mt={6}>
              {result.correctCount}/{result.total} Antworten korrekt · {result.score} Punkte in diesem Durchlauf
            </Text>
          </Box>
          <Divider />
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <Box>
              <Text fz="sm" c="dimmed">
                Gespeicherter Best Score
              </Text>
              <Text fz={30} fw={700} c="secondary.9" ff="var(--font-display)">
                {previousBest}/{mission.maxPoints}
              </Text>
            </Box>
            <Box>
              <Text fz="sm" c="dimmed">
                Gesamtpunkte
              </Text>
              <Text fz={30} fw={700} c="secondary.9" ff="var(--font-display)">
                {result.progress.totalPoints}
              </Text>
            </Box>
          </SimpleGrid>
          <Text c="dimmed">
            {improved
              ? 'Dein Ergebnis wurde gespeichert. Bei Replays zaehlt immer dein bester Score.'
              : 'Dein bisheriger Best Score bleibt erhalten, weil dieser Durchlauf niedriger war.'}
          </Text>
          <Group>
            <Button color="brand" onClick={onBack}>
              Zurueck zu Missions
            </Button>
            <Button variant="light" color="brand" leftSection={<IconRefresh size={17} />} onClick={onReplay}>
              Erneut spielen
            </Button>
            <Button variant="subtle" color="secondary" onClick={() => navigate('home')}>
              Zu Home
            </Button>
          </Group>
        </Stack>
      </Paper>
    </Box>
  )
}

export default function Missions({ user, navigate, startMissionId }) {
  const { userId, progress } = useUserProgress(user)
  const [activeMissionId, setActiveMissionId] = useState(startMissionId || null)
  const [result, setResult] = useState(null)

  const mission = useMemo(() => getMissionById(activeMissionId), [activeMissionId])

  const startMission = (missionId) => {
    setActiveMissionId(missionId)
    setResult(null)
  }

  const backToOverview = () => {
    setActiveMissionId(null)
    setResult(null)
  }

  if (mission && result) {
    return (
      <MissionResult
        mission={mission}
        result={result}
        navigate={navigate}
        onBack={backToOverview}
        onReplay={() => startMission(mission.id)}
      />
    )
  }

  if (mission?.id === 'prompt-quality-quiz') {
    return (
      <PromptQualityQuiz
        mission={mission}
        userId={userId}
        progress={progress}
        onDone={setResult}
        onBack={backToOverview}
      />
    )
  }

  if (mission?.id === 'compliance-check-challenge') {
    return (
      <ComplianceChallenge
        mission={mission}
        userId={userId}
        progress={progress}
        onDone={setResult}
        onBack={backToOverview}
      />
    )
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      <Stack gap={6} mb="xl">
        <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
          Missions
        </Title>
        <Text fz="lg" c="dimmed" maw={680}>
          Spiele kurze Finance-Missions, sammle Punkte und verbessere deinen Best Score.
        </Text>
      </Stack>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" mb="xl">
        {MISSIONS.map((item) => (
          <MissionCard key={item.id} mission={item} progress={progress} onStart={startMission} />
        ))}
      </SimpleGrid>
    </Box>
  )
}