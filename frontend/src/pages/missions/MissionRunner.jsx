import { useState } from 'react'
import { Alert, Badge, Box, Button, Paper, Stack, Text, Title } from '@mantine/core'
import { IconArrowLeft, IconBulb, IconTrophy } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { submitMission } from '../../services/missionService'
import { getMissionType } from './missionTypes'

export default function MissionRunner({ mission, onBack, onCompleted = () => {}, language, testMode = false, showPoints = true, backLabel }) {
  const { t } = useTranslation()
  const definition = getMissionType(mission.type)
  const [answer, setAnswer] = useState(() => definition.initialAnswer(mission))
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      if (testMode) {
        const trainingResult = definition.submitTraining
          ? await definition.submitTraining(mission, answer, language)
          : definition.evaluateTest(mission, answer)
        setResult({ ...trainingResult, microLearning: mission.test_solution?.micro_learning })
        return
      }
      const data = await submitMission(mission.id, answer, language)
      setResult({
        ...data.result,
        feedback: data.mission.content.feedback,
        microLearning: data.mission.content.micro_learning,
      })
      onCompleted(data.mission)
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
    <Button variant="subtle" color="secondary" leftSection={<IconArrowLeft size={17} />} onClick={onBack} mb="lg">{backLabel || t('missions.back')}</Button>
    <Paper withBorder radius="lg" p={{ base: 'xl', md: 40 }} bg="white">
      <Stack gap="xl">
        <Box><Badge variant="light" color="brand" mb="sm">{t(`missions.types.${definition.labelKey}`)}</Badge><Title order={1} fz={{ base: 25, md: 32 }}>{mission.title}</Title><Text c="dimmed" mt={6}>{mission.description}</Text></Box>
        <Text fw={700} fz="lg">{mission.content.question}</Text>
        <definition.Runner mission={mission} answer={answer} setAnswer={setAnswer} result={result} t={t} />
        {error && <Alert color="red">{error}</Alert>}
        {result && <Alert color={result.correct ? 'green' : 'orange'} icon={result.correct ? <IconTrophy size={20} /> : undefined}>
          {showPoints
            ? result.correct ? t('missions.result.correct', { points: result.score }) : result.correct_count !== undefined ? t('missions.result.partial', { points: result.score, correct: result.correct_count, total: result.total_count }) : t('missions.result.wrong')
            : result.correct ? t('training.result.correct') : result.correct_count !== undefined ? t('training.result.partial', { correct: result.correct_count, total: result.total_count }) : t('training.result.wrong')}
          {typeof result.feedback === 'string' && result.feedback && !definition.ResultDetails && <Text fz="sm" mt={6}>{result.correct ? t('missions.result.correctPrefix') : t('missions.result.wrongPrefix')} {result.feedback}</Text>}
        </Alert>}
        {result && definition.ResultDetails && <definition.ResultDetails mission={mission} result={result} t={t} />}
        {result?.microLearning && <Alert color="blue" icon={<IconBulb size={20} />} title={t('missions.microLearning.title')}>
          <Text fz="sm">{result.microLearning}</Text>
        </Alert>}
        {!result && <Button color="brand" disabled={!definition.isAnswerComplete(answer)} loading={submitting} onClick={submit}>{t('missions.submit')}</Button>}
      </Stack>
    </Paper>
  </Box>
}
