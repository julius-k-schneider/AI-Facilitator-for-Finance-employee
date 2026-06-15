import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Box, Button, Checkbox, Group, Modal, NumberInput, Paper, Radio, Select,
  SimpleGrid, Stack, Switch, Text, Textarea, TextInput, ThemeIcon, Title,
} from '@mantine/core'
import {
  IconArrowLeft, IconArrowRight, IconCalendar, IconCheck, IconChevronLeft,
  IconChevronRight, IconCircleCheck, IconEdit, IconEye, IconPlus, IconRefresh, IconSparkles,
  IconArrowDown, IconArrowUp, IconFlame, IconTargetArrow, IconTrash, IconTrophy, IconX,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useUserProgress } from '../hooks/useUserProgress'
import {
  approveAllReviewMissions, approveMission, createMission, deleteMission, generateNextWeekMissions, getDailyMissions,
  getMissionSchedule, getReviewMissions, regenerateMission, rejectMission, submitMission, updateMission,
  rejectAllReviewMissions,
} from '../services/missionService'
import './Missions.css'

const createEmptyForm = () => ({
  type: 'single_choice', scheduled_date: '', title_de: '', title_en: '',
  description_de: '', description_en: '', question_de: '', question_en: '',
  feedback_de: '', feedback_en: '',
  max_points: 100, correct_indices: [0],
  correct_order: [0, 1, 2],
  options: [{ de: '', en: '' }, { de: '', en: '' }],
  statements: Array.from({ length: 3 }, () => ({
    de: '', en: '', correct_color: 'green', feedback_de: '', feedback_en: '',
  })),
})

function isoDate(date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-')
}

function monthRange(month) {
  return {
    from: isoDate(new Date(month.getFullYear(), month.getMonth(), 1)),
    to: isoDate(new Date(month.getFullYear(), month.getMonth() + 1, 0)),
  }
}

function missionTypeLabel(t, type) {
  const labels = {
    single_choice: 'singleChoice',
    multiple_choice: 'multipleChoice',
    compliance_decision: 'complianceDecision',
    prompt_selection: 'promptSelection',
    prompt_ranking: 'promptRanking',
    compliance_traffic_light: 'complianceTrafficLight',
  }
  return t(`missions.types.${labels[type] || 'singleChoice'}`)
}

function missionToForm(mission) {
  return {
    type: mission.type,
    scheduled_date: mission.scheduled_date,
    title_de: mission.title_de,
    title_en: mission.title_en,
    description_de: mission.description_de,
    description_en: mission.description_en,
    question_de: mission.question_de,
    question_en: mission.question_en,
    feedback_de: mission.feedback_de || '',
    feedback_en: mission.feedback_en || '',
    max_points: mission.max_points,
    correct_indices: mission.correct_indices?.length ? mission.correct_indices : [0],
    correct_order: mission.correct_order?.length ? mission.correct_order : mission.options.map((_, index) => index),
    options: mission.options.map((option) => ({ ...option })),
    statements: mission.statements?.length ? mission.statements.map((statement) => ({ ...statement })) : createEmptyForm().statements,
  }
}

function moveItem(items, index, direction) {
  const target = index + direction
  if (target < 0 || target >= items.length) return items
  const next = [...items]
  ;[next[index], next[target]] = [next[target], next[index]]
  return next
}

function MissionSolutionContent({ mission, language, showSolution = true }) {
  const { t } = useTranslation()
  if (mission.type === 'compliance_traffic_light') {
    return <Stack gap="xs">{mission.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm">
      <Text fz="sm" fw={600}>{index + 1}. {statement[language]}</Text>
      {showSolution && <><Badge mt="xs" color={statement.correct_color === 'yellow' ? 'orange' : statement.correct_color}>{t(`missions.trafficLight.${statement.correct_color}`)}</Badge><Text fz="sm" mt="xs">{statement[`feedback_${language}`]}</Text></>}
    </Paper>)}</Stack>
  }
  if (mission.type === 'prompt_ranking') {
    const order = showSolution ? mission.correct_order : mission.options.map((_, index) => index)
    return <Stack gap={4}>{order.map((optionIndex, position) => <Text key={optionIndex} fz="sm" c={showSolution ? 'green.8' : undefined} fw={showSolution ? 700 : 400}>{position + 1}. {mission.options[optionIndex]?.[language]}</Text>)}</Stack>
  }
  return <Stack gap={4}>{mission.options.map((option, index) => <Text key={index} fz="sm" c={showSolution && mission.correct_indices.includes(index) ? 'green.8' : undefined} fw={showSolution && mission.correct_indices.includes(index) ? 700 : 400}>{index + 1}. {option[language]}</Text>)}</Stack>
}

