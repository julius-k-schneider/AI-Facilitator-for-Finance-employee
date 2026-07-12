import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Box, Button, Group, Modal, NumberInput, Paper, Select,
  SimpleGrid, Stack, Switch, Text, Textarea, TextInput, ThemeIcon, Title,
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
  approveAllReviewMissions, approveMission, createMission, deleteMission, generateNextWeekMissions, getDailyMissions, getLearningInsights,
  getMissionSchedule, getReviewMissions, regenerateMission, rejectMission, updateMission,
  rejectAllReviewMissions,
} from '../services/missionService'
import { createMissionTypeDefaults, createTestMissions, defaultMissionType, getMissionType, missionTypes } from './missions/missionTypes'
import MissionRunner from './missions/MissionRunner'
import './Missions.css'

const createEmptyForm = () => ({
  type: defaultMissionType, scheduled_date: '', title_de: '', title_en: '',
  description_de: '', description_en: '', question_de: '', question_en: '',
  feedback_de: '', feedback_en: '',
  max_points: 100, correct_indices: [0], ...createMissionTypeDefaults(),
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

function mondayOf(date) {
  const result = new Date(date)
  const day = (result.getDay() + 6) % 7
  result.setDate(result.getDate() - day)
  result.setHours(12, 0, 0, 0)
  return result
}

function nextWeekStart() {
  const monday = mondayOf(new Date())
  monday.setDate(monday.getDate() + 7)
  return isoDate(monday)
}

function currentWeekStart() {
  return isoDate(mondayOf(new Date()))
}

function selectedLanguage(i18n) {
  return (i18n.resolvedLanguage || i18n.language || 'de')
    .split('-')[0] === 'en'
    ? 'en'
    : 'de'
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
    max_points: mission.max_points,
    correct_indices: mission.correct_indices?.length ? mission.correct_indices : [0],
    correct_order: mission.correct_order?.length ? mission.correct_order : (mission.options || []).map((_, index) => index),
    options: (mission.options || []).map((option) => ({ ...option })),
    statements: mission.statements?.length ? mission.statements.map((statement) => ({ ...statement })) : createEmptyForm().statements,
  }
}

function MissionSolutionContent({ mission, language, showSolution = true }) {
  const { t } = useTranslation()
  const Solution = getMissionType(mission.type).Solution
  return <Solution mission={mission} language={language} showSolution={showSolution} t={t} />
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
          const count = schedule[value] || 0
          const weekStart = isoDate(mondayOf(new Date(`${value}T12:00:00`)))
          const selected = weekMode ? selectedWeekStart === weekStart : selectedDate === value
          const disabled = weekMode && weekStart < currentWeekStart()
          return <button key={value} type="button" disabled={disabled} className={`mission-calendar-day${selected ? ' is-selected' : ''}`} onClick={() => onSelect(weekMode ? weekStart : value)}>
            <span>{day}</span>{count > 0 && <span className={`mission-calendar-count${count >= 2 ? ' is-full' : ''}`}>{count}/2</span>}
          </button>
        })}
      </div>
    </Paper>
  )
}

