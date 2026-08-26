/* eslint-disable react-refresh/only-export-components */
import { Alert, Badge, Box, Button, CopyButton, Group, NumberInput, Paper, ScrollArea, Select, SimpleGrid, Stack, Table, Text, TextInput, Textarea } from '@mantine/core'
import { IconCheck, IconCopy, IconExternalLink, IconInfoCircle, IconPlus, IconTrash } from '@tabler/icons-react'
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

const emptyResultField = (index = 0) => ({
  id: `result_${index + 1}`,
  type: 'number',
  label_de: '',
  label_en: '',
  unit: '',
  solution: 0,
  tolerance: 0,
  feedback_de: '',
  feedback_en: '',
})

const taskDefaults = (id) => ({
  case_format: id === 'invoice_extraction' ? 'prose' : 'table',
  case_data_de: [''],
  case_data_en: [''],
  result_fields: [emptyResultField()],
})

function prepareTaskForm(form, id) {
  const defaults = taskDefaults(id)
  const caseDataDe = Array.isArray(form.case_data_de) && form.case_data_de.length ? form.case_data_de : defaults.case_data_de
  const caseDataEn = Array.isArray(form.case_data_en) && form.case_data_en.length ? form.case_data_en : defaults.case_data_en
  const rowCount = Math.max(caseDataDe.length, caseDataEn.length)
  const resultFields = Array.isArray(form.result_fields) && form.result_fields.length
    ? form.result_fields.map((field, index) => ({
      ...emptyResultField(index),
      ...field,
      solution: field.type === 'text'
        ? (typeof field.solution === 'object' && field.solution ? field.solution : { de: '', en: '' })
        : (field.solution ?? 0),
    }))
    : defaults.result_fields
  return {
    ...form,
    case_format: form.case_format || defaults.case_format,
    case_data_de: Array.from({ length: rowCount }, (_, index) => caseDataDe[index] ?? ''),
    case_data_en: Array.from({ length: rowCount }, (_, index) => caseDataEn[index] ?? ''),
    result_fields: resultFields,
  }
}

