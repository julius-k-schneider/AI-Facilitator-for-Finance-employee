import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Anchor,
  Badge,
  Box,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Textarea,
  TextInput,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconCalendarClock,
  IconEdit,
  IconExternalLink,
  IconNews,
  IconPlayerPlay,
  IconSearch,
  IconTrash,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'
import {
  deleteResearchItem,
  getLatestResearchRun,
  getResearch,
  startResearchRun,
  updateResearchItem,
  updateResearchSchedule,
} from '../services/researchService'

const ACTIVE_RUN_STATUSES = new Set(['queued', 'running'])

function localDate(value, locale, withTime = false) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(locale, withTime
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' })
}

function toLocalInput(value) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function editForm(item) {
  return {
    title: item.title || '',
    source_name: item.source_name || '',
    source_url: item.source_url || '',
    summary_de: item.summary_de || '',
    summary_en: item.summary_en || '',
    tags: (item.tags || []).join(', '),
    mission_hooks: (item.mission_hooks || []).join('\n'),
    safe_facts: (item.safe_facts || []).map((fact) => (
      `${fact.fact || fact} | ${fact.evidence_excerpt || fact.fact || fact}`
    )).join('\n'),
    relevance_score: item.relevance_score || 0,
    confidence: item.confidence || 'medium',
    valid_until: toLocalInput(item.valid_until),
    eligible: item.eligible === true,
  }
}

function StatCard({ value, label, color = 'brand' }) {
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Text fz={28} fw={800} c={`${color}.7`}>{value}</Text>
      <Text fz="sm" c="dimmed">{label}</Text>
    </Paper>
  )
}