function Creator({ opened, onClose, onCreated }) {
  const { i18n, t } = useTranslation()
  const language = selectedLanguage(i18n)
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
  const setType = (value) => setForm((current) => {
    const next = { ...current, ...getMissionType(value).createDefaults(), type: value }
    return getMissionType(value).prepareForm?.(next) || next
  })
  const setOption = (index, language, value) => setForm((current) => ({ ...current, options: current.options.map((option, optionIndex) => optionIndex === index ? { ...option, [language]: value } : option) }))
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
          <Select label={t('missions.creator.type')} value={form.type} data={missionTypes.map((definition) => ({ value: definition.id, label: t(`missions.types.${definition.labelKey}`) }))} onChange={setType} />
          <TextInput type="date" label={t('missions.creator.date')} value={form.scheduled_date} min={editingId ? undefined : isoDate(new Date())} onChange={(event) => setField('scheduled_date', event.target.value)} />
          <SimpleGrid cols={2}><TextInput label={t('missions.creator.titleDe')} value={form.title_de} onChange={(e) => setField('title_de', e.target.value)} /><TextInput label={t('missions.creator.titleEn')} value={form.title_en} onChange={(e) => setField('title_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.descriptionDe')} value={form.description_de} onChange={(e) => setField('description_de', e.target.value)} /><Textarea label={t('missions.creator.descriptionEn')} value={form.description_en} onChange={(e) => setField('description_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.questionDe')} value={form.question_de} onChange={(e) => setField('question_de', e.target.value)} /><Textarea label={t('missions.creator.questionEn')} value={form.question_en} onChange={(e) => setField('question_en', e.target.value)} /></SimpleGrid>
          {getMissionType(form.type).hasSharedFeedback && <SimpleGrid cols={2}><Textarea label={t('missions.creator.feedbackDe')} value={form.feedback_de} onChange={(e) => setField('feedback_de', e.target.value)} /><Textarea label={t('missions.creator.feedbackEn')} value={form.feedback_en} onChange={(e) => setField('feedback_en', e.target.value)} /></SimpleGrid>}
          {(() => { const Editor = getMissionType(form.type).Editor; return <Editor form={form} setForm={setForm} setOption={setOption} toggleCorrectOption={toggleCorrectOption} t={t} /> })()}
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
                  <Text fw={700}>
                    {mission[`title_${language}`]}
                  </Text>
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
          <Paper withBorder radius="md" p="md">
            <Stack gap="sm">
              <Badge variant="light">
                {language === 'en' ? 'English' : 'Deutsch'}
              </Badge>

              <Title order={4}>
                {preview[`title_${language}`]}
              </Title>

              <Text fz="sm" c="dimmed">
                {preview[`description_${language}`]}
              </Text>

              <Text fw={700}>
                {preview[`question_${language}`]}
              </Text>

              <MissionSolutionContent
                mission={preview}
                language={language}
                showSolution={showPreviewSolution}
              />

              {showPreviewSolution &&
                getMissionType(preview.type).hasSharedFeedback &&
                preview[`feedback_${language}`] && (
                  <Text fz="sm">
                    <Text span fw={700}>
                      {t('missions.review.feedback')}:{' '}
                    </Text>
                    {preview[`feedback_${language}`]}
                  </Text>
                )}
              </Stack>
            </Paper>  

          {preview.can_edit && !preview.has_attempts && <Button variant="light" leftSection={<IconEdit size={16} />} onClick={() => editMission(preview)}>{t('missions.creator.edit')}</Button>}
        </Stack>}
      </Modal>
    </Modal>
  )
}

