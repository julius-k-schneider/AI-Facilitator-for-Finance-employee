import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActionIcon, Alert, Badge, Box, Button, Group, Loader, Menu, Modal, NumberInput, Paper, Select,
  SegmentedControl, SimpleGrid, Stack, Switch, Tabs, Text, Textarea, TextInput, ThemeIcon, Title,
} from '@mantine/core'
import {
  IconArrowRight, IconCalendar, IconCheck, IconChevronLeft,
  IconChevronRight, IconCircleCheck, IconEdit, IconEye, IconPlus, IconRefresh, IconSparkles,
  IconFlame, IconTargetArrow, IconTrash, IconX,
  IconBug,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useUserProgress } from '../hooks/useUserProgress'
import {
  approveAllReviewMissions, approveMission, createMission, deleteMission, generateTaskChallenge,
  getArchivedMissions, getAvailableMissions, getCurrentWeeklyGenerationRun, getDailyMissions, getGenerationRun,
  getMissionSchedule, getReviewMissions, regenerateMission, rejectMission, updateMission,
  rejectAllReviewMissions, startNextWeekMissionGeneration,
} from '../services/missionService'
import { createMissionTypeDefaults, createTestMissions, defaultMissionType, getMissionType, missionTypes, taskChallengeTypes } from './missions/missionTypes'
import MissionRunner from './missions/MissionRunner'
import './Missions.css'

const createEmptyForm = () => ({
  type: defaultMissionType, scheduled_date: '', title_de: '', title_en: '',
  description_de: '', description_en: '', question_de: '', question_en: '',
  feedback_de: '', feedback_en: '',
  micro_learning_de: '', micro_learning_en: '',
  max_points: 100, correct_indices: [0], ...createMissionTypeDefaults(),
})

const difficultyVariants = ['easy', 'medium', 'hard']

const createEmptyVariants = () => Object.fromEntries(
  difficultyVariants.map((difficulty) => [difficulty, createEmptyForm()]),
)

const createEmptySharedFields = () => ({
  topic_de: '', topic_en: '', learning_objective_de: '', learning_objective_en: '',
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

function weekRange(date) {
  const start = mondayOf(date)
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return { from: isoDate(start), to: isoDate(end) }
}

function archiveRange(mode, month, date) {
  if (mode === 'day') {
    const value = isoDate(date)
    return { from: value, to: value }
  }
  if (mode === 'week') return weekRange(date)
  return monthRange(month)
}

function addDays(date, days) {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

function appLocale(language) {
  return language === 'en' ? 'en-US' : 'de-DE'
}

function formatArchiveRange(mode, month, range, language) {
  const locale = appLocale(language)
  if (mode === 'month') {
    return month.toLocaleDateString(locale, { month: 'long', year: 'numeric' })
  }
  const dateOptions = mode === 'day'
    ? { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' }
    : { day: '2-digit', month: '2-digit', year: 'numeric' }
  const from = new Date(`${range.from}T12:00:00`).toLocaleDateString(locale, dateOptions)
  if (mode === 'day') return from
  const to = new Date(`${range.to}T12:00:00`).toLocaleDateString(locale, dateOptions)
  return `${from} - ${to}`
}

function mondayOf(date) {
  const result = new Date(date)
  const day = (result.getDay() + 6) % 7
  result.setDate(result.getDate() - day)
  result.setHours(12, 0, 0, 0)
  return result
}

function isBusinessDay(date) {
  const day = date.getDay()
  return day >= 1 && day <= 5
}

function nextWeekStart() {
  const monday = mondayOf(new Date())
  monday.setDate(monday.getDate() + 7)
  return isoDate(monday)
}

function currentWeekStart() {
  return isoDate(mondayOf(new Date()))
}

function missionTypeLabel(t, type) {
  return t(`missions.types.${getMissionType(type).labelKey}`)
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
    micro_learning_de: mission.micro_learning_de || '',
    micro_learning_en: mission.micro_learning_en || '',
    max_points: mission.max_points,
    correct_indices: mission.correct_indices?.length ? mission.correct_indices : [0],
    correct_order: mission.correct_order?.length ? mission.correct_order : (mission.options || []).map((_, index) => index),
    options: (mission.options || []).map((option) => ({ ...option })),
    statements: mission.statements?.length ? mission.statements.map((statement) => ({ ...statement })) : createEmptyForm().statements,
  }
}

function variantToReviewMission(mission, difficulty) {
  const variant = mission.variants?.[difficulty] || {}
  const content = variant.content || {}
  return {
    ...mission,
    ...variant,
    difficulty,
    question_de: content.question?.de || content.task?.de || '',
    question_en: content.question?.en || content.task?.en || '',
    options: content.options || [],
    correct_indices: content.correct_indices || [],
    correct_order: content.correct_order || [],
    statements: (content.statements || []).map((statement) => ({
      de: statement.text?.de,
      en: statement.text?.en,
      correct_color: statement.correct_color,
      feedback_de: statement.feedback?.de,
      feedback_en: statement.feedback?.en,
    })),
    case_format: content.case_format,
    case_data_de: content.case_data?.de || [],
    case_data_en: content.case_data?.en || [],
    result_fields: (content.result_fields || []).map((field) => ({
      ...field,
      label_de: field.label?.de || '',
      label_en: field.label?.en || '',
    })),
    feedback_de: content.feedback?.de || '',
    feedback_en: content.feedback?.en || '',
    micro_learning_de: content.micro_learning?.de || '',
    micro_learning_en: content.micro_learning?.en || '',
  }
}

function missionToVariantForms(mission) {
  return Object.fromEntries(difficultyVariants.map((difficulty) => [
    difficulty,
    mission.has_difficulty_variants
      ? missionToForm(variantToReviewMission(mission, difficulty))
      : missionToForm(mission),
  ]))
}

function MissionSolutionContent({ mission, language, showSolution = true }) {
  const { t } = useTranslation()
  const Solution = getMissionType(mission.type).Solution
  return <Solution mission={mission} language={language} showSolution={showSolution} t={t} />
}

function MissionCard({ mission, onOpen, archiveMode = false }) {
  const { i18n, t } = useTranslation()
  const missionDate = new Date(`${mission.scheduled_date}T12:00:00`)
  const formattedMissionDate = missionDate.toLocaleDateString(i18n.resolvedLanguage, {
    weekday: 'long',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
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
          <Group gap={6} mt="sm" align="center">
            <IconCalendar size={15} style={{ display: 'block', flexShrink: 0 }} />
            <Text c="dimmed" fz="sm" lh={1}>{formattedMissionDate}</Text>
          </Group>
        </Box>
        <Group justify="space-between">
          <Badge variant="light" color="secondary">{missionTypeLabel(t, mission.type)}</Badge>
          <Text fz="sm" fw={700} c="brand.7">
            {mission.completed ? `${mission.score}/${mission.max_points}` : mission.max_points} {t('missions.points')}
          </Text>
        </Group>
        <Button color="brand" variant={mission.completed || archiveMode ? 'light' : 'filled'} disabled={!archiveMode && mission.completed}
          rightSection={archiveMode ? <IconEye size={17} /> : mission.completed ? <IconCheck size={17} /> : <IconArrowRight size={17} />}
          onClick={() => onOpen(mission)}>
          {archiveMode ? t('missions.archive.viewButton') : mission.completed ? t('missions.completedButton') : t('missions.startButton')}
        </Button>
      </Stack>
    </Paper>
  )
}

function MissionList({ missions, loading, error, emptyTitle, emptyText, onSelect }) {
  const { t } = useTranslation()
  if (loading) return <Text c="dimmed">{t('missions.loading')}</Text>
  if (error) return <Alert color="red">{error}</Alert>
  if (missions.length === 0) {
    return (
      <Paper withBorder radius="lg" p={48} bg="white">
        <Stack align="center">
          <ThemeIcon size={58} radius="xl" variant="light"><IconCalendar size={28} /></ThemeIcon>
          <Text fw={700}>{emptyTitle}</Text>
          <Text c="dimmed" ta="center">{emptyText}</Text>
        </Stack>
      </Paper>
    )
  }
  return <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">{missions.map((mission) => <MissionCard key={mission.id} mission={mission} onOpen={onSelect} />)}</SimpleGrid>
}

function Calendar({ month, setMonth, schedule, selectedDate, selectedWeekStart, onSelect, weekMode = false }) {
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
          const dateValue = new Date(`${value}T12:00:00`)
          const weekend = !isBusinessDay(dateValue)
          const count = schedule[value] || 0
          const weekStart = isoDate(mondayOf(dateValue))
          const selected = weekMode ? selectedWeekStart === weekStart && !weekend : selectedDate === value
          const disabled = weekMode ? weekStart < currentWeekStart() || weekend : weekend
          return <button key={value} type="button" disabled={disabled} className={`mission-calendar-day${weekend ? ' is-weekend' : ''}${selected ? ' is-selected' : ''}`} onClick={() => onSelect(weekMode ? weekStart : value)}>
            <span>{day}</span>{count > 0 && <span className={`mission-calendar-count${count >= 1 ? ' is-full' : ''}`}>{count}/1</span>}
          </button>
        })}
      </div>
    </Paper>
  )
}

