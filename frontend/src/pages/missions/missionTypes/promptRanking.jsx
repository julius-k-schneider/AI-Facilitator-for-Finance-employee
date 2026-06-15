/* eslint-disable react-refresh/only-export-components */
import { Badge, Button, Group, Paper, Stack, Text, TextInput } from '@mantine/core'
import { IconArrowDown, IconArrowUp, IconPlus } from '@tabler/icons-react'

export function moveItem(items, index, direction) {
  const target = index + direction
  if (target < 0 || target >= items.length) return items
  const next = [...items]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

function Runner({ mission, answer, setAnswer, result, t }) {
  return <Stack gap="sm">
    <Text fz="sm" c="dimmed">{t('missions.rankingInstruction')}</Text>
    {answer.map((optionIndex, position) => <Paper key={optionIndex} withBorder radius="md" p="md"><Group justify="space-between" wrap="nowrap">
      <Group wrap="nowrap"><Badge variant="light">{position + 1}</Badge><Text>{mission.content.options[optionIndex]}</Text></Group>
      <Group gap={4} wrap="nowrap"><Button variant="subtle" size="compact-sm" disabled={Boolean(result) || position === 0} aria-label={t('missions.moveUp')} onClick={() => setAnswer((current) => moveItem(current, position, -1))}><IconArrowUp size={17} /></Button><Button variant="subtle" size="compact-sm" disabled={Boolean(result) || position === answer.length - 1} aria-label={t('missions.moveDown')} onClick={() => setAnswer((current) => moveItem(current, position, 1))}><IconArrowDown size={17} /></Button></Group>
    </Group></Paper>)}
  </Stack>
}

function Editor({ form, setForm, setOption, t }) {
  const addOption = () => setForm((current) => ({ ...current, options: [...current.options, { de: '', en: '' }], correct_order: [...current.correct_order, current.options.length] }))
  return <Stack gap="sm">
    <Group justify="space-between"><Text fw={700}>{t('missions.creator.answers')}</Text><Button size="xs" variant="light" leftSection={<IconPlus size={14} />} disabled={form.options.length >= 4} onClick={addOption}>{t('missions.creator.addAnswer')}</Button></Group>
    {form.options.map((option, index) => <Paper key={index} withBorder radius="md" p="sm"><Group align="flex-end" wrap="nowrap"><Badge variant="light">{form.correct_order.indexOf(index) + 1}</Badge><TextInput label={`DE ${index + 1}`} value={option.de} onChange={(event) => setOption(index, 'de', event.target.value)} style={{ flex: 1 }} /><TextInput label={`EN ${index + 1}`} value={option.en} onChange={(event) => setOption(index, 'en', event.target.value)} style={{ flex: 1 }} /></Group></Paper>)}
    <Stack gap="xs"><Text fw={700}>{t('missions.creator.rankingSolution')}</Text>{form.correct_order.map((optionIndex, position) => <Paper key={optionIndex} withBorder radius="md" p="xs"><Group justify="space-between" wrap="nowrap"><Text fz="sm">{position + 1}. {form.options[optionIndex]?.de || form.options[optionIndex]?.en || `${t('missions.creator.answers')} ${optionIndex + 1}`}</Text><Group gap={4}><Button variant="subtle" size="compact-sm" disabled={position === 0} onClick={() => setForm((current) => ({ ...current, correct_order: moveItem(current.correct_order, position, -1) }))}><IconArrowUp size={16} /></Button><Button variant="subtle" size="compact-sm" disabled={position === form.correct_order.length - 1} onClick={() => setForm((current) => ({ ...current, correct_order: moveItem(current.correct_order, position, 1) }))}><IconArrowDown size={16} /></Button></Group></Group></Paper>)}</Stack>
  </Stack>
}

function Solution({ mission, language, showSolution = true }) {
  const order = showSolution ? mission.correct_order : mission.options.map((_, index) => index)
  return <Stack gap={4}>{order.map((optionIndex, position) => <Text key={optionIndex} fz="sm" c={showSolution ? 'green.8' : undefined} fw={showSolution ? 700 : 400}>{position + 1}. {mission.options[optionIndex]?.[language]}</Text>)}</Stack>
}

function ResultDetails({ mission, result, t }) {
  return <Paper withBorder radius="md" p="md"><Text fw={700} mb="xs">{t('missions.creator.rankingSolution')}</Text>{result.correct_order.map((optionIndex, index) => <Text key={optionIndex} fz="sm">{index + 1}. {mission.content.options[optionIndex]}</Text>)}{result.feedback && <Text fz="sm" c="dimmed" mt="sm">{result.feedback}</Text>}</Paper>
}

export default {
  id: 'prompt_ranking', labelKey: 'promptRanking', hasSharedFeedback: true,
  createDefaults: () => ({ options: [{ de: '', en: '' }, { de: '', en: '' }, { de: '', en: '' }], correct_order: [0, 1, 2], correct_indices: [0] }),
  prepareForm: (form) => ({ ...form, options: form.options.length < 3 ? [...form.options, ...Array.from({ length: 3 - form.options.length }, () => ({ de: '', en: '' }))] : form.options, correct_order: Array.from({ length: Math.max(3, form.options.length) }, (_, index) => index) }),
  initialAnswer: (mission) => mission.content.options.map((_, index) => index), isAnswerComplete: () => true,
  Runner, Editor, Solution, ResultDetails,
  evaluateTest: (mission, answer) => { const correct = answer.every((value, index) => value === mission.test_solution.correct_order[index]); return { correct, score: correct ? mission.max_points : 0, max_points: mission.max_points, correct_order: mission.test_solution.correct_order, feedback: mission.test_solution.feedback } },
  example: (text) => ({ id: 'test-ranking', type: 'prompt_ranking', title: text('Prompts sortieren', 'Rank prompts'), description: text('Ordne drei Prompts nach ihrer Qualität.', 'Order three prompts by quality.'), max_points: 30, completed: false, score: null, content: { question: text('Sortiere vom schlechtesten zum besten Prompt.', 'Sort from the worst to the best prompt.'), options: [text('Was ist hier los?', 'What is going on?'), text('Analysiere die Abweichungen.', 'Analyze the variances.'), text('Vergleiche Plan und Ist, nenne die fünf größten Abweichungen und mögliche Ursachen als Tabelle.', 'Compare plan and actuals, listing the five largest variances and possible causes in a table.')] }, test_solution: { correct_order: [0, 1, 2], feedback: text('Ziel, Kontext und Ausgabeformat machen einen Prompt konkret.', 'Goal, context, and output format make a prompt specific.') } }),
}