function MissionCard({ mission, onOpen }) {
  const { t } = useTranslation()
  return (
    <Paper withBorder radius="lg" p="xl" bg="white">
      <Stack gap="lg" h="100%">
        <Group justify="space-between" align="flex-start">
          <ThemeIcon size={48} radius="md" variant="light" color={mission.completed ? 'green' : 'brand'}>
            {mission.completed ? <IconCircleCheck size={25} /> : <IconTargetArrow size={25} />}
          </ThemeIcon>
          <Badge color={mission.completed ? 'green' : 'accent'} variant="light">
            {mission.completed ? t('missions.status.completed') : t('missions.status.open')}
          </Badge>
        </Group>
        <Box style={{ flex: 1 }}>
          <Text fw={700} fz="lg">{mission.title}</Text>
          <Text c="dimmed" fz="sm" mt={5}>{mission.description}</Text>
        </Box>
        <Group justify="space-between">
          <Badge variant="light" color="secondary">{missionTypeLabel(t, mission.type)}</Badge>
          <Text fz="sm" fw={700} c="brand.7">
            {mission.completed ? `${mission.score}/${mission.max_points}` : mission.max_points} {t('missions.points')}
          </Text>
        </Group>
        <Button color="brand" variant={mission.completed ? 'light' : 'filled'} disabled={mission.completed}
          rightSection={mission.completed ? <IconCheck size={17} /> : <IconArrowRight size={17} />}
          onClick={() => onOpen(mission)}>
          {mission.completed ? t('missions.completedButton') : t('missions.startButton')}
        </Button>
      </Stack>
    </Paper>
  )
}

