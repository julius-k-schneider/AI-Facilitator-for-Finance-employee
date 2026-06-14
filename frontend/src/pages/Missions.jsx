import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Box, Button, Group, Modal, NumberInput, Paper, Radio, Select,
  SimpleGrid, Stack, Text, Textarea, TextInput, ThemeIcon, Title,
} from '@mantine/core'
import {
  IconArrowLeft, IconArrowRight, IconCalendar, IconCheck, IconChevronLeft,
  IconChevronRight, IconCircleCheck, IconEye, IconPlus, IconTargetArrow, IconTrash, IconTrophy,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { createMission, deleteMission, getDailyMissions, getMissionSchedule, submitMission } from '../services/missionService'
import './Missions.css'

const createEmptyForm = () => ({
  type: 'single_choice', scheduled_date: '', title_de: '', title_en: '',
  description_de: '', description_en: '', question_de: '', question_en: '',
  max_points: 100, correct_index: 0,
  options: [{ de: '', en: '' }, { de: '', en: '' }],
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
          <Badge variant="light" color="secondary">{t('missions.types.singleChoice')}</Badge>
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
  const [answer, setAnswer] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const data = await submitMission(mission.id, answer)
      setResult(data.result)
      onCompleted(data.mission)
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={900}>
      <Button variant="subtle" color="secondary" leftSection={<IconArrowLeft size={17} />} onClick={onBack} mb="lg">{t('missions.back')}</Button>
      <Paper withBorder radius="lg" p={{ base: 'xl', md: 40 }} bg="white">
        <Stack gap="xl">
          <Box>
            <Badge variant="light" color="brand" mb="sm">{t('missions.types.singleChoice')}</Badge>
            <Title order={1} fz={{ base: 25, md: 32 }}>{mission.title}</Title>
            <Text c="dimmed" mt={6}>{mission.description}</Text>
          </Box>
          <Text fw={700} fz="lg">{mission.content.question}</Text>
          <Radio.Group value={answer === null ? '' : String(answer)} onChange={(value) => setAnswer(Number(value))}>
            <Stack gap="sm">
              {mission.content.options.map((option, index) => (
                <Paper key={`${index}-${option}`} withBorder radius="md" p="md">
                  <Radio value={String(index)} label={option} disabled={Boolean(result)} />
                </Paper>
              ))}
            </Stack>
          </Radio.Group>
          {error && <Alert color="red">{error}</Alert>}
          {result && <Alert color={result.correct ? 'green' : 'orange'} icon={result.correct ? <IconTrophy size={20} /> : undefined}>
            {result.correct ? t('missions.result.correct', { points: result.score }) : t('missions.result.wrong')}
          </Alert>}
          {!result && <Button color="brand" disabled={answer === null} loading={submitting} onClick={submit}>{t('missions.submit')}</Button>}
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
  const setOption = (index, language, value) => setForm((current) => ({ ...current, options: current.options.map((option, optionIndex) => optionIndex === index ? { ...option, [language]: value } : option) }))
  const missionsForDate = form.scheduled_date ? scheduledMissions[form.scheduled_date] || [] : []

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
      await createMission(form)
      setForm(createEmptyForm())
      loadSchedule()
      onCreated()
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal opened={opened} onClose={onClose} title={t('missions.creator.title')} size="xl" centered>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
        <Stack gap="md">
          <Select label={t('missions.creator.type')} value={form.type} data={[{ value: 'single_choice', label: t('missions.types.singleChoice') }]} disabled />
          <TextInput type="date" label={t('missions.creator.date')} value={form.scheduled_date} min={isoDate(new Date())} onChange={(event) => setField('scheduled_date', event.target.value)} />
          <SimpleGrid cols={2}><TextInput label={t('missions.creator.titleDe')} value={form.title_de} onChange={(e) => setField('title_de', e.target.value)} /><TextInput label={t('missions.creator.titleEn')} value={form.title_en} onChange={(e) => setField('title_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.descriptionDe')} value={form.description_de} onChange={(e) => setField('description_de', e.target.value)} /><Textarea label={t('missions.creator.descriptionEn')} value={form.description_en} onChange={(e) => setField('description_en', e.target.value)} /></SimpleGrid>
          <SimpleGrid cols={2}><Textarea label={t('missions.creator.questionDe')} value={form.question_de} onChange={(e) => setField('question_de', e.target.value)} /><Textarea label={t('missions.creator.questionEn')} value={form.question_en} onChange={(e) => setField('question_en', e.target.value)} /></SimpleGrid>
          <Stack gap="sm">
            <Group justify="space-between"><Text fw={700}>{t('missions.creator.answers')}</Text><Button size="xs" variant="light" leftSection={<IconPlus size={14} />} onClick={() => setForm((current) => ({ ...current, options: [...current.options, { de: '', en: '' }] }))}>{t('missions.creator.addAnswer')}</Button></Group>
            {form.options.map((option, index) => <Paper key={index} withBorder radius="md" p="sm"><Group align="flex-end" wrap="nowrap"><Radio checked={form.correct_index === index} onChange={() => setField('correct_index', index)} /><TextInput label={`DE ${index + 1}`} value={option.de} onChange={(e) => setOption(index, 'de', e.target.value)} style={{ flex: 1 }} /><TextInput label={`EN ${index + 1}`} value={option.en} onChange={(e) => setOption(index, 'en', e.target.value)} style={{ flex: 1 }} /></Group></Paper>)}
          </Stack>
          <NumberInput label={t('missions.creator.points')} min={1} max={1000} value={form.max_points} onChange={(value) => setField('max_points', value)} />
          {error && <Alert color="red">{error}</Alert>}
          <Button color="brand" loading={saving} onClick={save}>{t('missions.creator.save')}</Button>
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
                  <Button variant="subtle" size="compact-sm" aria-label={t('missions.creator.view')} onClick={() => setPreview(mission)}><IconEye size={17} /></Button>
                  {mission.can_delete && <Button color="red" variant="subtle" size="compact-sm" loading={deletingId === mission.id} disabled={mission.has_attempts} aria-label={t('missions.creator.delete')} onClick={() => removeMission(mission)}><IconTrash size={17} /></Button>}
                </Group>
              </Group>
              {mission.has_attempts && <Text fz="xs" c="orange" mt={6}>{t('missions.creator.deleteBlocked')}</Text>}
            </Paper>)}
          </Stack>}
        </Stack>
      </SimpleGrid>
      <Modal opened={Boolean(preview)} onClose={() => setPreview(null)} title={t('missions.creator.previewTitle')} size="lg" centered>
        {preview && <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
          {[['de', 'Deutsch'], ['en', 'English']].map(([language, label]) => <Paper key={language} withBorder radius="md" p="md">
            <Stack gap="sm">
              <Badge variant="light">{label}</Badge>
              <Title order={4}>{preview[`title_${language}`]}</Title>
              <Text fz="sm" c="dimmed">{preview[`description_${language}`]}</Text>
              <Text fw={700}>{preview[`question_${language}`]}</Text>
              {preview.options.map((option, index) => <Text key={index} fz="sm" c={index === preview.correct_index ? 'green' : undefined} fw={index === preview.correct_index ? 700 : 400}>{index + 1}. {option[language]}{index === preview.correct_index ? ` (${t('missions.creator.correctAnswer')})` : ''}</Text>)}
            </Stack>
          </Paper>)}
        </SimpleGrid>}
      </Modal>
    </Modal>
  )
}