function TaskEditor({ form, setForm, t }) {
  const setCaseValue = (index, language, value) => setForm((current) => ({
    ...current,
    [`case_data_${language}`]: current[`case_data_${language}`].map((row, rowIndex) => rowIndex === index ? value : row),
  }))
  const addCaseRow = () => setForm((current) => ({
    ...current,
    case_data_de: [...current.case_data_de, ''],
    case_data_en: [...current.case_data_en, ''],
  }))
  const removeCaseRow = (index) => setForm((current) => ({
    ...current,
    case_data_de: current.case_data_de.filter((_, rowIndex) => rowIndex !== index),
    case_data_en: current.case_data_en.filter((_, rowIndex) => rowIndex !== index),
  }))
  const setResultField = (index, field, value) => setForm((current) => ({
    ...current,
    result_fields: current.result_fields.map((resultField, fieldIndex) => {
      if (fieldIndex !== index) return resultField
      if (field === 'type') {
        return {
          ...resultField,
          type: value,
          solution: value === 'text' ? { de: '', en: '' } : 0,
          tolerance: 0,
          unit: value === 'text' ? '' : resultField.unit,
        }
      }
      return { ...resultField, [field]: value }
    }),
  }))
  const setTextSolution = (index, language, value) => setForm((current) => ({
    ...current,
    result_fields: current.result_fields.map((field, fieldIndex) => fieldIndex === index
      ? { ...field, solution: { ...(typeof field.solution === 'object' ? field.solution : {}), [language]: value } }
      : field),
  }))
  const addResultField = () => setForm((current) => ({
    ...current,
    result_fields: [...current.result_fields, emptyResultField(current.result_fields.length)],
  }))
  const removeResultField = (index) => setForm((current) => ({
    ...current,
    result_fields: current.result_fields.filter((_, fieldIndex) => fieldIndex !== index),
  }))

  return <Stack gap="lg">
    <Paper withBorder radius="md" p="md">
      <Group justify="space-between" align="flex-end" mb="sm">
        <Select
          label={t('missions.creator.task.caseFormat')}
          value={form.case_format}
          data={[
            { value: 'table', label: t('missions.creator.task.table') },
            { value: 'prose', label: t('missions.creator.task.prose') },
          ]}
          onChange={(value) => setForm((current) => ({ ...current, case_format: value || 'table' }))}
        />
        <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addCaseRow}>
          {t('missions.creator.task.addCaseRow')}
        </Button>
      </Group>
      <Text fw={700} mb={4}>{t('missions.creator.task.caseData')}</Text>
      <Text fz="sm" c="dimmed" mb="sm">{t('missions.creator.task.caseDataHint')}</Text>
      <ScrollArea.Autosize mah={460} type="auto">
        <Stack gap="xs" pr="xs">
          {form.case_data_de.map((row, index) => <Paper key={index} withBorder radius="sm" p="sm">
            <Group align="flex-end" wrap="nowrap">
              <TextInput style={{ flex: 1 }} label={`DE ${index + 1}`} value={row} onChange={(event) => setCaseValue(index, 'de', event.target.value)} />
              <TextInput style={{ flex: 1 }} label={`EN ${index + 1}`} value={form.case_data_en[index] || ''} onChange={(event) => setCaseValue(index, 'en', event.target.value)} />
              <Button color="red" variant="subtle" size="compact-sm" disabled={form.case_data_de.length <= 1} aria-label={t('missions.creator.task.removeCaseRow')} onClick={() => removeCaseRow(index)}>
                <IconTrash size={16} />
              </Button>
            </Group>
          </Paper>)}
        </Stack>
      </ScrollArea.Autosize>
    </Paper>

    <Stack gap="sm">
      <Group justify="space-between">
        <Box>
          <Text fw={700}>{t('missions.creator.task.resultFields')}</Text>
          <Text fz="sm" c="dimmed">{t('missions.creator.task.resultFieldsHint')}</Text>
        </Box>
        <Button size="xs" variant="light" leftSection={<IconPlus size={14} />} disabled={form.result_fields.length >= 12} onClick={addResultField}>
          {t('missions.creator.task.addResultField')}
        </Button>
      </Group>
      {form.result_fields.map((field, index) => <Paper key={index} withBorder radius="md" p="md">
        <Group justify="space-between" mb="sm">
          <Text fw={700}>{t('missions.creator.task.resultField', { number: index + 1 })}</Text>
          <Button color="red" variant="subtle" size="compact-sm" disabled={form.result_fields.length <= 1} onClick={() => removeResultField(index)}>
            <IconTrash size={16} />
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="sm">
          <TextInput label={t('missions.creator.task.fieldId')} value={field.id} onChange={(event) => setResultField(index, 'id', event.target.value)} />
          <Select label={t('missions.creator.task.fieldType')} value={field.type} data={[
            { value: 'number', label: t('missions.creator.task.number') },
            { value: 'text', label: t('missions.creator.task.text') },
          ]} onChange={(value) => setResultField(index, 'type', value || 'number')} />
          <TextInput label={t('missions.creator.task.labelDe')} value={field.label_de} onChange={(event) => setResultField(index, 'label_de', event.target.value)} />
          <TextInput label={t('missions.creator.task.labelEn')} value={field.label_en} onChange={(event) => setResultField(index, 'label_en', event.target.value)} />
        </SimpleGrid>
        {field.type === 'text' ? <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" mt="sm">
          <TextInput label={t('missions.creator.task.solutionDe')} value={field.solution?.de || ''} onChange={(event) => setTextSolution(index, 'de', event.target.value)} />
          <TextInput label={t('missions.creator.task.solutionEn')} value={field.solution?.en || ''} onChange={(event) => setTextSolution(index, 'en', event.target.value)} />
        </SimpleGrid> : <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm" mt="sm">
          <NumberInput label={t('missions.creator.task.solution')} value={field.solution} onChange={(value) => setResultField(index, 'solution', value)} />
          <NumberInput min={0} label={t('missions.creator.task.tolerance')} value={field.tolerance} onChange={(value) => setResultField(index, 'tolerance', value)} />
          <TextInput label={t('missions.creator.task.unit')} value={field.unit} onChange={(event) => setResultField(index, 'unit', event.target.value)} />
        </SimpleGrid>}
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm" mt="sm">
          <Textarea label={t('missions.creator.task.feedbackDe')} value={field.feedback_de} onChange={(event) => setResultField(index, 'feedback_de', event.target.value)} />
          <Textarea label={t('missions.creator.task.feedbackEn')} value={field.feedback_en} onChange={(event) => setResultField(index, 'feedback_en', event.target.value)} />
        </SimpleGrid>
      </Paper>)}
    </Stack>
  </Stack>
}

export function createTaskChallengeType(id, labelKey) {
  return {
    id,
    labelKey,
    aiOnly: true,
    hasSharedFeedback: false,
    createDefaults: () => taskDefaults(id),
    prepareForm: (form) => prepareTaskForm(form, id),
    initialAnswer: (mission) => ({
      values: Object.fromEntries((mission?.content?.result_fields || []).map((field) => [field.id, ''])),
      prompt: '',
    }),
    isAnswerComplete: (answer) => {
      const values = Object.values(answer?.values || {})
      return values.length > 0 && values.every((value) => value !== '' && value !== null && value !== undefined)
    },
    Runner,
    Editor: TaskEditor,
    ResultDetails,
    Solution,
    submitTraining: async (mission, answer, language) => submitTrainingTaskChallenge(mission.session_id, answer.values, language),
  }
}