function Creator({ opened, onClose, onCreated }) {
  const { i18n, t } = useTranslation()
  const [variantForms, setVariantForms] = useState(createEmptyVariants)
  const [activeDifficulty, setActiveDifficulty] = useState('easy')
  const [sharedFields, setSharedFields] = useState(createEmptySharedFields)
  const [month, setMonth] = useState(new Date())
  const [schedule, setSchedule] = useState({})
  const [scheduledMissions, setScheduledMissions] = useState({})
  const [preview, setPreview] = useState(null)
  const [previewDifficulty, setPreviewDifficulty] = useState('easy')
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
  const form = variantForms[activeDifficulty]
  const setForm = (update) => setVariantForms((current) => ({
    ...current,
    [activeDifficulty]: typeof update === 'function' ? update(current[activeDifficulty]) : update,
  }))
  const setField = (field, value) => setForm((current) => ({ ...current, [field]: value }))
  const setSharedField = (field, value) => setSharedFields((current) => ({ ...current, [field]: value }))
  const setType = (value) => setVariantForms((current) => Object.fromEntries(
    difficultyVariants.map((difficulty) => {
      const next = { ...current[difficulty], ...getMissionType(value).createDefaults(), type: value }
      return [difficulty, getMissionType(value).prepareForm?.(next) || next]
    }),
  ))
  const setScheduledDate = (value) => setVariantForms((current) => Object.fromEntries(
    difficultyVariants.map((difficulty) => [difficulty, { ...current[difficulty], scheduled_date: value }]),
  ))
  const setOption = (index, language, value) => setForm((current) => ({ ...current, options: current.options.map((option, optionIndex) => optionIndex === index ? { ...option, [language]: value } : option) }))
  const toggleCorrectOption = (index) => setForm((current) => ({
    ...current,
    correct_indices: current.correct_indices.includes(index)
      ? current.correct_indices.filter((value) => value !== index)
      : [...current.correct_indices, index].sort((a, b) => a - b),
  }))
  const missionsForDate = form.scheduled_date ? scheduledMissions[form.scheduled_date] || [] : []

  const resetForm = () => {
    setVariantForms(createEmptyVariants())
    setSharedFields(createEmptySharedFields())
    setActiveDifficulty('easy')
    setEditingId(null)
  }

  const editMission = (mission) => {
    setVariantForms(missionToVariantForms(mission))
    setSharedFields({
      topic_de: mission.topic_de || mission.title_de || '',
      topic_en: mission.topic_en || mission.title_en || '',
      learning_objective_de: mission.learning_objective_de || mission.description_de || '',
      learning_objective_en: mission.learning_objective_en || mission.description_en || '',
    })
    setActiveDifficulty('easy')
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
      const payload = {
        type: form.type,
        scheduled_date: form.scheduled_date,
        ...sharedFields,
        variants: variantForms,
      }
      if (editingId) await updateMission(editingId, payload)
      else await createMission(payload)
      resetForm()
      loadSchedule()
      onCreated()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSaving(false)
    }
  }

  const previewMission = preview?.has_difficulty_variants
    ? variantToReviewMission(preview, previewDifficulty)
    : preview

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
          <Select label={t('missions.creator.type')} value={form.type} data={missionTypes.map((definition) => ({ value: definition.id, label: t(`missions.types.${definition.labelKey}`) }))} onChange={setType} />
          <TextInput
            type="date"
            label={t('missions.creator.date')}
            value={form.scheduled_date}
            min={editingId ? undefined : isoDate(new Date())}
            onChange={(event) => {
              const value = event.target.value
              if (!value || isBusinessDay(new Date(`${value}T12:00:00`))) setScheduledDate(value)
            }}
          />
          <Alert color="brand" variant="light">{t('missions.creator.adaptiveHint')}</Alert>
          <SimpleGrid cols={2}><TextInput label={t('missions.creator.topicDe')} value={sharedFields.topic_de} onChange={(e) => setSharedField('topic_de', e.target.value)} /><TextInput label={t('missions.creator.topicEn')} value={sharedFields.topic_en} onChange={(e) => setSharedField('topic_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.learningObjectiveDe')} value={sharedFields.learning_objective_de} onChange={(e) => setSharedField('learning_objective_de', e.target.value)} /><Textarea label={t('missions.creator.learningObjectiveEn')} value={sharedFields.learning_objective_en} onChange={(e) => setSharedField('learning_objective_en', e.target.value)} /></SimpleGrid>
          <Stack gap={5}>
            <Text fz="sm" fw={600}>{t('missions.creator.difficultyVariant')}</Text>
            <SegmentedControl
              fullWidth
              value={activeDifficulty}
              onChange={setActiveDifficulty}
              data={difficultyVariants.map((difficulty) => ({ value: difficulty, label: t(`difficulties.${difficulty}`) }))}
            />
          </Stack>
          <SimpleGrid cols={2}><TextInput label={t('missions.creator.titleDe')} value={form.title_de} onChange={(e) => setField('title_de', e.target.value)} /><TextInput label={t('missions.creator.titleEn')} value={form.title_en} onChange={(e) => setField('title_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.descriptionDe')} value={form.description_de} onChange={(e) => setField('description_de', e.target.value)} /><Textarea label={t('missions.creator.descriptionEn')} value={form.description_en} onChange={(e) => setField('description_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.questionDe')} value={form.question_de} onChange={(e) => setField('question_de', e.target.value)} /><Textarea label={t('missions.creator.questionEn')} value={form.question_en} onChange={(e) => setField('question_en', e.target.value)} /></SimpleGrid>
          {getMissionType(form.type).hasSharedFeedback && <SimpleGrid cols={2}><Textarea label={t('missions.creator.feedbackDe')} value={form.feedback_de} onChange={(e) => setField('feedback_de', e.target.value)} /><Textarea label={t('missions.creator.feedbackEn')} value={form.feedback_en} onChange={(e) => setField('feedback_en', e.target.value)} /></SimpleGrid>}
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.microLearningDe')} value={form.micro_learning_de} onChange={(e) => setField('micro_learning_de', e.target.value)} /><Textarea label={t('missions.creator.microLearningEn')} value={form.micro_learning_en} onChange={(e) => setField('micro_learning_en', e.target.value)} /></SimpleGrid>
          {(() => { const Editor = getMissionType(form.type).Editor; return <Editor form={form} setForm={setForm} setOption={setOption} toggleCorrectOption={toggleCorrectOption} t={t} /> })()}
          <NumberInput label={t('missions.creator.points')} min={1} max={1000} value={form.max_points} onChange={(value) => setField('max_points', value)} />
          {error && <Alert color="red">{error}</Alert>}
          <Button color="brand" loading={saving} onClick={save}>{editingId ? t('missions.creator.update') : t('missions.creator.save')}</Button>
        </Stack>
        <Stack gap="sm">
          <Group gap="sm"><IconCalendar size={20} /><Text fw={700}>{t('missions.creator.calendarTitle')}</Text></Group>
          <Text fz="sm" c="dimmed">{t('missions.creator.calendarText')}</Text>
          <Calendar month={month} setMonth={setMonth} schedule={schedule} selectedDate={form.scheduled_date} onSelect={setScheduledDate} />
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
                  <Button variant="subtle" size="compact-sm" aria-label={t('missions.creator.view')} onClick={() => { setShowPreviewSolution(false); setPreviewDifficulty('easy'); setPreview(mission) }}><IconEye size={17} /></Button>
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
        {previewMission && <Stack gap="md">
          {preview?.has_difficulty_variants && <SegmentedControl
            fullWidth
            value={previewDifficulty}
            onChange={setPreviewDifficulty}
            data={difficultyVariants.map((difficulty) => ({ value: difficulty, label: t(`difficulties.${difficulty}`) }))}
          />}
          <Switch checked={showPreviewSolution} onChange={(event) => setShowPreviewSolution(event.currentTarget.checked)} label={t('missions.creator.showSolution')} />
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
          {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Paper key={language} withBorder radius="md" p="md">
            <Stack gap="sm">
              <Badge variant="light">{label}</Badge>
              <Title order={4}>{previewMission[`title_${language}`]}</Title>
              <Text fz="sm" c="dimmed">{previewMission[`description_${language}`]}</Text>
              <Text fw={700}>{previewMission[`question_${language}`]}</Text>
              <MissionSolutionContent mission={previewMission} language={language} showSolution={showPreviewSolution} />
              {showPreviewSolution && getMissionType(previewMission.type).hasSharedFeedback && previewMission[`feedback_${language}`] && <Text fz="sm"><Text span fw={700}>{t('missions.review.feedback')}: </Text>{previewMission[`feedback_${language}`]}</Text>}
              {showPreviewSolution && previewMission[`micro_learning_${language}`] && <Text fz="sm"><Text span fw={700}>{t('missions.microLearning.title')}: </Text>{previewMission[`micro_learning_${language}`]}</Text>}
            </Stack>
          </Paper>)}
          </SimpleGrid>
          {preview.can_edit && !preview.has_attempts && getMissionType(preview.type).Editor && <Button variant="light" leftSection={<IconEdit size={16} />} onClick={() => editMission(preview)}>{t('missions.creator.edit')}</Button>}
        </Stack>}
      </Modal>
    </Modal>
  )
}

