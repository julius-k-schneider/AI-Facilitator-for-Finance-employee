/* eslint-disable react-refresh/only-export-components */
import { Alert, Badge, Button, CopyButton, Group, NumberInput, Paper, ScrollArea, Stack, Table, Text, TextInput, Textarea } from '@mantine/core'
import { IconCheck, IconCopy, IconExternalLink, IconInfoCircle } from '@tabler/icons-react'
import { submitTrainingTaskChallenge } from '../../../services/trainingService'

function splitRow(row) {
  return String(row ?? '').split('|').map((cell) => cell.trim())
}

// Tab-separated so table cases paste straight into Excel columns; prose cases join as paragraphs.
function clipboardText(caseData, caseFormat) {
  if (caseFormat === 'prose') return caseData.join('\n\n')
  return caseData.map((row) => splitRow(row).join('\t')).join('\n')
}

function CaseSection({ caseData, caseFormat, t }) {
  const rows = caseFormat === 'prose' ? null : caseData.map(splitRow)
  return <Paper withBorder radius="md" p="md">
    <Group justify="space-between" mb="sm">
      <Group gap="xs"><Text fw={700}>{t('training.task.caseData')}</Text><Badge variant="light">{t('training.task.rowCount', { count: caseData.length })}</Badge></Group>
      <CopyButton value={clipboardText(caseData, caseFormat)}>
        {({ copied, copy }) => <Button size="xs" variant="light" color={copied ? 'green' : 'brand'} leftSection={copied ? <IconCheck size={14} /> : <IconCopy size={14} />} onClick={copy}>{copied ? t('training.task.copied') : t('training.task.copy')}</Button>}
      </CopyButton>
    </Group>
    <ScrollArea.Autosize mah={rows ? 320 : 360} type="auto">
      {rows
        ? <Table striped highlightOnHover withRowBorders={false} fz="sm">
            <Table.Tbody>
              {rows.map((cells, index) => <Table.Tr key={index}>{cells.map((cell, cellIndex) => <Table.Td key={cellIndex} style={{ whiteSpace: 'nowrap' }}>{cell}</Table.Td>)}</Table.Tr>)}
            </Table.Tbody>
          </Table>
        : <Stack gap="sm">
            {caseData.map((paragraph, index) => <Paper key={index} withBorder radius="sm" p="sm" bg="gray.0"><Text fz="sm">{paragraph}</Text></Paper>)}
          </Stack>}
    </ScrollArea.Autosize>
  </Paper>
}

function Runner({ mission, answer, setAnswer, result, t }) {
  const fields = mission.content.result_fields || []
  const caseFormat = mission.content.case_format || 'table'
  const setValue = (id, value) => setAnswer((current) => ({ ...current, values: { ...current.values, [id]: value } }))
  const fieldResult = (id) => (result?.field_results || []).find((item) => item.id === id)
  return <Stack gap="lg">
    <Alert color="brand" variant="light" icon={<IconExternalLink size={18} />}>{t('training.task.hint')}</Alert>
    <CaseSection caseData={mission.content.case_data || []} caseFormat={caseFormat} t={t} />
    <Stack gap="md">
      <Text fw={700}>{t('training.task.yourResult')}</Text>
      {fields.map((field) => {
        const outcome = fieldResult(field.id)
        return <Paper key={field.id} withBorder radius="md" p="md" bg={outcome ? (outcome.correct ? 'green.0' : 'red.0') : undefined}>
          {field.type === 'text'
            ? <TextInput
                label={field.label}
                value={answer.values[field.id] ?? ''}
                disabled={Boolean(result)}
                onChange={(event) => setValue(field.id, event.target.value)}
              />
            : <NumberInput
                label={field.label}
                suffix={field.unit ? ` ${field.unit}` : undefined}
                decimalSeparator=","
                thousandSeparator="."
                allowedDecimalSeparators={[',']}
                decimalScale={2}
                value={answer.values[field.id] ?? ''}
                disabled={Boolean(result)}
                onChange={(value) => setValue(field.id, value)}
              />}
        </Paper>
      })}
    </Stack>
    <Textarea
      label={t('training.task.promptLabel')}
      description={t('training.task.promptHint')}
      autosize minRows={2} maxRows={6}
      value={answer.prompt}
      disabled={Boolean(result)}
      onChange={(event) => setAnswer((current) => ({ ...current, prompt: event.target.value }))}
    />
  </Stack>
}

function ResultDetails({ mission, result, t }) {
  const fields = mission.content.result_fields || []
  const labelFor = (id) => fields.find((field) => field.id === id)?.label || id
  return <Stack gap="xs">
    {(result.field_results || []).map((item) => <Paper key={item.id} withBorder radius="md" p="sm">
      <Group justify="space-between">
        <Text fw={700} c={item.correct ? 'green.8' : 'red.7'}>{labelFor(item.id)}</Text>
        <Badge color={item.correct ? 'green' : 'red'} variant="light">{item.correct ? t('missions.result.correctPrefix') : t('missions.result.wrongPrefix')}</Badge>
      </Group>
      <Text fz="sm" mt={4}>{item.feedback}</Text>
    </Paper>)}
  </Stack>
}

// A text field's solution is stored bilingually ({de, en}); a number field's solution is language-agnostic.
function solutionText(field, language) {
  const solution = field.solution
  if (solution === undefined || solution === null) return ''
  if (typeof solution === 'object') return solution[language] ?? ''
  return `${solution}${field.unit ? ` ${field.unit}` : ''}`
}

function Solution({ mission, language, showSolution = true, t }) {
  const caseData = mission[`case_data_${language}`] || []
  const fields = mission.result_fields || []
  return <Stack gap="sm">
    {mission[`question_${language}`] && <Text fz="sm">{mission[`question_${language}`]}</Text>}
    <Group gap="xs"><IconInfoCircle size={16} /><Text fz="sm" c="dimmed">{t('training.task.rowCount', { count: caseData.length })}</Text></Group>
    <Stack gap={4}>
      {fields.map((field) => <Text key={field.id} fz="sm" fw={showSolution ? 700 : 400}>
        {field[`label_${language}`]}{showSolution ? `: ${solutionText(field, language)}` : ''}
      </Text>)}
    </Stack>
  </Stack>
}

export function createTaskChallengeType(id, labelKey) {
  return {
    id,
    labelKey,
    aiOnly: true,
    initialAnswer: (mission) => ({
      values: Object.fromEntries((mission?.content?.result_fields || []).map((field) => [field.id, ''])),
      prompt: '',
    }),
    isAnswerComplete: (answer) => {
      const values = Object.values(answer?.values || {})
      return values.length > 0 && values.every((value) => value !== '' && value !== null && value !== undefined)
    },
    Runner,
    ResultDetails,
    Solution,
    submitTraining: async (mission, answer, language) => submitTrainingTaskChallenge(mission.session_id, answer.values, language),
  }
}