export default function Research() {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  const locale = i18n.resolvedLanguage || language
  const [items, setItems] = useState([])
  const [stats, setStats] = useState({ total: 0, current: 0, expired: 0, inactive: 0 })
  const [schedule, setSchedule] = useState(null)
  const [latestRun, setLatestRun] = useState(null)
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [savingSchedule, setSavingSchedule] = useState(false)
  const [savingItem, setSavingItem] = useState(false)
  const [message, setMessage] = useState(null)
  const [editTarget, setEditTarget] = useState(null)
  const [form, setForm] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)

  const loadData = useCallback(async () => {
    try {
      const data = await getResearch({
        ...(query.trim() ? { q: query.trim() } : {}),
        ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
      })
      setItems(data.items || [])
      setStats(data.stats || {})
      setSchedule(data.schedule || null)
      setLatestRun(data.latest_run || null)
      setRunning(ACTIVE_RUN_STATUSES.has(data.latest_run?.status))
    } catch (error) {
      setMessage({ color: 'red', text: error.message || t('research.errors.load') })
    } finally {
      setLoading(false)
    }
  }, [query, statusFilter, t])

  useEffect(() => {
    const timer = window.setTimeout(loadData, query ? 250 : 0)
    return () => window.clearTimeout(timer)
  }, [loadData, query])

  useEffect(() => {
    if (!ACTIVE_RUN_STATUSES.has(latestRun?.status)) return undefined
    let active = true
    const poll = async () => {
      try {
        const data = await getLatestResearchRun()
        if (!active) return
        const run = data.research_run
        setLatestRun(run)
        setRunning(ACTIVE_RUN_STATUSES.has(run?.status))
        if (run && !ACTIVE_RUN_STATUSES.has(run.status)) {
          await loadData()
          if (!active) return
          setMessage({
            color: run.status === 'completed' ? 'green' : 'red',
            text: run.status === 'completed'
              ? t('research.messages.completed', { count: run.result?.stored_count || 0 })
              : (run.error_message || t('research.errors.run')),
          })
        }
      } catch (error) {
        if (active) setMessage({ color: 'red', text: error.message || t('research.errors.load') })
      }
    }
    const timer = window.setInterval(poll, 2000)
    return () => { active = false; window.clearInterval(timer) }
  }, [latestRun?.id, latestRun?.status, loadData, t])

  const weekdayOptions = useMemo(() => Array.from({ length: 7 }, (_, weekday) => ({
    value: String(weekday),
    label: t(`research.schedule.weekdays.${weekday}`),
  })), [t])

  const runResearch = async () => {
    setRunning(true)
    setMessage(null)
    try {
      const data = await startResearchRun()
      setLatestRun(data.research_run)
      setMessage({ color: 'blue', text: t('research.messages.started') })
    } catch (error) {
      setRunning(false)
      setMessage({ color: 'red', text: error.message || t('research.errors.run') })
    }
  }

  const saveSchedule = async () => {
    if (!schedule) return
    setSavingSchedule(true)
    try {
      const data = await updateResearchSchedule(schedule)
      setSchedule(data.schedule)
      setMessage({ color: 'green', text: t('research.messages.scheduleSaved') })
    } catch (error) {
      setMessage({ color: 'red', text: error.message || t('research.errors.schedule') })
    } finally {
      setSavingSchedule(false)
    }
  }

  const openEdit = (item) => {
    setEditTarget(item)
    setForm(editForm(item))
  }

  const saveItem = async () => {
    if (!editTarget || !form) return
    setSavingItem(true)
    try {
      const facts = form.safe_facts.split('\n').map((line) => {
        const [fact, ...evidence] = line.split('|')
        return { fact: fact.trim(), evidence_excerpt: (evidence.join('|').trim() || fact.trim()) }
      }).filter((fact) => fact.fact)
      await updateResearchItem(editTarget.id, {
        title: form.title,
        source_name: form.source_name,
        source_url: form.source_url,
        summary_de: form.summary_de,
        summary_en: form.summary_en,
        tags: form.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
        mission_hooks: form.mission_hooks.split('\n').map((hook) => hook.trim()).filter(Boolean),
        safe_facts: facts,
        relevance_score: form.relevance_score,
        confidence: form.confidence,
        valid_until: new Date(form.valid_until).toISOString(),
        eligible: form.eligible,
      })
      setEditTarget(null)
      setForm(null)
      setMessage({ color: 'green', text: t('research.messages.updated') })
      await loadData()
    } catch (error) {
      setMessage({ color: 'red', text: error.message || t('research.errors.update') })
    } finally {
      setSavingItem(false)
    }
  }

  const removeItem = async () => {
    if (!deleteTarget) return
    try {
      await deleteResearchItem(deleteTarget.id)
      setDeleteTarget(null)
      setMessage({ color: 'green', text: t('research.messages.deleted') })
      await loadData()
    } catch (error) {
      setMessage({ color: 'red', text: error.message || t('research.errors.delete') })
    }
  }

  return (
    <PageShell title={t('research.title')} description={t('research.description')}>
      <Stack gap="xl">
        {message && <Alert color={message.color} withCloseButton onClose={() => setMessage(null)}>{message.text}</Alert>}

        <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
          <Group justify="space-between" align="flex-start">
            <Group align="flex-start" wrap="nowrap">
              <ThemeIcon size={46} radius="md" variant="light" color="brand"><IconNews size={24} /></ThemeIcon>
              <Box>
                <Title order={2} fz="xl">{t('research.run.title')}</Title>
                <Text c="dimmed" fz="sm" mt={3}>{t('research.run.description')}</Text>
                {latestRun && <Group gap="xs" mt="sm">
                  <Badge color={latestRun.status === 'failed' ? 'red' : latestRun.status === 'completed' ? 'green' : 'blue'}>
                    {t(`research.run.status.${latestRun.status}`)}
                  </Badge>
                  <Text fz="xs" c="dimmed">{localDate(latestRun.created_at, locale, true)}</Text>
                </Group>}
              </Box>
            </Group>
            <Button leftSection={running ? <Loader size={16} color="white" /> : <IconPlayerPlay size={17} />} disabled={running} onClick={runResearch}>
              {running ? t('research.run.running') : t('research.run.button')}
            </Button>
          </Group>
        </Paper>

        <SimpleGrid cols={{ base: 2, md: 4 }} spacing="md">
          <StatCard value={stats.total || 0} label={t('research.stats.total')} />
          <StatCard value={stats.current || 0} label={t('research.stats.current')} color="green" />
          <StatCard value={stats.expired || 0} label={t('research.stats.expired')} color="orange" />
          <StatCard value={stats.inactive || 0} label={t('research.stats.inactive')} color="gray" />
        </SimpleGrid>

        {schedule && <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
          <Group mb="lg" align="flex-start" wrap="nowrap">
            <ThemeIcon size={42} radius="md" variant="light" color="secondary"><IconCalendarClock size={22} /></ThemeIcon>
            <Box><Title order={2} fz="lg">{t('research.schedule.title')}</Title><Text c="dimmed" fz="sm">{t('research.schedule.description')}</Text></Box>
          </Group>
          <Group align="flex-end" gap="md">
            <Switch
              label={t('research.schedule.enabled')}
              checked={schedule.enabled}
              onChange={(event) => setSchedule((current) => ({ ...current, enabled: event.currentTarget.checked }))}
              mb={8}
            />
            <Select
              label={t('research.schedule.weekday')}
              data={weekdayOptions}
              value={String(schedule.weekday)}
              onChange={(value) => value !== null && setSchedule((current) => ({ ...current, weekday: Number(value) }))}
              disabled={!schedule.enabled}
              w={200}
            />
            <TextInput
              type="time"
              label={t('research.schedule.time')}
              value={schedule.run_time}
              onChange={(event) => setSchedule((current) => ({ ...current, run_time: event.currentTarget.value }))}
              disabled={!schedule.enabled}
              w={150}
            />
            <Button variant="light" loading={savingSchedule} onClick={saveSchedule}>{t('research.schedule.save')}</Button>
          </Group>
          <Text fz="xs" c="dimmed" mt="sm">{t('research.schedule.timezone', { timezone: schedule.timezone })}</Text>
        </Paper>}

        <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
          <Group justify="space-between" mb="lg" align="flex-end">
            <Box><Title order={2} fz="xl">{t('research.library.title')}</Title><Text c="dimmed" fz="sm">{t('research.library.description')}</Text></Box>
            <Group>
              <TextInput leftSection={<IconSearch size={16} />} placeholder={t('research.library.search')} value={query} onChange={(event) => setQuery(event.currentTarget.value)} />
              <Select
                value={statusFilter}
                onChange={(value) => setStatusFilter(value || 'all')}
                data={['all', 'current', 'expired', 'inactive'].map((value) => ({ value, label: t(`research.library.filters.${value}`) }))}
                w={170}
              />
            </Group>
          </Group>
          {loading ? <Group justify="center" py="xl"><Loader size="sm" /><Text c="dimmed">{t('research.library.loading')}</Text></Group> : items.length === 0 ? (
            <Stack align="center" py={40} gap="xs"><ThemeIcon size={58} radius="xl" variant="light"><IconNews size={28} /></ThemeIcon><Text fw={700}>{t('research.library.empty')}</Text><Text c="dimmed" ta="center">{t('research.library.emptyText')}</Text></Stack>
          ) : <Stack gap="md">{items.map((item) => {
            const expired = new Date(item.valid_until) < new Date()
            return <Paper key={item.id} withBorder radius="md" p="lg" bg="gray.0">
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Box style={{ flex: 1, minWidth: 0 }}>
                  <Group gap="xs" mb={6}>
                    <Badge color={!item.eligible ? 'gray' : expired ? 'orange' : 'green'} variant="light">
                      {!item.eligible ? t('research.library.inactive') : expired ? t('research.library.expired') : t('research.library.current')}
                    </Badge>
                    <Badge color={item.confidence === 'high' ? 'brand' : item.confidence === 'medium' ? 'blue' : 'gray'} variant="outline">
                      {t(`research.confidence.${item.confidence}`)}
                    </Badge>
                    <Text fz="xs" c="dimmed">{t('research.library.score', { score: item.relevance_score })}</Text>
                  </Group>
                  <Title order={3} fz="lg">{item.title}</Title>
                  <Group gap={6} mt={4}>
                    <Text fz="sm" fw={600}>{item.source_name}</Text>
                    <Anchor href={item.source_url} target="_blank" rel="noreferrer" fz="sm"><IconExternalLink size={14} /></Anchor>
                    <Text fz="xs" c="dimmed">{t('research.library.published', { date: localDate(item.published_at, locale) })}</Text>
                    <Text fz="xs" c="dimmed">{t('research.library.validUntil', { date: localDate(item.valid_until, locale) })}</Text>
                  </Group>
                  <Text fz="sm" mt="md" style={{ whiteSpace: 'pre-wrap' }}>{item[`summary_${language}`] || item.summary_en || item.summary_de}</Text>
                  <Group gap="xs" mt="md">{(item.tags || []).map((tag) => <Badge key={tag} color="secondary" variant="light">{tag}</Badge>)}</Group>
                </Box>
                <Group gap="xs">
                  <Button variant="subtle" size="xs" leftSection={<IconEdit size={15} />} onClick={() => openEdit(item)}>{t('research.actions.edit')}</Button>
                  <Button color="red" variant="subtle" size="xs" leftSection={<IconTrash size={15} />} onClick={() => setDeleteTarget(item)}>{t('research.actions.delete')}</Button>
                </Group>
              </Group>
            </Paper>
          })}</Stack>}
        </Paper>
      </Stack>

      <Modal opened={Boolean(editTarget)} onClose={() => { setEditTarget(null); setForm(null) }} title={t('research.edit.title')} size="xl" centered>
        {form && <Stack gap="md">
          <TextInput label={t('research.edit.itemTitle')} value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.currentTarget.value }))} />
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput label={t('research.edit.sourceName')} value={form.source_name} onChange={(event) => setForm((current) => ({ ...current, source_name: event.currentTarget.value }))} />
            <TextInput label={t('research.edit.sourceUrl')} value={form.source_url} onChange={(event) => setForm((current) => ({ ...current, source_url: event.currentTarget.value }))} />
          </SimpleGrid>
          <Textarea label={t('research.edit.summaryDe')} minRows={3} value={form.summary_de} onChange={(event) => setForm((current) => ({ ...current, summary_de: event.currentTarget.value }))} />
          <Textarea label={t('research.edit.summaryEn')} minRows={3} value={form.summary_en} onChange={(event) => setForm((current) => ({ ...current, summary_en: event.currentTarget.value }))} />
          <TextInput label={t('research.edit.tags')} description={t('research.edit.tagsHint')} value={form.tags} onChange={(event) => setForm((current) => ({ ...current, tags: event.currentTarget.value }))} />
          <Textarea label={t('research.edit.facts')} description={t('research.edit.factsHint')} minRows={4} value={form.safe_facts} onChange={(event) => setForm((current) => ({ ...current, safe_facts: event.currentTarget.value }))} />
          <Textarea label={t('research.edit.hooks')} description={t('research.edit.hooksHint')} minRows={3} value={form.mission_hooks} onChange={(event) => setForm((current) => ({ ...current, mission_hooks: event.currentTarget.value }))} />
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <NumberInput label={t('research.edit.score')} min={0} max={100} value={form.relevance_score} onChange={(value) => setForm((current) => ({ ...current, relevance_score: value }))} />
            <Select label={t('research.edit.confidence')} value={form.confidence} onChange={(value) => setForm((current) => ({ ...current, confidence: value }))} data={['low', 'medium', 'high'].map((value) => ({ value, label: t(`research.confidence.${value}`) }))} />
            <TextInput type="datetime-local" label={t('research.edit.validUntil')} value={form.valid_until} onChange={(event) => setForm((current) => ({ ...current, valid_until: event.currentTarget.value }))} />
          </SimpleGrid>
          <Switch label={t('research.edit.eligible')} checked={form.eligible} onChange={(event) => setForm((current) => ({ ...current, eligible: event.currentTarget.checked }))} />
          <Group justify="flex-end"><Button variant="subtle" onClick={() => { setEditTarget(null); setForm(null) }}>{t('research.actions.cancel')}</Button><Button loading={savingItem} onClick={saveItem}>{t('research.actions.save')}</Button></Group>
        </Stack>}
      </Modal>

      <Modal opened={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} title={t('research.delete.title')} centered>
        <Stack><Text>{t('research.delete.text', { title: deleteTarget?.title })}</Text><Alert color="orange">{t('research.delete.warning')}</Alert><Group justify="flex-end"><Button variant="subtle" onClick={() => setDeleteTarget(null)}>{t('research.actions.cancel')}</Button><Button color="red" onClick={removeItem}>{t('research.actions.delete')}</Button></Group></Stack>
      </Modal>
    </PageShell>
  )
}