function MissionRunner({ mission, onBack, onCompleted }) {
  const { t } = useTranslation()
  const isMultiple = mission.type === 'multiple_choice'
  const isRanking = mission.type === 'prompt_ranking'
  const isTrafficLight = mission.type === 'compliance_traffic_light'
  const initialAnswer = isMultiple ? [] : isRanking
    ? mission.content.options.map((_, index) => index)
    : isTrafficLight ? mission.content.statements.map(() => '') : null
  const [answer, setAnswer] = useState(initialAnswer)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const data = await submitMission(mission.id, answer)
      setResult({ ...data.result, feedback: data.mission.content.feedback })
      onCompleted(data.mission)
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Button variant="subtle" color="secondary" leftSection={<IconArrowLeft size={17} />} onClick={onBack} mb="lg">{t('missions.back')}</Button>
      <Paper withBorder radius="lg" p={{ base: 'xl', md: 40 }} bg="white">
        <Stack gap="xl">
          <Box>
            <Badge variant="light" color="brand" mb="sm">{missionTypeLabel(t, mission.type)}</Badge>
            <Title order={1} fz={{ base: 25, md: 32 }}>{mission.title}</Title>
            <Text c="dimmed" mt={6}>{mission.description}</Text>
          </Box>
          <Text fw={700} fz="lg">{mission.content.question}</Text>
          {isRanking ? <Stack gap="sm">
              <Text fz="sm" c="dimmed">{t('missions.rankingInstruction')}</Text>
              {answer.map((optionIndex, position) => <Paper key={optionIndex} withBorder radius="md" p="md">
                <Group justify="space-between" wrap="nowrap">
                  <Group wrap="nowrap"><Badge variant="light">{position + 1}</Badge><Text>{mission.content.options[optionIndex]}</Text></Group>
                  <Group gap={4} wrap="nowrap">
                    <Button variant="subtle" size="compact-sm" disabled={Boolean(result) || position === 0} aria-label={t('missions.moveUp')} onClick={() => setAnswer((current) => moveItem(current, position, -1))}><IconArrowUp size={17} /></Button>
                    <Button variant="subtle" size="compact-sm" disabled={Boolean(result) || position === answer.length - 1} aria-label={t('missions.moveDown')} onClick={() => setAnswer((current) => moveItem(current, position, 1))}><IconArrowDown size={17} /></Button>
                  </Group>
                </Group>
              </Paper>)}
            </Stack> : isTrafficLight ? <Stack gap="md">
              {mission.content.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="md">
                <Stack gap="sm"><Text fw={600}>{index + 1}. {statement}</Text>
                  <Radio.Group value={answer[index]} onChange={(value) => setAnswer((current) => current.map((item, itemIndex) => itemIndex === index ? value : item))}>
                    <Group grow>{['green', 'yellow', 'red'].map((color) => <Paper key={color} withBorder radius="md" p="xs"><Radio value={color} color={color === 'yellow' ? 'orange' : color} label={t(`missions.trafficLight.${color}`)} disabled={Boolean(result)} /></Paper>)}</Group>
                  </Radio.Group>
                </Stack>
              </Paper>)}
            </Stack> : isMultiple ? <Checkbox.Group value={answer.map(String)} onChange={(values) => setAnswer(values.map(Number))}>
              <Stack gap="sm">
                {mission.content.options.map((option, index) => <Paper key={`${index}-${option}`} withBorder radius="md" p="md"><Checkbox value={String(index)} label={option} disabled={Boolean(result)} /></Paper>)}
              </Stack>
            </Checkbox.Group> : <Radio.Group value={answer === null ? '' : String(answer)} onChange={(value) => setAnswer(Number(value))}>
              <Stack gap="sm">
                {mission.content.options.map((option, index) => <Paper key={`${index}-${option}`} withBorder radius="md" p="md"><Radio value={String(index)} label={option} disabled={Boolean(result)} /></Paper>)}
              </Stack>
            </Radio.Group>}
          {error && <Alert color="red">{error}</Alert>}
          {result && <Alert color={result.correct ? 'green' : 'orange'} icon={result.correct ? <IconTrophy size={20} /> : undefined}>
            {result.correct ? t('missions.result.correct', { points: result.score }) : result.correct_count !== undefined
              ? t('missions.result.partial', { points: result.score, correct: result.correct_count, total: result.total_count })
              : t('missions.result.wrong')}
          </Alert>}
          {result && isTrafficLight && <Stack gap="xs">{mission.content.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm"><Group gap="xs"><Badge color={result.correct_colors[index] === 'yellow' ? 'orange' : result.correct_colors[index]}>{t(`missions.trafficLight.${result.correct_colors[index]}`)}</Badge><Text fz="sm" fw={600}>{statement}</Text></Group><Text fz="sm" c="dimmed" mt="xs">{result.feedback[index]}</Text></Paper>)}</Stack>}
          {result && isRanking && <Paper withBorder radius="md" p="md"><Text fw={700} mb="xs">{t('missions.creator.rankingSolution')}</Text>{result.correct_order.map((optionIndex, index) => <Text key={optionIndex} fz="sm">{index + 1}. {mission.content.options[optionIndex]}</Text>)}{result.feedback && <Text fz="sm" c="dimmed" mt="sm">{result.feedback}</Text>}</Paper>}
          {!result && <Button color="brand" disabled={isMultiple ? answer.length === 0 : isTrafficLight ? answer.some((value) => !value) : answer === null} loading={submitting} onClick={submit}>{t('missions.submit')}</Button>}
        </Stack>
      </Paper>
    </Box>
  )
}

function Calendar({ month, setMonth, schedule, selectedDate, onSelect }) {
  const { i18n, t } = useTranslation()
  const offset = (new Date(month.getFullYear(), month.getMonth(), 1).getDay() + 6) % 7
  const length = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const cells = [...Array(offset).fill(null), ...Array.from({ length }, (_, index) => index + 1)]
  const weekDays = t('missions.creator.weekDays', { returnObjects: true })

  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" mb="md">
        <Button variant="subtle" px="xs" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}><IconChevronLeft size={18} /></Button>
        <Text fw={700}>{month.toLocaleDateString(i18n.resolvedLanguage, { month: 'long', year: 'numeric' })}</Text>
        <Button variant="subtle" px="xs" onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}><IconChevronRight size={18} /></Button>
      </Group>
      <div className="mission-calendar-grid">
        {weekDays.map((day) => <Text key={day} ta="center" fz="xs" fw={700} c="dimmed">{day}</Text>)}
        {cells.map((day, index) => {
          if (!day) return <div key={`empty-${index}`} />
          const value = isoDate(new Date(month.getFullYear(), month.getMonth(), day))
          const count = schedule[value] || 0
          return <button key={value} type="button" className={`mission-calendar-day${selectedDate === value ? ' is-selected' : ''}`} onClick={() => onSelect(value)}>
            <span>{day}</span>{count > 0 && <span className={`mission-calendar-count${count >= 2 ? ' is-full' : ''}`}>{count}/2</span>}
          </button>
        })}
      </div>
    </Paper>
  )
}

