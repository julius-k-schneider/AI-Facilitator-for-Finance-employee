import { useMemo, useState } from 'react'
import { Alert, Badge, Box, Button, Group, Paper, SimpleGrid, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { IconBrain, IconPlayerPlay, IconSparkles } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import MissionRunner from './missions/MissionRunner'
import { missionTypes } from './missions/missionTypes'
import { generateTrainingMission } from '../services/trainingService'

function localizeMission(raw, language) {
  const text = (value) => value?.[language] || value?.de || value?.en || ''
  const content = {
    question: raw[`question_${language}`],
    options: (raw.options || []).map(text),
    statements: (raw.statements || []).map((statement) => text(statement.text)),
  }
  const feedback = raw[`feedback_${language}`]
  const statementFeedback = raw.test_solution?.[`feedback_${language}`] || []
  return {
    id: `training-${raw.type}`,
    type: raw.type,
    title: raw[`title_${language}`],
    description: raw[`description_${language}`],
    max_points: 0,
    content,
    test_solution: {
      correct_indices: raw.test_solution?.correct_indices || [],
      correct_order: raw.test_solution?.correct_order || [],
      correct_colors: raw.test_solution?.correct_colors || [],
      feedback: statementFeedback.length ? statementFeedback : feedback,
    },
  }
}

export default function Training() {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  const [rawMission, setRawMission] = useState(null)
  const [generatingType, setGeneratingType] = useState('')
  const [error, setError] = useState('')
  const mission = useMemo(() => rawMission ? localizeMission(rawMission, language) : null, [rawMission, language])

  const generate = async (type) => {
    setGeneratingType(type)
    setError('')
    try {
      setRawMission(await generateTrainingMission(type))
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setGeneratingType('')
    }
  }

  if (mission) return <MissionRunner mission={mission} language={language} testMode showPoints={false} backLabel={t('training.back')} onBack={() => setRawMission(null)} />

  return <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
    <Badge variant="light" color="brand" mb="sm">{t('training.badge')}</Badge>
    <Title order={1} fz={{ base: 28, md: 34 }}>{t('training.title')}</Title>
    <Text c="dimmed" fz="lg" mt={4} mb="xl">{t('training.description')}</Text>
    {error && <Alert color="red" mb="lg">{error}</Alert>}
    <SimpleGrid cols={{ base: 1, sm: 2, xl: 3 }} spacing="lg">
      {missionTypes.map((definition) => <Paper key={definition.id} withBorder radius="lg" p="xl" bg="white">
        <Stack gap="lg" h="100%">
          <Group justify="space-between"><ThemeIcon size={48} radius="md" variant="light" color="brand"><IconBrain size={25} /></ThemeIcon><Badge variant="light" color="secondary">{t(`missions.types.${definition.labelKey}`)}</Badge></Group>
          <Box style={{ flex: 1 }}><Text fw={700} fz="lg">{t(`training.types.${definition.labelKey}.title`)}</Text><Text c="dimmed" fz="sm" mt={5}>{t(`training.types.${definition.labelKey}.description`)}</Text></Box>
          <Button color="brand" leftSection={generatingType === definition.id ? <IconSparkles size={17} /> : <IconPlayerPlay size={17} />} loading={generatingType === definition.id} disabled={Boolean(generatingType) && generatingType !== definition.id} onClick={() => generate(definition.id)}>{t('training.generate')}</Button>
        </Stack>
      </Paper>)}
    </SimpleGrid>
  </Box>
}
