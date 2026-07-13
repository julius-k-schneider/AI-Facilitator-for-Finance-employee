import { useState } from 'react'
import { Alert, Badge, Box, Button, Paper, Stack, Text, Title } from '@mantine/core'
import { IconArrowLeft, IconBooks, IconBulb, IconTrophy } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { submitMission } from '../../services/missionService'
import { getMissionType } from './missionTypes'

function initialAnswerForMission(definition, mission, readOnly) {
  if (!readOnly || !mission.attempt?.answer) return definition.initialAnswer(mission)
  const stored = mission.attempt.answer
  if (Array.isArray(stored.selected_colors)) return stored.selected_colors
  if (Array.isArray(stored.selected_order)) return stored.selected_order
  if (Array.isArray(stored.selected_indices)) {
    return mission.content?.multiple ? stored.selected_indices : stored.selected_indices[0] ?? null
  }
  return definition.initialAnswer(mission)
}

export default function MissionRunner({
  mission,
  onBack,
  onCompleted = () => {},
  language,
  testMode = false,
  readOnly = false,
  showSubmit = true,
  showPoints = true,
  backLabel,
}) {
  const { t } = useTranslation()
  const definition = getMissionType(mission.type)
  const [answer, setAnswer] = useState(() => initialAnswerForMission(definition, mission, readOnly))
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const microLearning = testMode
    ? mission.test_solution?.micro_learning
    : mission.content?.micro_learning || result?.microLearning
  const feedback = testMode
    ? mission.test_solution?.feedback ?? result?.feedback
    : mission.content?.feedback ?? result?.feedback
  const isPartial = result?.correct_count !== undefined && !result.correct
  const resultTitle = result?.correct
    ? t('missions.result.correctTitle')
    : isPartial ? t('missions.result.partialTitle') : t('missions.result.wrongTitle')
  const resultSummary = showPoints
    ? result?.correct
      ? t('missions.result.pointsEarned', { points: result.score })
      : isPartial
        ? t('missions.result.partialSummary', { points: result.score, correct: result.correct_count, total: result.total_count })
        : ''
    : result?.correct
      ? ''
      : isPartial
        ? t('training.result.partial', { correct: result.correct_count, total: result.total_count })
        : ''

  const submit = async () => {
    if (readOnly || !showSubmit) return
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
        <definition.Runner mission={mission} answer={answer} setAnswer={readOnly ? () => {} : setAnswer} result={readOnly ? {} : result} t={t} />
        {readOnly && mission.completed && showPoints && <Alert color="green" icon={<IconTrophy size={20} />} title={t('missions.archive.completedTitle')}>
          <Text fz="sm">{t('missions.archive.score', { score: mission.score, max: mission.max_points })}</Text>
        </Alert>}
        {error && <Alert color="red">{error}</Alert>}
        {!readOnly && result && <Alert color={result.correct ? 'green' : 'orange'} icon={result.correct ? <IconTrophy size={20} /> : undefined} title={resultTitle}>
          {resultSummary && <Text fz="sm">{resultSummary}</Text>}
          {typeof feedback === 'string' && feedback && !definition.ResultDetails && <>
            <Text fz="sm" fw={700} mt={resultSummary ? 'sm' : 0}>{t('missions.result.explanationLabel')}</Text>
            <Text fz="sm">{feedback}</Text>
          </>}
        </Alert>}
        {!readOnly && result && definition.ResultDetails && <definition.ResultDetails mission={mission} result={{ ...result, feedback }} t={t} />}
        {readOnly && typeof feedback === 'string' && feedback && <Alert color="blue" icon={<IconBulb size={20} />} title={t('missions.result.explanationLabel')}>
          <Text fz="sm">{feedback}</Text>
        </Alert>}
        {((!readOnly && result) || readOnly) && microLearning && <Alert color="blue" icon={<IconBooks size={20} />} title={t('missions.microLearning.title')}>
          <Text fz="sm">{microLearning}</Text>
        </Alert>}
        {!readOnly && showSubmit && !result && <Button color="brand" disabled={!definition.isAnswerComplete(answer)} loading={submitting} onClick={submit}>{t('missions.submit')}</Button>}
      </Stack>
    </Paper>
  </Box>
}