function Creator({ opened, onClose, onCreated }) {
  const { i18n, t } = useTranslation()
  const [form, setForm] = useState(createEmptyForm)
  const [month, setMonth] = useState(new Date())
  const [schedule, setSchedule] = useState({})
  const [scheduledMissions, setScheduledMissions] = useState({})
  const [preview, setPreview] = useState(null)
  const [showPreviewSolution, setShowPreviewSolution] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const loadSchedule = useCallback(() => {
    const range = monthRange(month)
    getMissionSchedule(range.from, range.to)
      .then((data) => { setSchedule(data.dates || {}); setScheduledMissions(data.missions || {}) })
      .catch(() => { setSchedule({}); setScheduledMissions({}) })
  }, [month])

  useEffect(() => { if (opened) loadSchedule() }, [opened, loadSchedule])
  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }))
  const setType = (value) => setForm((current) => ({
    ...current,
    type: value,
    correct_indices: value === 'multiple_choice' ? current.correct_indices : [current.correct_indices[0] ?? 0],
    options: value === 'prompt_ranking' && current.options.length < 3
      ? [...current.options, ...Array.from({ length: 3 - current.options.length }, () => ({ de: '', en: '' }))]
      : current.options,
    correct_order: value === 'prompt_ranking'
      ? Array.from({ length: Math.max(3, current.options.length) }, (_, index) => index)
      : current.correct_order,
  }))
  const setOption = (index, language, value) => setForm((current) => ({ ...current, options: current.options.map((option, optionIndex) => optionIndex === index ? { ...option, [language]: value } : option) }))
  const addOption = () => setForm((current) => ({
    ...current,
    options: [...current.options, { de: '', en: '' }],
    correct_order: current.type === 'prompt_ranking' ? [...current.correct_order, current.options.length] : current.correct_order,
  }))
  const setStatement = (index, field, value) => setForm((current) => ({
    ...current,
    statements: current.statements.map((statement, statementIndex) => statementIndex === index ? { ...statement, [field]: value } : statement),
  }))
  const toggleCorrectOption = (index) => setForm((current) => ({
    ...current,
    correct_indices: current.correct_indices.includes(index)
      ? current.correct_indices.filter((value) => value !== index)
      : [...current.correct_indices, index].sort((a, b) => a - b),
  }))
  const missionsForDate = form.scheduled_date ? scheduledMissions[form.scheduled_date] || [] : []

  const resetForm = () => {
    setForm(createEmptyForm())
    setEditingId(null)
  }

  const editMission = (mission) => {
    setForm(missionToForm(mission))
    setEditingId(mission.id)
    setPreview(null)
    setError('')
  }

  const removeMission = async (mission) => {
    if (!window.confirm(t('missions.creator.deleteConfirm', { title: mission.title_de || mission.title_en }))) return
    setDeletingId(mission.id)
    setError('')
    try {
      await deleteMission(mission.id)
      if (preview?.id === mission.id) setPreview(null)
      loadSchedule()
      onCreated()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setDeletingId(null)
    }
  }

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      if (editingId) await updateMission(editingId, form)
      else await createMission(form)
      resetForm()
      loadSchedule()
      onCreated()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={editingId ? t('missions.creator.editTitle') : t('missions.creator.title')}
      size="calc(80vw)"
      centered
      classNames={{ content: 'mission-manager-modal', body: 'mission-manager-body' }}
    >
      <div className="mission-manager-grid">
        <Stack gap="md">
          {editingId && <Group justify="space-between"><Badge variant="light" color="brand">{t('missions.creator.editing')}</Badge><Button variant="subtle" size="xs" onClick={resetForm}>{t('missions.creator.cancelEdit')}</Button></Group>}
          <Select label={t('missions.creator.type')} value={form.type} data={[
            { value: 'single_choice', label: t('missions.types.singleChoice') },
            { value: 'multiple_choice', label: t('missions.types.multipleChoice') },
            { value: 'prompt_selection', label: t('missions.types.promptSelection') },
            { value: 'prompt_ranking', label: t('missions.types.promptRanking') },
            { value: 'compliance_traffic_light', label: t('missions.types.complianceTrafficLight') },
          ]} onChange={setType} />
          <TextInput type="date" label={t('missions.creator.date')} value={form.scheduled_date} min={editingId ? undefined : isoDate(new Date())} onChange={(event) => setField('scheduled_date', event.target.value)} />
          <SimpleGrid cols={2}><TextInput label={t('missions.creator.titleDe')} value={form.title_de} onChange={(e) => setField('title_de', e.target.value)} /><TextInput label={t('missions.creator.titleEn')} value={form.title_en} onChange={(e) => setField('title_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.descriptionDe')} value={form.description_de} onChange={(e) => setField('description_de', e.target.value)} /><Textarea label={t('missions.creator.descriptionEn')} value={form.description_en} onChange={(e) => setField('description_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.questionDe')} value={form.question_de} onChange={(e) => setField('question_de', e.target.value)} /><Textarea label={t('missions.creator.questionEn')} value={form.question_en} onChange={(e) => setField('question_en', e.target.value)} /></SimpleGrid>
          {form.type !== 'compliance_traffic_light' && <SimpleGrid cols={2}><Textarea label={t('missions.creator.feedbackDe')} value={form.feedback_de} onChange={(e) => setField('feedback_de', e.target.value)} /><Textarea label={t('missions.creator.feedbackEn')} value={form.feedback_en} onChange={(e) => setField('feedback_en', e.target.value)} /></SimpleGrid>}
          {form.type === 'compliance_traffic_light' ? <Stack gap="sm">
            <Text fw={700}>{t('missions.creator.statements')}</Text>
            {form.statements.map((statement, index) => <Paper key={index} withBorder radius="md" p="sm">
              <Stack gap="sm">
                <Group grow><TextInput label={`DE ${index + 1}`} value={statement.de} onChange={(e) => setStatement(index, 'de', e.target.value)} /><TextInput label={`EN ${index + 1}`} value={statement.en} onChange={(e) => setStatement(index, 'en', e.target.value)} /></Group>
                <Select label={t('missions.creator.correctColor')} value={statement.correct_color} data={['green', 'yellow', 'red'].map((color) => ({ value: color, label: t(`missions.trafficLight.${color}`) }))} onChange={(value) => setStatement(index, 'correct_color', value)} />
                <Group grow><Textarea label={t('missions.creator.feedbackDe')} value={statement.feedback_de} onChange={(e) => setStatement(index, 'feedback_de', e.target.value)} /><Textarea label={t('missions.creator.feedbackEn')} value={statement.feedback_en} onChange={(e) => setStatement(index, 'feedback_en', e.target.value)} /></Group>
              </Stack>
            </Paper>)}
          </Stack> : <Stack gap="sm">
            <Group justify="space-between"><Text fw={700}>{t('missions.creator.answers')}</Text><Button size="xs" variant="light" leftSection={<IconPlus size={14} />} disabled={form.type === 'prompt_ranking' && form.options.length >= 4} onClick={addOption}>{t('missions.creator.addAnswer')}</Button></Group>
            {form.options.map((option, index) => <Paper key={index} withBorder radius="md" p="sm"><Group align="flex-end" wrap="nowrap">{form.type === 'prompt_ranking' ? <Badge variant="light">{form.correct_order.indexOf(index) + 1}</Badge> : form.type === 'multiple_choice' ? <Checkbox checked={form.correct_indices.includes(index)} onChange={() => toggleCorrectOption(index)} aria-label={t('missions.creator.correctAnswer')} /> : <Radio checked={form.correct_indices.includes(index)} onChange={() => setField('correct_indices', [index])} aria-label={t('missions.creator.correctAnswer')} />}<TextInput label={`DE ${index + 1}`} value={option.de} onChange={(e) => setOption(index, 'de', e.target.value)} style={{ flex: 1 }} /><TextInput label={`EN ${index + 1}`} value={option.en} onChange={(e) => setOption(index, 'en', e.target.value)} style={{ flex: 1 }} /></Group></Paper>)}
            {form.type === 'prompt_ranking' && <Stack gap="xs"><Text fw={700}>{t('missions.creator.rankingSolution')}</Text>{form.correct_order.map((optionIndex, position) => <Paper key={optionIndex} withBorder radius="md" p="xs"><Group justify="space-between" wrap="nowrap"><Text fz="sm">{position + 1}. {form.options[optionIndex]?.de || form.options[optionIndex]?.en || `${t('missions.creator.answers')} ${optionIndex + 1}`}</Text><Group gap={4}><Button variant="subtle" size="compact-sm" disabled={position === 0} onClick={() => setField('correct_order', moveItem(form.correct_order, position, -1))}><IconArrowUp size={16} /></Button><Button variant="subtle" size="compact-sm" disabled={position === form.correct_order.length - 1} onClick={() => setField('correct_order', moveItem(form.correct_order, position, 1))}><IconArrowDown size={16} /></Button></Group></Group></Paper>)}</Stack>}
          </Stack>}
          <NumberInput label={t('missions.creator.points')} min={1} max={1000} value={form.max_points} onChange={(value) => setField('max_points', value)} />
          {error && <Alert color="red">{error}</Alert>}
          <Button color="brand" loading={saving} onClick={save}>{editingId ? t('missions.creator.update') : t('missions.creator.save')}</Button>
        </Stack>
        <Stack gap="sm">
          <Group gap="sm"><IconCalendar size={20} /><Text fw={700}>{t('missions.creator.calendarTitle')}</Text></Group>
          <Text fz="sm" c="dimmed">{t('missions.creator.calendarText')}</Text>
          <Calendar month={month} setMonth={setMonth} schedule={schedule} selectedDate={form.scheduled_date} onSelect={(value) => setField('scheduled_date', value)} />
          {form.scheduled_date && <Stack gap="xs" mt="sm">
            <Text fw={700}>{t('missions.creator.scheduledFor', { date: new Date(`${form.scheduled_date}T12:00:00`).toLocaleDateString(i18n.resolvedLanguage) })}</Text>
            {missionsForDate.length === 0 && <Text fz="sm" c="dimmed">{t('missions.creator.noScheduled')}</Text>}
            {missionsForDate.map((mission) => <Paper key={mission.id} withBorder radius="md" p="sm">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Box>
                  <Text fw={700}>{mission.title_de}</Text>
                  <Text fz="sm" c="dimmed">{mission.title_en}</Text>
                </Box>
                <Group gap={4} wrap="nowrap">
                  <Button variant="subtle" size="compact-sm" aria-label={t('missions.creator.view')} onClick={() => { setShowPreviewSolution(false); setPreview(mission) }}><IconEye size={17} /></Button>
                  {mission.can_edit && !mission.has_attempts && <Button variant="subtle" size="compact-sm" aria-label={t('missions.creator.edit')} onClick={() => editMission(mission)}><IconEdit size={17} /></Button>}
                  {mission.can_delete && <Button color="red" variant="subtle" size="compact-sm" loading={deletingId === mission.id} disabled={mission.has_attempts} aria-label={t('missions.creator.delete')} onClick={() => removeMission(mission)}><IconTrash size={17} /></Button>}
                </Group>
              </Group>
              {mission.has_attempts && <Text fz="xs" c="orange" mt={6}>{t('missions.creator.deleteBlocked')}</Text>}
            </Paper>)}
          </Stack>}
        </Stack>
      </div>
      <Modal opened={Boolean(preview)} onClose={() => { setPreview(null); setShowPreviewSolution(false) }} title={t('missions.creator.previewTitle')} size="lg" centered>
        {preview && <Stack gap="md">
          <Switch checked={showPreviewSolution} onChange={(event) => setShowPreviewSolution(event.currentTarget.checked)} label={t('missions.creator.showSolution')} />
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
          {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Paper key={language} withBorder radius="md" p="md">
            <Stack gap="sm">
              <Badge variant="light">{label}</Badge>
              <Title order={4}>{preview[`title_${language}`]}</Title>
              <Text fz="sm" c="dimmed">{preview[`description_${language}`]}</Text>
              <Text fw={700}>{preview[`question_${language}`]}</Text>
              <MissionSolutionContent mission={preview} language={language} showSolution={showPreviewSolution} />
              {showPreviewSolution && preview.type !== 'compliance_traffic_light' && preview[`feedback_${language}`] && <Text fz="sm"><Text span fw={700}>{t('missions.review.feedback')}: </Text>{preview[`feedback_${language}`]}</Text>}
            </Stack>
          </Paper>)}
          </SimpleGrid>
          {preview.can_edit && !preview.has_attempts && <Button variant="light" leftSection={<IconEdit size={16} />} onClick={() => editMission(preview)}>{t('missions.creator.edit')}</Button>}
        </Stack>}
      </Modal>
    </Modal>
  )
}

