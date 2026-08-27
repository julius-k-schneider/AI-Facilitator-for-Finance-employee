/* eslint-disable react-refresh/only-export-components */
import { Badge, Button, Checkbox, Group, Paper, Radio, Stack, Text, TextInput } from '@mantine/core'
import { IconPlus } from '@tabler/icons-react'

export const emptyOptions = () => [{ de: '', en: '' }, { de: '', en: '' }]

export function ChoiceRunner({ mission, answer, setAnswer, result, multiple = false }) {
  const correctIndices = result?.correct_indices || mission.test_solution?.correct_indices || []
  const completedControlStyles = result ? {
    root: { opacity: 1 },
    body: { opacity: 1 },
    label: { color: 'var(--mantine-color-text)', opacity: 1 },
  } : undefined
  const optionState = (index) => {
    if (!result) return {}
    const selected = multiple ? answer.includes(index) : answer === index
    if (correctIndices.includes(index)) {
      return { bg: 'green.0', style: { borderColor: 'var(--mantine-color-green-6)', borderWidth: 2 } }
    }
    if (selected) {
      return { bg: 'red.0', style: { borderColor: 'var(--mantine-color-red-6)', borderWidth: 2 } }
    }
    return {}
  }
  if (multiple) {
    return <Checkbox.Group value={answer.map(String)} onChange={(values) => setAnswer(values.map(Number))}>
      <Stack gap="sm">{mission.content.options.map((option, index) => <Paper key={`${index}-${option}`} withBorder radius="md" p="md" {...optionState(index)}><Checkbox value={String(index)} label={option} disabled={Boolean(result)} styles={completedControlStyles} /></Paper>)}</Stack>
    </Checkbox.Group>
  }
  return <Radio.Group value={answer === null ? '' : String(answer)} onChange={(value) => setAnswer(Number(value))}>
    <Stack gap="sm">{mission.content.options.map((option, index) => <Paper key={`${index}-${option}`} withBorder radius="md" p="md" {...optionState(index)}><Radio value={String(index)} label={option} disabled={Boolean(result)} styles={completedControlStyles} /></Paper>)}</Stack>
  </Radio.Group>
}

export function ChoiceEditor({ form, setForm, setOption, toggleCorrectOption, t, multiple = false }) {
  const addOption = () => setForm((current) => ({ ...current, options: [...current.options, { de: '', en: '' }] }))
  return <Stack gap="sm">
    <Group justify="space-between"><Text fw={700}>{t('missions.creator.answers')}</Text><Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={addOption}>{t('missions.creator.addAnswer')}</Button></Group>
    {form.options.map((option, index) => <Paper key={index} withBorder radius="md" p="sm"><Group align="flex-end" wrap="nowrap">
      {multiple ? <Checkbox checked={form.correct_indices.includes(index)} onChange={() => toggleCorrectOption(index)} aria-label={t('missions.creator.correctAnswer')} /> : <Radio checked={form.correct_indices.includes(index)} onChange={() => setForm((current) => ({ ...current, correct_indices: [index] }))} aria-label={t('missions.creator.correctAnswer')} />}
      <TextInput label={`DE ${index + 1}`} value={option.de} onChange={(event) => setOption(index, 'de', event.target.value)} style={{ flex: 1 }} />
      <TextInput label={`EN ${index + 1}`} value={option.en} onChange={(event) => setOption(index, 'en', event.target.value)} style={{ flex: 1 }} />
    </Group></Paper>)}
  </Stack>
}

export function ChoiceSolution({ mission, language, showSolution = true }) {
  return <Stack gap={4}>{mission.options.map((option, index) => <Text key={index} fz="sm" c={showSolution && mission.correct_indices.includes(index) ? 'green.8' : undefined} fw={showSolution && mission.correct_indices.includes(index) ? 700 : 400}>{index + 1}. {option[language]}</Text>)}</Stack>
}

export function evaluateChoiceTest(mission, answer, multiple = false) {
  const selected = multiple ? [...answer].sort() : [answer]
  const expected = [...mission.test_solution.correct_indices].sort()
  const correct = selected.length === expected.length && selected.every((value, index) => value === expected[index])
  const feedback = mission.test_solution.feedback || `${mission.content.options.filter((_, index) => expected.includes(index)).join(', ')}`
  return { correct, score: correct ? mission.max_points : 0, max_points: mission.max_points, correct_indices: expected, feedback }
}

export function choiceDefinition({ id, labelKey, multiple = false }) {
  return {
    id,
    labelKey,
    hasSharedFeedback: true,
    createDefaults: () => ({ options: emptyOptions(), correct_indices: [0] }),
    initialAnswer: () => multiple ? [] : null,
    isAnswerComplete: (answer) => multiple ? answer.length > 0 : answer !== null,
    Runner: (props) => <ChoiceRunner {...props} multiple={multiple} />,
    Editor: (props) => <ChoiceEditor {...props} multiple={multiple} />,
    Solution: ChoiceSolution,
    evaluateTest: (mission, answer) => evaluateChoiceTest(mission, answer, multiple),
  }
}

export function typeBadge(position) {
  return <Badge variant="light">{position + 1}</Badge>
}
