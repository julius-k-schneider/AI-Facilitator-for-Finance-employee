import { useEffect, useRef, useState } from 'react'
import { Alert, Badge, Box, Button, Group, Paper, Stack, Text, Textarea, Title } from '@mantine/core'
import { IconMessageCircle, IconSend, IconSparkles } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { sendAgentMessage } from '../services/agentService'

function cleanText(text) {
  return String(text || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^>\s?/gm, '')
    .replace(/^\s*-{3,}\s*$/gm, '')
    .replace(/^\|(.+)\|$/gm, (_match, row) => row.split('|').map((cell) => cell.trim()).filter(Boolean).join(' | '))
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export default function DeinAgent() {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  const send = async (text = draft) => {
    const content = text.trim()
    if (!content || sending) return
    const nextMessages = [...messages, { role: 'user', content }]
    setMessages(nextMessages)
    setDraft('')
    setSending(true)
    setError('')
    try {
      const reply = await sendAgentMessage(nextMessages, language)
      setMessages((current) => [...current, { role: 'assistant', content: reply }])
    } catch (nextError) {
      setError(nextError.message)
      setMessages(messages)
      setDraft(content)
    } finally {
      setSending(false)
    }
  }

  const starters = t('agent.starters', { returnObjects: true })

  return <Box px={{ base: 'md', md: 32 }} py={{ base: 10, md: 12 }} w="100%" style={{ height: 'calc(100vh - 65px)', boxSizing: 'border-box', display: 'flex', overflow: 'hidden' }}>
    <Stack gap="sm" maw={1120} mx="auto" w="100%" style={{ flex: 1, minHeight: 0 }}>
      <Group justify="space-between" align="center">
        <Box>
          <Badge variant="light" color="brand" mb={4}>{t('agent.badge')}</Badge>
          <Title order={1} fz={{ base: 22, md: 28 }}>{t('agent.title')}</Title>
        </Box>
      </Group>

      <Paper withBorder radius="lg" bg="white" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Stack gap="sm" p={{ base: 'md', md: 'xl' }} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
          {messages.length === 0 && <Stack gap="md" align="center" justify="center" mih={260}>
            <IconSparkles size={34} color="var(--mantine-color-brand-6)" />
            <Box ta="center" maw={620}>
              <Text fw={700} fz="lg">{t('agent.emptyTitle')}</Text>
              <Text c="dimmed" fz="sm" mt={4}>{t('agent.emptyText')}</Text>
            </Box>
            <Group gap="xs" justify="center">
              {Array.isArray(starters) && starters.map((starter) => <Button key={starter} variant="light" color="gray" size="xs" onClick={() => send(starter)} disabled={sending}>{starter}</Button>)}
            </Group>
          </Stack>}

          {messages.map((item, index) => <Group key={index} justify={item.role === 'user' ? 'flex-end' : 'flex-start'} align="flex-start">
            <Paper radius="md" p="md" maw={item.role === 'user' ? '78%' : '92%'} bg={item.role === 'user' ? 'brand.0' : 'gray.0'} style={{ border: item.role === 'assistant' ? '1px solid var(--line)' : undefined }}>
              <Text fz="xs" fw={700} mb={3}>{item.role === 'user' ? t('agent.you') : t('agent.assistant')}</Text>
              <Text fz="sm" lh={1.6} style={{ whiteSpace: 'pre-wrap' }}>{cleanText(item.content)}</Text>
            </Paper>
          </Group>)}
          {sending && <Group justify="flex-start"><Paper radius="md" p="sm" bg="gray.0"><Text fz="xs" fw={700}>{t('agent.assistant')}</Text><Text c="dimmed" fz="sm">...</Text></Paper></Group>}
          <span ref={endRef} />
        </Stack>

        {error && <Alert color="red" radius={0}>{error}</Alert>}
        <Box p={{ base: 'md', md: 'lg' }} style={{ borderTop: '1px solid var(--line)' }}>
          <Group align="flex-end">
            <Textarea
              style={{ flex: 1 }}
              minRows={2}
              maxRows={6}
              autosize
              placeholder={t('agent.placeholder')}
              value={draft}
              disabled={sending}
              onChange={(event) => setDraft(event.currentTarget.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) send()
              }}
            />
            <Button leftSection={<IconSend size={16} />} loading={sending} disabled={!draft.trim()} onClick={() => send()}>{t('agent.send')}</Button>
          </Group>
          <Group gap={6} mt="xs"><IconMessageCircle size={14} /><Text c="dimmed" fz="xs">{t('agent.note')}</Text></Group>
        </Box>
      </Paper>
    </Stack>
  </Box>
}