export default function Missions() {
  const { t, i18n } = useTranslation()
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
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      <Group justify="space-between" align="flex-start" mb="xl">
        <Box><Badge variant="light" color="brand" mb="sm">{t('missions.badge')}</Badge><Title order={1} fz={{ base: 28, md: 34 }}>{t('missions.title')}</Title><Text c="dimmed" fz="lg" mt={4}>{t('missions.description')}</Text></Box>
        {canCreate && <Button color="brand" leftSection={<IconPlus size={18} />} onClick={() => setCreatorOpen(true)}>{t('missions.creator.button')}</Button>}
      </Group>
      {loading ? <Text c="dimmed">{t('missions.loading')}</Text> : error ? <Alert color="red">{error}</Alert> : missions.length === 0 ? <Paper withBorder radius="lg" p={48} bg="white"><Stack align="center"><ThemeIcon size={58} radius="xl" variant="light"><IconCalendar size={28} /></ThemeIcon><Text fw={700}>{t('missions.emptyTitle')}</Text><Text c="dimmed" ta="center">{t('missions.emptyText')}</Text></Stack></Paper> : <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">{missions.map((mission) => <MissionCard key={mission.id} mission={mission} onOpen={setActiveMission} />)}</SimpleGrid>}
      <Creator opened={creatorOpen} onClose={() => setCreatorOpen(false)} onCreated={load} />
    </Box>
  )
}