function MissionReview({ enabled, onPublished }) {
  const { i18n, t } = useTranslation()
  const language = selectedLanguage(i18n)
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
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

  const generate = async () => {
    setGenerating(true)
    setError('')
    setMessage('')
    try {
      const data = await generateNextWeekMissions(generationWeek)
      setMessage(t('missions.review.generated', { count: data.created_count }))
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
      const data = action === 'approve' ? await approveAllReviewMissions(generationWeek) : await rejectAllReviewMissions(generationWeek)
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
                  <Text fw={700} fz="lg">
                    {mission[`title_${language}`]}
                  </Text>
                </Box>
                <Badge color="accent" variant="light">{mission.max_points} {t('missions.points')}</Badge>
              </Group>
              <Box>
                <Text fz="xs" fw={700} c="dimmed" tt="uppercase" mb={5}>
                  {language === 'en' ? 'English' : 'Deutsch'}
                </Text>

                <Text fz="sm" c="dimmed" mb="xs">
                  {mission[`description_${language}`]}
                </Text>

                <Text fw={700} fz="sm" mb="xs">
                  {mission[`question_${language}`]}
                </Text>

                <MissionSolutionContent mission={mission} language={language} />

                {getMissionType(mission.type).hasSharedFeedback && (
                  <Text fz="sm" mt="sm">
                    <Text span fw={700}>
                      {t('missions.review.feedback')}:{' '}
                    </Text>
                    {mission[`feedback_${language}`]}
                  </Text>
                )}
              </Box>
              
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

export default function Missions({ user }) {
  const { t, i18n } = useTranslation()
  const { progress } = useUserProgress(user)
  const [missions, setMissions] = useState([])
  const [learningInsights, setLearningInsights] = useState(null)
  const [canCreate, setCanCreate] = useState(false)
  const [activeMissionId, setActiveMissionId] = useState(null)
  const [testMissionId, setTestMissionId] = useState(null)
  const [creatorOpen, setCreatorOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const language = selectedLanguage(i18n)
  const activeMission = missions.find((mission) => mission.id === activeMissionId)
  const testMission = createTestMissions(language).find((mission) => mission.id === testMissionId)

  const load = useCallback((showLoading = true) => {
    if (showLoading) setLoading(true)
    getDailyMissions(language).then((data) => { setMissions(data.missions || []); setCanCreate(Boolean(data.can_create)); setError('') }).catch((nextError) => setError(nextError.message)).finally(() => setLoading(false))
  }, [language])

  useEffect(() => {
  let active = true

  Promise.all([
    getDailyMissions(language),
    getLearningInsights(),
  ])
    .then(([missionsData, insightsData]) => {
      if (!active) return


      setMissions(missionsData.missions || [])
      setCanCreate(Boolean(missionsData.can_create))
      setLearningInsights(insightsData.insights || null)
      setError('')
    })
    .catch((nextError) => {
      if (active) setError(nextError.message)
    })
    .finally(() => {
      if (active) setLoading(false)
    })

  return () => {
    active = false
  }
}, [language])

  if (testMission) return <MissionRunner mission={testMission} language={language} testMode onBack={() => setTestMissionId(null)} onCompleted={() => {}} />
  if (activeMission) return <MissionRunner mission={activeMission} language={language} onBack={() => { setActiveMissionId(null); load() }} onCompleted={(completed) => setMissions((current) => current.map((mission) => mission.id === completed.id ? completed : mission))} />

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
      {learningInsights && (
        <Paper withBorder radius="lg" p="xl" bg="white" mb="xl">
          <Stack gap="lg">
            <Group justify="space-between" align="flex-start">
              <Group align="flex-start" wrap="nowrap">
                <ThemeIcon size={46} radius="md" variant="light" color="brand">
                  <IconSparkles size={24} />
                </ThemeIcon>

                <Box>
                  <Text fw={700} fz="xl">
                    {language === 'en' ? 'Your Learning Profile' : 'Dein Lernprofil'}
                  </Text>

                  <Text c="dimmed" fz="sm">
                    {language === 'en'
                      ? 'Personalized insights based on your mission performance.'
                      : 'Personalisierte Einblicke basierend auf deinen Missionsergebnissen.'}
                  </Text>
                </Box>
              </Group>

              <Badge variant="light" color="brand" size="lg">
                {learningInsights.level}
              </Badge>
            </Group>

            <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
              <Box>
                <Text fz="xs" fw={700} c="dimmed" tt="uppercase">
                  {language === 'en' ? 'Strengths' : 'Stärken'}
                </Text>

                <Text mt={5}>
                  {learningInsights.strengths?.length
                    ? learningInsights.strengths.join(', ')
                    : language === 'en'
                      ? 'Complete more missions to identify your strengths.'
                      : 'Absolviere weitere Missionen, um deine Stärken zu erkennen.'}
                </Text>
              </Box>

              <Box>
                <Text fz="xs" fw={700} c="dimmed" tt="uppercase">
                  {language === 'en' ? 'Needs improvement' : 'Verbesserungspotenzial'}
                </Text>

                <Text mt={5}>
                  {learningInsights.weaknesses?.length
                    ? learningInsights.weaknesses.join(', ')
                    : language === 'en'
                      ? 'No improvement area identified yet.'
                      : 'Noch kein Verbesserungsbereich erkannt.'}
                </Text>
              </Box>

              <Box>
                <Text fz="xs" fw={700} c="dimmed" tt="uppercase">
                  {language === 'en' ? 'Recommended next step' : 'Empfohlener nächster Schritt'}
                </Text>

                <Text mt={5}>
                  {learningInsights.recommended_next_step?.recommendation
                    || (language === 'en'
                      ? 'Complete at least three missions to unlock a personalized recommendation.'
                      : 'Absolviere mindestens drei Missionen, um eine persönliche Empfehlung zu erhalten.')}
                </Text>
              </Box>
            </SimpleGrid>
          </Stack>
        </Paper>
      )}

      {loading ? <Text c="dimmed">{t('missions.loading')}</Text> : error ? <Alert color="red">{error}</Alert> : missions.length === 0 ? <Paper withBorder radius="lg" p={48} bg="white"><Stack align="center"><ThemeIcon size={58} radius="xl" variant="light"><IconCalendar size={28} /></ThemeIcon><Text fw={700}>{t('missions.emptyTitle')}</Text><Text c="dimmed" ta="center">{t('missions.emptyText')}</Text></Stack></Paper> : <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">{missions.map((mission) => <MissionCard key={mission.id} mission={mission} onOpen={(selected) => setActiveMissionId(selected.id)} />)}</SimpleGrid>}
      <MissionReview enabled={canCreate} onPublished={() => load(false)} />
      <Creator opened={creatorOpen} onClose={() => setCreatorOpen(false)} onCreated={load} />
      {user?.role === 'admin' && <MissionTestArea language={language} onSelect={(selected) => setTestMissionId(selected.id)} />}
    </Box>
  )
}