const visibleGenerationStatuses = ['running', 'validating', 'reviewing', 'repairing']
const activeGenerationStatuses = new Set(['queued', 'dispatched', ...visibleGenerationStatuses])
const weeklyGenerationStorageKey = 'missions.current-weekly-generation-run'

function rememberWeeklyGenerationRun(runId) {
  try {
    if (runId) window.localStorage.setItem(weeklyGenerationStorageKey, runId)
  } catch {
    // The backend lookup still restores active runs if storage is unavailable.
  }
}

function rememberedWeeklyGenerationRun() {
  try {
    return window.localStorage.getItem(weeklyGenerationStorageKey)
  } catch {
    return null
  }
}

function forgetWeeklyGenerationRun() {
  try {
    window.localStorage.removeItem(weeklyGenerationStorageKey)
  } catch {
    // Nothing else is required when storage is unavailable.
  }
}

function GenerationStatus({ run }) {
  const { i18n, t } = useTranslation()
  const status = run?.status || 'queued'
  const displayStatus = ['queued', 'dispatched'].includes(status) ? 'preparing' : status
  const locale = i18n.resolvedLanguage || i18n.language
  const updatedAt = run?.updated_at
    ? new Date(run.updated_at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null
  const weekStart = run?.week_start
    ? new Date(`${run.week_start}T12:00:00`).toLocaleDateString(locale)
    : null
  const weekEnd = run?.week_end
    ? new Date(`${run.week_end}T12:00:00`).toLocaleDateString(locale)
    : null

  return (
    <Paper className="mission-generation-status" withBorder radius="md" p="md" role="status" aria-live="polite">
      <Group align="flex-start" wrap="nowrap">
        <Loader color="brand" size="sm" mt={3} />
        <Box style={{ flex: 1, minWidth: 0 }}>
          <Group gap="xs" justify="space-between" align="center">
            <Text fw={700}>{t('missions.review.generationStatus.title')}</Text>
            <Badge color="brand" variant="light">
              {t(`missions.review.generationStatus.statuses.${displayStatus}`)}
            </Badge>
          </Group>
          <Text c="dimmed" fz="sm" mt={4}>
            {t(`missions.review.generationStatus.descriptions.${displayStatus}`)}
          </Text>
          {(weekStart || updatedAt) && <Group gap="md" mt={6}>
            {weekStart && <Text c="dimmed" fz="xs">
              {t('missions.review.generationStatus.week', { start: weekStart, end: weekEnd || weekStart })}
            </Text>}
            {updatedAt && <Text c="dimmed" fz="xs">
              {t('missions.review.generationStatus.lastUpdate', { time: updatedAt })}
            </Text>}
          </Group>}
          <Group className="mission-generation-status__steps" gap="xs" mt="sm">
            {visibleGenerationStatuses.map((step) => (
              <Badge
                className={displayStatus === step ? 'is-active' : ''}
                color={displayStatus === step ? 'brand' : 'gray'}
                key={step}
                variant={displayStatus === step ? 'filled' : 'light'}
              >
                {t(`missions.review.generationStatus.statuses.${step}`)}
              </Badge>
            ))}
          </Group>
        </Box>
      </Group>
    </Paper>
  )
}

function MissionReview({ enabled, onPublished }) {
  const { i18n, t } = useTranslation()
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generationRun, setGenerationRun] = useState(null)
  const [activeAction, setActiveAction] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [weekSelectionOpen, setWeekSelectionOpen] = useState(false)
  const [generationMonth, setGenerationMonth] = useState(() => new Date(`${nextWeekStart()}T12:00:00`))
  const [generationWeek, setGenerationWeek] = useState(nextWeekStart)
  const [generationSchedule, setGenerationSchedule] = useState({})

  const loadGenerationSchedule = useCallback(() => {
    const range = monthRange(generationMonth)
    return getMissionSchedule(range.from, range.to)
      .then((data) => setGenerationSchedule(data.dates || {}))
      .catch(() => setGenerationSchedule({}))
  }, [generationMonth])

  useEffect(() => {
    if (!enabled) return undefined
    loadGenerationSchedule()
    return undefined
  }, [enabled, loadGenerationSchedule])

  const loadReview = useCallback(() => {
    if (!enabled) return
    setLoading(true)
    return getReviewMissions(generationWeek)
      .then((data) => { setMissions(data.missions || []); setError('') })
      .catch((nextError) => setError(nextError.message))
      .finally(() => setLoading(false))
  }, [enabled, generationWeek])

  useEffect(() => {
    if (!enabled) return undefined
    let active = true
    getReviewMissions(generationWeek)
      .then((data) => {
        if (!active) return
        setMissions(data.missions || [])
        setError('')
      })
      .catch((nextError) => active && setError(nextError.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [enabled, generationWeek])

  const finalizeGeneration = useCallback(async (run) => {
    forgetWeeklyGenerationRun()
    setGenerating(false)
    setGenerationRun(null)
    if (run.status === 'completed') {
      setError('')
      setMessage(run.failed_count > 0
        ? t('missions.review.generatedPartial', {
          count: run.created_count || 0,
          failedCount: run.failed_count,
        })
        : t('missions.review.generated', { count: run.created_count || 0 }))
      await Promise.all([loadReview(), loadGenerationSchedule()])
      return
    }
    setMessage('')
    setError(run.error_message || t('missions.review.generationStatus.failed'))
  }, [loadGenerationSchedule, loadReview, t])
  const finalizeGenerationRef = useRef(finalizeGeneration)

  useEffect(() => {
    finalizeGenerationRef.current = finalizeGeneration
  }, [finalizeGeneration])

  useEffect(() => {
    if (!enabled) return undefined
    let active = true

    const restoreGeneration = async () => {
      let run = null
      let lookupError = null
      try {
        const data = await getCurrentWeeklyGenerationRun()
        run = data.generation_run
      } catch (nextError) {
        lookupError = nextError
      }

      const rememberedRunId = rememberedWeeklyGenerationRun()
      if (!run && rememberedRunId) {
        try {
          const data = await getGenerationRun(rememberedRunId)
          run = data.generation_run
        } catch (nextError) {
          if (nextError.status === 404 || nextError.status === 403) forgetWeeklyGenerationRun()
          else lookupError = lookupError || nextError
        }
      }

      if (!active) return
      if (!run) {
        if (lookupError) setError(lookupError.message)
        return
      }

      if (run.week_start) {
        setGenerationWeek(run.week_start)
        setGenerationMonth(new Date(`${run.week_start}T12:00:00`))
      }
      if (!activeGenerationStatuses.has(run.status)) {
        await finalizeGenerationRef.current(run)
        return
      }
      rememberWeeklyGenerationRun(run.id)
      setGenerationRun(run)
      setGenerating(true)
    }

    restoreGeneration()
    return () => { active = false }
  }, [enabled])

  useEffect(() => {
    const runId = generationRun?.id
    if (!enabled || !runId) return undefined
    let active = true
    let timerId = null

    const pollGeneration = async () => {
      try {
        const data = await getGenerationRun(runId)
        if (!active) return
        const run = data.generation_run
        setGenerationRun(run)
        if (!activeGenerationStatuses.has(run.status)) {
          await finalizeGenerationRef.current(run)
          return
        }
        setGenerating(true)
        timerId = window.setTimeout(pollGeneration, 1500)
      } catch (nextError) {
        if (!active) return
        setError(nextError.message)
        timerId = window.setTimeout(pollGeneration, 3000)
      }
    }

    timerId = window.setTimeout(pollGeneration, 500)

    return () => {
      active = false
      if (timerId) window.clearTimeout(timerId)
    }
  }, [enabled, generationRun?.id])

  const generate = async () => {
    setGenerating(true)
    setGenerationRun({ status: 'queued' })
    setError('')
    setMessage('')
    try {
      const data = await startNextWeekMissionGeneration(generationWeek, false)
      const run = data.generation_run
      rememberWeeklyGenerationRun(run.id)
      setGenerationRun(run)
      if (!activeGenerationStatuses.has(run.status)) await finalizeGeneration(run)
    } catch (nextError) {
      setError(nextError.message)
      setGenerating(false)
      setGenerationRun(null)
    }
  }

  const generateTask = async (missionType) => {
    setGenerating(true)
    setError('')
    setMessage('')
    try {
      await generateTaskChallenge(missionType, generationWeek)
      setMessage(t('missions.review.taskGenerated'))
      await Promise.all([loadReview(), loadGenerationSchedule()])
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
      await Promise.all([loadReview(), loadGenerationSchedule()])
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
      const data = action === 'approve' ? await approveAllReviewMissions(generationWeek) : await rejectAllReviewMissions(generationWeek)
      const count = action === 'approve' ? data.approved_count : data.rejected_count
      setMessage(t(`missions.review.${action}AllSuccess`, { count }))
      await Promise.all([loadReview(), loadGenerationSchedule()])
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
            <Menu position="bottom-end" withinPortal>
              <Menu.Target>
                <Button color="brand" variant="light" leftSection={<IconTargetArrow size={17} />} loading={generating}>
                  {t('missions.review.generateTask')}
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                {taskChallengeTypes.map((definition) => (
                  <Menu.Item key={definition.id} onClick={() => generateTask(definition.id)}>
                    {t(`missions.types.${definition.labelKey}`)}
                  </Menu.Item>
                ))}
              </Menu.Dropdown>
            </Menu>
            <Group gap="xs" grow>
              <Button color="green" variant="light" leftSection={<IconCheck size={16} />} disabled={missions.length === 0} loading={activeAction === 'approve-all'} onClick={() => runBulkAction('approve')}>{t('missions.review.approveAll')}</Button>
              <Button color="red" variant="light" leftSection={<IconX size={16} />} disabled={missions.length === 0} loading={activeAction === 'reject-all'} onClick={() => runBulkAction('reject')}>{t('missions.review.rejectAll')}</Button>
            </Group>
          </Stack>
        </Group>
        <Group justify="space-between">
          <Text fw={700}>{t('missions.review.selectedWeek', {
            start: new Date(`${generationWeek}T12:00:00`).toLocaleDateString(i18n.resolvedLanguage),
            end: new Date(new Date(`${generationWeek}T12:00:00`).getTime() + 6 * 86400000).toLocaleDateString(i18n.resolvedLanguage),
          })}</Text>
          <Button variant="light" leftSection={<IconCalendar size={17} />} onClick={() => setWeekSelectionOpen((current) => !current)}>{t('missions.review.selectWeekButton')}</Button>
        </Group>
        <Modal opened={weekSelectionOpen} onClose={() => setWeekSelectionOpen(false)} title={t('missions.review.selectWeek')} size="lg" centered>
          <Stack gap="md"><Text c="dimmed" fz="sm">{t('missions.review.selectWeekDescription')}</Text><Calendar month={generationMonth} setMonth={setGenerationMonth} schedule={generationSchedule} selectedWeekStart={generationWeek} onSelect={(value) => { setGenerationWeek(value); setWeekSelectionOpen(false) }} weekMode /></Stack>
        </Modal>
        {error && <Alert color="red">{error}</Alert>}
        {message && <Alert color="green">{message}</Alert>}
        {generating && generationRun && <GenerationStatus run={generationRun} />}
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
              {mission.has_difficulty_variants && <Stack gap="sm">
                <Text fz="sm"><Text span fw={700}>{t('missions.review.learningObjective')}: </Text>{mission.learning_objective_de}</Text>
                {['easy', 'medium', 'hard'].map((difficulty) => {
                  const variantMission = variantToReviewMission(mission, difficulty)
                  return <Paper key={difficulty} withBorder radius="sm" p="md" bg="gray.0">
                    <Badge mb="sm" color="secondary" variant="light">{t(`difficulties.${difficulty}`)}</Badge>
                    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                      {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Box key={language}>
                        <Text fz="xs" fw={700} c="dimmed" tt="uppercase">{label}</Text>
                        <Text fw={700}>{variantMission[`title_${language}`]}</Text>
                        <Text fz="sm" c="dimmed">{variantMission[`description_${language}`]}</Text>
                        <Text fw={700} fz="sm" mt="xs">{variantMission[`question_${language}`]}</Text>
                        <MissionSolutionContent mission={variantMission} language={language} />
                        {variantMission[`micro_learning_${language}`] && <Text fz="sm" mt="xs"><Text span fw={700}>{t('missions.microLearning.title')}: </Text>{variantMission[`micro_learning_${language}`]}</Text>}
                      </Box>)}
                    </SimpleGrid>
                  </Paper>
                })}
              </Stack>}
              {!mission.has_difficulty_variants && <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Box key={language}>
                  <Text fz="xs" fw={700} c="dimmed" tt="uppercase" mb={5}>{label}</Text>
                  <Text fz="sm" c="dimmed" mb="xs">{mission[`description_${language}`]}</Text>
                  <Text fw={700} fz="sm" mb="xs">{mission[`question_${language}`]}</Text>
                  <MissionSolutionContent mission={mission} language={language} />
                  {getMissionType(mission.type).hasSharedFeedback && <Text fz="sm" mt="sm"><Text span fw={700}>{t('missions.review.feedback')}: </Text>{mission[`feedback_${language}`]}</Text>}
                  {mission[`micro_learning_${language}`] && <Text fz="sm" mt="sm"><Text span fw={700}>{t('missions.microLearning.title')}: </Text>{mission[`micro_learning_${language}`]}</Text>}
                </Box>)}
              </SimpleGrid>}
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

function MissionTestArea({ language, onSelect }) {
  const { t } = useTranslation()
  const [opened, setOpened] = useState(false)
  const examples = createTestMissions(language)
  return <>
    <Paper withBorder radius="lg" p="xl" bg="white" mt="xl">
      <Group justify="space-between"><Box><Group gap="xs"><IconBug size={20} /><Text fw={700}>{t('missions.test.title')}</Text></Group><Text fz="sm" c="dimmed" mt={4}>{t('missions.test.description')}</Text></Box><Button variant="light" leftSection={<IconBug size={17} />} onClick={() => setOpened(true)}>{t('missions.test.button')}</Button></Group>
    </Paper>
    <Modal opened={opened} onClose={() => setOpened(false)} title={t('missions.test.title')} size="xl" centered>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">{examples.map((mission) => <MissionCard key={mission.id} mission={mission} onOpen={(selected) => { setOpened(false); onSelect(selected) }} />)}</SimpleGrid>
    </Modal>
  </>
}

function defaultArchiveMonth() {
  return new Date()
}

function ArchivePeriodPicker({ mode, month, setMonth, date, setDate, label, valueLabel, onMove }) {
  const inputRef = useRef(null)
  const inputValue = mode === 'month'
    ? `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}`
    : isoDate(date)
  const openPicker = () => {
    if (inputRef.current?.showPicker) inputRef.current.showPicker()
    else inputRef.current?.click()
  }

  return (
    <Stack gap={5} className="archive-period-picker">
      <Text fz="sm" fw={600}>{label}</Text>
      <Group gap={0} wrap="nowrap" className="archive-period-control">
        <ActionIcon variant="subtle" size={40} className="archive-period-step" aria-label="Previous period" onClick={() => onMove(-1)}>
          <IconChevronLeft size={18} />
        </ActionIcon>
        <Box className="archive-period-value">
          <Button variant="subtle" h={40} fullWidth className="archive-period-button" leftSection={<IconCalendar size={16} />} onClick={openPicker}>
            {valueLabel}
          </Button>
          <input
            ref={inputRef}
            className="archive-period-native-input"
            type={mode === 'month' ? 'month' : 'date'}
            value={inputValue}
            onChange={(event) => {
              if (!event.target.value) return
              if (mode === 'month') {
                const [year, monthIndex] = event.target.value.split('-').map(Number)
                if (year && monthIndex) setMonth(new Date(year, monthIndex - 1, 1))
              } else {
                setDate(new Date(`${event.target.value}T12:00:00`))
              }
            }}
            tabIndex={-1}
          />
        </Box>
        <ActionIcon variant="subtle" size={40} className="archive-period-step" aria-label="Next period" onClick={() => onMove(1)}>
          <IconChevronRight size={18} />
        </ActionIcon>
      </Group>
    </Stack>
  )
}

function ArchiveTab({ language, month, setMonth, type, setType, onSelect }) {
  const { t } = useTranslation()
  const [mode, setMode] = useState('month')
  const [date, setDate] = useState(new Date())
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const range = archiveRange(mode, month, date)
  const rangeLabel = formatArchiveRange(mode, month, range, language)

  useEffect(() => {
    let active = true
    const params = {
      from: range.from,
      to: range.to,
      lang: language,
    }
    if (type !== 'all') params.type = type
    getArchivedMissions(params)
      .then((data) => {
        if (!active) return
        setMissions(data.missions || [])
        setError('')
      })
      .catch((nextError) => active && setError(nextError.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [range.from, range.to, type, language])

  const moveRange = (direction) => {
    if (mode === 'month') {
      setMonth(new Date(month.getFullYear(), month.getMonth() + direction, 1))
    } else {
      setDate((current) => addDays(current, direction * (mode === 'week' ? 7 : 1)))
    }
  }

  return <Stack gap="lg">
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start" gap="lg">
        <Box>
          <Text fw={700}>{t('missions.archive.filterTitle')}</Text>
          <Text fz="sm" c="dimmed">{t('missions.archive.filterText')}</Text>
        </Box>
        <div className="archive-filter-grid">
          <Stack gap={5} className="archive-mode-field">
            <Text fz="sm" fw={600}>{t('missions.archive.viewMode')}</Text>
            <SegmentedControl
              value={mode}
              className="archive-mode-control"
              data={[
                { value: 'month', label: t('missions.archive.modeMonth') },
                { value: 'week', label: t('missions.archive.modeWeek') },
                { value: 'day', label: t('missions.archive.modeDay') },
              ]}
              onChange={setMode}
            />
          </Stack>
          <ArchivePeriodPicker
            mode={mode}
            month={month}
            setMonth={setMonth}
            date={date}
            setDate={setDate}
            label={mode === 'month' ? t('missions.archive.month') : mode === 'week' ? t('missions.archive.week') : t('missions.archive.day')}
            valueLabel={rangeLabel}
            onMove={moveRange}
          />
          <Select
            label={t('missions.archive.typeFilter')}
            value={type}
            data={[
              { value: 'all', label: t('missions.archive.typeAll') },
              ...missionTypes.map((definition) => ({ value: definition.id, label: t(`missions.types.${definition.labelKey}`) })),
            ]}
            onChange={(value) => setType(value || 'all')}
          />
        </div>
      </Group>
    </Paper>
    {loading ? <Text c="dimmed">{t('missions.archive.loading')}</Text> : error ? <Alert color="red">{error}</Alert> : missions.length === 0 ? (
      <Paper withBorder radius="lg" p={48} bg="white"><Stack align="center"><ThemeIcon size={58} radius="xl" variant="light"><IconCalendar size={28} /></ThemeIcon><Text fw={700}>{t('missions.archive.emptyTitle')}</Text><Text c="dimmed" ta="center">{t('missions.archive.emptyText')}</Text></Stack></Paper>
    ) : <>
      <Text fz="sm" c="dimmed">{t('missions.archive.rangeResult', { range: rangeLabel })}</Text>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {missions.map((mission) => <MissionCard key={mission.id} mission={mission} archiveMode onOpen={onSelect} />)}
      </SimpleGrid>
    </>}
  </Stack>
}

export default function Missions({ user }) {
  const { t, i18n } = useTranslation()
  const { progress } = useUserProgress(user)
  const [missions, setMissions] = useState([])
  const [availableMissions, setAvailableMissions] = useState([])
  const [canCreate, setCanCreate] = useState(false)
  const [activeMission, setActiveMission] = useState(null)
  const [activeArchiveMission, setActiveArchiveMission] = useState(null)
  const [activeTab, setActiveTab] = useState('today')
  const [archiveMonth, setArchiveMonth] = useState(defaultArchiveMonth)
  const [archiveType, setArchiveType] = useState('all')
  const [testMissionId, setTestMissionId] = useState(null)
  const [creatorOpen, setCreatorOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [availableLoading, setAvailableLoading] = useState(true)
  const [error, setError] = useState('')
  const [availableError, setAvailableError] = useState('')
  const language = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  const activeArchiveMissionId = activeArchiveMission?.id
  const activeArchiveMissionDate = activeArchiveMission?.scheduled_date
  const activeArchiveMissionType = activeArchiveMission?.type
  const activeMissionId = activeMission?.id
  const activeMissionDate = activeMission?.scheduled_date
  const activeMissionType = activeMission?.type
  const testMission = createTestMissions(language).find((mission) => mission.id === testMissionId)

  const load = useCallback((showLoading = true) => {
    if (showLoading) setLoading(true)
    getDailyMissions(language).then((data) => { setMissions(data.missions || []); setCanCreate(Boolean(data.can_create)); setError('') }).catch((nextError) => setError(nextError.message)).finally(() => setLoading(false))
  }, [language])
  const loadAvailable = useCallback((showLoading = true) => {
    if (showLoading) setAvailableLoading(true)
    getAvailableMissions(language).then((data) => { setAvailableMissions(data.missions || []); setAvailableError('') }).catch((nextError) => setAvailableError(nextError.message)).finally(() => setAvailableLoading(false))
  }, [language])
  const setTab = (value) => {
    const nextTab = value || 'today'
    if (nextTab === 'archive' && activeTab !== 'archive') {
      setArchiveMonth(defaultArchiveMonth())
      setArchiveType('all')
    }
    setActiveTab(nextTab)
  }
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
  useEffect(() => {
    let active = true
    getAvailableMissions(language)
      .then((data) => {
        if (!active) return
        setAvailableMissions(data.missions || [])
        setAvailableError('')
      })
      .catch((nextError) => active && setAvailableError(nextError.message))
      .finally(() => active && setAvailableLoading(false))
    return () => { active = false }
  }, [language])
  useEffect(() => {
    if (!activeArchiveMissionId || !activeArchiveMissionDate) return undefined
    let active = true
    const params = {
      from: activeArchiveMissionDate,
      to: activeArchiveMissionDate,
      lang: language,
    }
    if (activeArchiveMissionType) params.type = activeArchiveMissionType
    getArchivedMissions(params)
      .then((data) => {
        if (!active) return
        const translatedMission = (data.missions || []).find((mission) => mission.id === activeArchiveMissionId)
        if (translatedMission) setActiveArchiveMission(translatedMission)
      })
      .catch(() => {})
    return () => { active = false }
  }, [activeArchiveMissionId, activeArchiveMissionDate, activeArchiveMissionType, language])
  useEffect(() => {
    if (!activeMissionId || !activeMissionDate) return undefined
    if (!activeMission?.completed) {
      const translatedMission = [...missions, ...availableMissions].find((mission) => mission.id === activeMissionId)
      let active = true
      Promise.resolve().then(() => {
        if (active && translatedMission) setActiveMission(translatedMission)
      })
      return () => { active = false }
    }
    let active = true
    const params = {
      from: activeMissionDate,
      to: activeMissionDate,
      lang: language,
    }
    if (activeMissionType) params.type = activeMissionType
    getArchivedMissions(params)
      .then((data) => {
        if (!active) return
        const translatedMission = (data.missions || []).find((mission) => mission.id === activeMissionId)
        if (translatedMission) setActiveMission(translatedMission)
      })
      .catch(() => {})
    return () => { active = false }
  }, [activeMissionId, activeMissionDate, activeMissionType, activeMission?.completed, missions, availableMissions, language])

  if (testMission) return <MissionRunner mission={testMission} language={language} testMode onBack={() => setTestMissionId(null)} onCompleted={() => {}} />
  if (activeArchiveMission) return <MissionRunner mission={activeArchiveMission} language={language} readOnly showSubmit={false} onBack={() => { setActiveArchiveMission(null); setActiveTab('archive') }} backLabel={t('missions.archive.back')} />
  if (activeMission) return <MissionRunner mission={activeMission} language={language} onBack={() => { setActiveMission(null); load(); loadAvailable(false) }} onCompleted={(completed) => {
    setActiveMission(completed)
    setMissions((current) => current.map((mission) => mission.id === completed.id ? completed : mission))
    setAvailableMissions((current) => current.filter((mission) => mission.id !== completed.id))
  }} />

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
      <Tabs value={activeTab} onChange={setTab}>
        <Tabs.List mb="lg">
          <Tabs.Tab value="today" leftSection={<IconTargetArrow size={16} />}>{t('missions.tabs.today')}</Tabs.Tab>
          <Tabs.Tab value="available" leftSection={<IconCalendar size={16} />}>{t('missions.tabs.available')}</Tabs.Tab>
          <Tabs.Tab value="archive" leftSection={<IconCalendar size={16} />}>{t('missions.tabs.archive')}</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="today">
          <MissionList missions={missions} loading={loading} error={error} emptyTitle={t('missions.todayEmptyTitle')} emptyText={t('missions.todayEmptyText')} onSelect={setActiveMission} />
          <MissionReview enabled={canCreate} onPublished={() => load(false)} />
          {user?.role === 'admin' && <MissionTestArea language={language} onSelect={(selected) => setTestMissionId(selected.id)} />}
        </Tabs.Panel>
        <Tabs.Panel value="available">
          <MissionList missions={availableMissions} loading={availableLoading} error={availableError} emptyTitle={t('missions.availableEmptyTitle')} emptyText={t('missions.availableEmptyText')} onSelect={setActiveMission} />
        </Tabs.Panel>
        <Tabs.Panel value="archive">
          <ArchiveTab
            language={language}
            month={archiveMonth}
            setMonth={setArchiveMonth}
            type={archiveType}
            setType={setArchiveType}
            onSelect={(mission) => { setActiveArchiveMission(mission); setActiveTab('archive') }}
          />
        </Tabs.Panel>
      </Tabs>
      <Creator opened={creatorOpen} onClose={() => setCreatorOpen(false)} onCreated={load} />
    </Box>
  )
}