function MissionReview({ enabled, onPublished }) {
  const { i18n, t } = useTranslation()
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activeAction, setActiveAction] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadReview = useCallback(() => {
    if (!enabled) return
    setLoading(true)
    return getReviewMissions()
      .then((data) => { setMissions(data.missions || []); setError('') })
      .catch((nextError) => setError(nextError.message))
      .finally(() => setLoading(false))
  }, [enabled])

  useEffect(() => {
    if (!enabled) return undefined
    let active = true
    getReviewMissions()
      .then((data) => {
        if (!active) return
        setMissions(data.missions || [])
        setError('')
      })
      .catch((nextError) => active && setError(nextError.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [enabled])

  const generate = async () => {
    setGenerating(true)
    setError('')
    setMessage('')
    try {
      const data = await generateNextWeekMissions()
      setMessage(t('missions.review.generated', { count: data.created_count }))
      loadReview()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setGenerating(false)
    }
  }

  const runAction = async (mission, action) => {
    if (action === 'reject' && !window.confirm(t('missions.review.rejectConfirm', { title: mission.title_de }))) return
    setActiveAction(`${action}-${mission.id}`)
    setError('')
    setMessage('')
    try {
      if (action === 'approve') await approveMission(mission.id)
      if (action === 'regenerate') await regenerateMission(mission.id)
      if (action === 'reject') await rejectMission(mission.id)
      setMessage(t(`missions.review.${action}Success`))
      await loadReview()
      if (action === 'approve') onPublished()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setActiveAction('')
    }
  }

  const runBulkAction = async (action) => {
    if (action === 'reject' && !window.confirm(t('missions.review.rejectAllConfirm', { count: missions.length }))) return
    setActiveAction(`${action}-all`)
    setError('')
    setMessage('')
    try {
      const data = action === 'approve' ? await approveAllReviewMissions() : await rejectAllReviewMissions()
      const count = action === 'approve' ? data.approved_count : data.rejected_count
      setMessage(t(`missions.review.${action}AllSuccess`, { count }))
      await loadReview()
      if (action === 'approve') onPublished()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setActiveAction('')
    }
  }

  if (!enabled) return null
  return (
    <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white" mt="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="flex-start">
          <Group align="flex-start" wrap="nowrap">
            <ThemeIcon size={44} radius="md" variant="light" color="accent"><IconSparkles size={23} /></ThemeIcon>
            <Box>
              <Title order={2} fz="xl">{t('missions.review.title')}</Title>
              <Text c="dimmed" fz="sm" mt={3}>{t('missions.review.description')}</Text>
            </Box>
          </Group>
          <Stack gap="xs" align="stretch">
            <Button color="brand" leftSection={<IconSparkles size={17} />} loading={generating} onClick={generate}>
              {t('missions.review.generate')}
            </Button>
            <Group gap="xs" grow>
              <Button color="green" variant="light" leftSection={<IconCheck size={16} />} disabled={missions.length === 0} loading={activeAction === 'approve-all'} onClick={() => runBulkAction('approve')}>{t('missions.review.approveAll')}</Button>
              <Button color="red" variant="light" leftSection={<IconX size={16} />} disabled={missions.length === 0} loading={activeAction === 'reject-all'} onClick={() => runBulkAction('reject')}>{t('missions.review.rejectAll')}</Button>
            </Group>
          </Stack>
        </Group>
        {error && <Alert color="red">{error}</Alert>}
        {message && <Alert color="green">{message}</Alert>}
        {loading ? <Text c="dimmed">{t('missions.review.loading')}</Text> : missions.length === 0 ? (
          <Paper withBorder radius="md" p="xl" bg="gray.0"><Text ta="center" c="dimmed">{t('missions.review.empty')}</Text></Paper>
        ) : <Stack gap="md">
          {missions.map((mission) => <Paper key={mission.id} withBorder radius="md" p="lg">
            <Stack gap="md">
              <Group justify="space-between" align="flex-start">
                <Box>
                  <Group gap="xs" mb={5}>
                    <Badge color="yellow" variant="light">{t('missions.review.status')}</Badge>
                    <Badge color="secondary" variant="light">{missionTypeLabel(t, mission.type)}</Badge>
                    <Text fz="sm" c="dimmed">{new Date(`${mission.scheduled_date}T12:00:00`).toLocaleDateString(i18n.resolvedLanguage)}</Text>
                  </Group>
                  <Text fw={700} fz="lg">{mission.title_de}</Text>
                  <Text c="dimmed" fz="sm">{mission.title_en}</Text>
                </Box>
                <Badge color="accent" variant="light">{mission.max_points} {t('missions.points')}</Badge>
              </Group>
              <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Box key={language}>
                  <Text fz="xs" fw={700} c="dimmed" tt="uppercase" mb={5}>{label}</Text>
                  <Text fz="sm" c="dimmed" mb="xs">{mission[`description_${language}`]}</Text>
                  <Text fw={700} fz="sm" mb="xs">{mission[`question_${language}`]}</Text>
                  <MissionSolutionContent mission={mission} language={language} />
                  {mission.type !== 'compliance_traffic_light' && <Text fz="sm" mt="sm"><Text span fw={700}>{t('missions.review.feedback')}: </Text>{mission[`feedback_${language}`]}</Text>}
                </Box>)}
              </SimpleGrid>
              <Group justify="flex-end">
                <Button color="red" variant="subtle" leftSection={<IconX size={16} />} loading={activeAction === `reject-${mission.id}`} onClick={() => runAction(mission, 'reject')}>{t('missions.review.reject')}</Button>
                <Button color="secondary" variant="light" leftSection={<IconRefresh size={16} />} loading={activeAction === `regenerate-${mission.id}`} onClick={() => runAction(mission, 'regenerate')}>{t('missions.review.regenerate')}</Button>
                <Button color="green" leftSection={<IconCheck size={16} />} loading={activeAction === `approve-${mission.id}`} onClick={() => runAction(mission, 'approve')}>{t('missions.review.approve')}</Button>
              </Group>
            </Stack>
          </Paper>)}
        </Stack>}
      </Stack>
    </Paper>
  )
}

export default function Missions({ user }) {
  const { t, i18n } = useTranslation()
  const { progress } = useUserProgress(user)
  const [missions, setMissions] = useState([])
  const [canCreate, setCanCreate] = useState(false)
  const [activeMission, setActiveMission] = useState(null)
  const [creatorOpen, setCreatorOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const language = i18n.resolvedLanguage === 'en' ? 'en' : 'de'

  const load = useCallback((showLoading = true) => {
    if (showLoading) setLoading(true)
    getDailyMissions(language).then((data) => { setMissions(data.missions || []); setCanCreate(Boolean(data.can_create)); setError('') }).catch((nextError) => setError(nextError.message)).finally(() => setLoading(false))
  }, [language])
  useEffect(() => {
    let active = true
    getDailyMissions(language)
      .then((data) => {
        if (!active) return
        setMissions(data.missions || [])
        setCanCreate(Boolean(data.can_create))
        setError('')
      })
      .catch((nextError) => active && setError(nextError.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [language])

  if (activeMission) return <MissionRunner mission={activeMission} onBack={() => { setActiveMission(null); load() }} onCompleted={(completed) => setMissions((current) => current.map((mission) => mission.id === completed.id ? completed : mission))} />

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Group justify="space-between" align="flex-start" mb="xl">
        <Box><Badge variant="light" color="brand" mb="sm">{t('missions.badge')}</Badge><Title order={1} fz={{ base: 28, md: 34 }}>{t('missions.title')}</Title><Text c="dimmed" fz="lg" mt={4}>{t('missions.description')}</Text></Box>
        <Group gap="sm">
          <Paper withBorder radius="md" px="md" py="xs" bg="white">
            <Group gap="xs" wrap="nowrap">
              <ThemeIcon color="orange" variant="light" size="sm"><IconFlame size={15} /></ThemeIcon>
              <Box><Text fz="xs" c="dimmed">{t('missions.streak.current')}</Text><Text fw={700}>{progress.currentStreak} · {t('missions.streak.best', { count: progress.maxStreak })}</Text></Box>
            </Group>
          </Paper>
          {canCreate && <Button color="brand" leftSection={<IconPlus size={18} />} onClick={() => setCreatorOpen(true)}>{t('missions.creator.button')}</Button>}
        </Group>
      </Group>
      {loading ? <Text c="dimmed">{t('missions.loading')}</Text> : error ? <Alert color="red">{error}</Alert> : missions.length === 0 ? <Paper withBorder radius="lg" p={48} bg="white"><Stack align="center"><ThemeIcon size={58} radius="xl" variant="light"><IconCalendar size={28} /></ThemeIcon><Text fw={700}>{t('missions.emptyTitle')}</Text><Text c="dimmed" ta="center">{t('missions.emptyText')}</Text></Stack></Paper> : <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">{missions.map((mission) => <MissionCard key={mission.id} mission={mission} onOpen={setActiveMission} />)}</SimpleGrid>}
      <MissionReview enabled={canCreate} onPublished={() => load(false)} />
      <Creator opened={creatorOpen} onClose={() => setCreatorOpen(false)} onCreated={load} />
    </Box>
  )
}
