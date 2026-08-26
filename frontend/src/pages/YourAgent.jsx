import { useEffect, useRef, useState } from 'react'
import {
  ActionIcon, Alert, Badge, Box, Button, Drawer, Group, Loader, Paper, ScrollArea,
  Stack, Text, Textarea, Title, Tooltip,
} from '@mantine/core'
import { IconList, IconMessageCircle, IconPlus, IconSend, IconSparkles, IconTrash } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import ConfirmModal from '../components/ConfirmModal'
import { notifyError, notifySuccess } from '../services/notify'
import { createAgentChat, deleteAgentChat, getAgentChat, getAgentChats, sendAgentChatMessage } from '../services/agentService'
import './YourAgent.css'

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

function ChatList({ chats, activeChatId, loading, onOpen, onRequestDelete }) {
  const { t } = useTranslation()
  return (
    <>
      <Text fz="xs" fw={700} c="dimmed" px="xs" mb="xs">{t('agent.previousChats')}</Text>
      <ScrollArea style={{ flex: 1 }}>
        <Stack gap={4}>
          {chats.map((chat) => (
            <Group key={chat.id} gap={4} wrap="nowrap">
              <Button
                variant={chat.id === activeChatId ? 'light' : 'subtle'}
                color={chat.id === activeChatId ? 'brand' : 'gray'}
                justify="flex-start"
                fullWidth
                onClick={() => onOpen(chat.id)}
                styles={{ label: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }}
              >
                {chat.title || t('agent.untitled')}
              </Button>
              <Tooltip label={t('agent.deleteChat')}>
                <ActionIcon variant="subtle" color="red" onClick={() => onRequestDelete(chat)} aria-label={t('agent.deleteChat')}>
                  <IconTrash size={16} />
                </ActionIcon>
              </Tooltip>
            </Group>
          ))}
          {!chats.length && !loading && <Text c="dimmed" fz="sm" px="xs">{t('agent.noChats')}</Text>}
        </Stack>
      </ScrollArea>
    </>
  )
}

export default function YourAgent() {
  const { t, i18n } = useTranslation()
  const language = (i18n.resolvedLanguage || i18n.language || 'de').split('-')[0] === 'en' ? 'en' : 'de'
  const [chats, setChats] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [listOpen, setListOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    let active = true
    getAgentChats()
      .then(async (items) => {
        if (!active) return
        setChats(items)
        if (items[0]) {
          setActiveChatId(items[0].id)
          const chat = await getAgentChat(items[0].id)
          if (active) setMessages(chat.messages || [])
        }
      })
      .catch((nextError) => active && setError(nextError.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  const refreshChat = (chat) => {
    setActiveChatId(chat.id)
    setMessages(chat.messages || [])
    setChats((current) => {
      const rest = current.filter((item) => item.id !== chat.id)
      return [{ id: chat.id, title: chat.title, updated_at: chat.updated_at, created_at: chat.created_at }, ...rest]
    })
  }

  const startChat = async () => {
    setError('')
    setCreating(true)
    try {
      const chat = await createAgentChat()
      refreshChat(chat)
      setListOpen(false)
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setCreating(false)
    }
  }

  const openChat = async (chatId) => {
    setListOpen(false)
    if (chatId === activeChatId) return
    setError('')
    setLoading(true)
    try {
      const chat = await getAgentChat(chatId)
      setActiveChatId(chat.id)
      setMessages(chat.messages || [])
    } catch (nextError) {
      setError(nextError.message)
    } finally {
      setLoading(false)
    }
  }

  const removeChat = async () => {
    if (!deleteTarget) return
    const chatId = deleteTarget.id
    setDeleting(true)
    setError('')
    try {
      await deleteAgentChat(chatId)
      const nextChats = chats.filter((item) => item.id !== chatId)
      setChats(nextChats)
      if (chatId === activeChatId) {
        setActiveChatId(nextChats[0]?.id || null)
        if (nextChats[0]) {
          const chat = await getAgentChat(nextChats[0].id)
          setMessages(chat.messages || [])
        } else {
          setMessages([])
        }
      }
      notifySuccess(t('agent.deleteSuccess'))
      setDeleteTarget(null)
    } catch (nextError) {
      notifyError(nextError.message)
    } finally {
      setDeleting(false)
    }
  }

  const send = async (text = draft) => {
    const content = text.trim()
    if (!content || sending) return
    let chatId = activeChatId
    if (!chatId) {
      try {
        const chat = await createAgentChat()
        chatId = chat.id
        refreshChat(chat)
      } catch (nextError) {
        setError(nextError.message)
        return
      }
    }
    const nextMessages = [...messages, { role: 'user', content }]
    setMessages(nextMessages)
    setDraft('')
    setSending(true)
    setError('')
    try {
      const chat = await sendAgentChatMessage(chatId, content, language)
      refreshChat(chat)
    } catch (nextError) {
      setError(nextError.message)
      setMessages(messages)
      setDraft(content)
    } finally {
      setSending(false)
    }
  }

  const starters = t('agent.starters', { returnObjects: true })
  const listProps = { chats, activeChatId, loading, onOpen: openChat, onRequestDelete: setDeleteTarget }

  return <Box px={{ base: 'md', md: 32 }} py={{ base: 10, md: 12 }} w="100%" className="agent-page">
    <Stack gap="sm" maw={1120} mx="auto" w="100%" style={{ flex: 1, minHeight: 0 }}>
      <Group justify="space-between" align="center" wrap="wrap">
        <Box style={{ minWidth: 0 }}>
          <Badge variant="light" color="brand" mb={4}>{t('agent.badge')}</Badge>
          <Title order={2} fz={{ base: 22, md: 28 }}>{t('agent.title')}</Title>
        </Box>
        <Group gap="xs" wrap="nowrap">
          <Button hiddenFrom="sm" variant="default" leftSection={<IconList size={16} />} onClick={() => setListOpen(true)}>
            {t('agent.chats')}
          </Button>
          <Button leftSection={<IconPlus size={16} />} variant="light" onClick={startChat} loading={creating}>{t('agent.newChat')}</Button>
        </Group>
      </Group>

      <Paper withBorder radius="lg" bg="white" className="agent-panel">
        <Box p="sm" className="agent-chat-list">
          <ChatList {...listProps} />
        </Box>

        <Box style={{ minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <Stack gap="sm" p={{ base: 'md', md: 'xl' }} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
          {loading && <Group justify="center" mt="xl"><Loader size="sm" /><Text c="dimmed" fz="sm">{t('agent.loading')}</Text></Group>}
          {!loading && messages.length === 0 && <Stack gap="md" align="center" justify="center" mih={260}>
            <IconSparkles size={34} color="var(--mantine-color-brand-6)" />
            <Box ta="center" maw={620}>
              <Text fw={700} fz="lg">{t('agent.emptyTitle')}</Text>
              <Text c="dimmed" fz="sm" mt={4}>{t('agent.emptyText')}</Text>
            </Box>
            {/* Long starters have to wrap; as single-line buttons they were wider
                than a phone screen and spilled out of the card on both sides. */}
            <Group gap="xs" justify="center" w="100%">
              {Array.isArray(starters) && starters.map((starter) => (
                <Button
                  key={starter}
                  variant="light"
                  color="gray"
                  size="xs"
                  maw="100%"
                  h="auto"
                  py={8}
                  styles={{ label: { whiteSpace: 'normal', textAlign: 'center', lineHeight: 1.4 } }}
                  onClick={() => send(starter)}
                  disabled={sending}
                >
                  {starter}
                </Button>
              ))}
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
          <Group align="flex-end" wrap="nowrap">
            <Textarea
              style={{ flex: 1, minWidth: 0 }}
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
            <Button leftSection={<IconSend size={16} />} loading={sending} disabled={!draft.trim()} onClick={() => send()} style={{ flexShrink: 0 }}>{t('agent.send')}</Button>
          </Group>
          <Group gap={6} mt="xs" wrap="nowrap"><IconMessageCircle size={14} style={{ flexShrink: 0 }} /><Text c="dimmed" fz="xs">{t('agent.note')}</Text></Group>
        </Box>
        </Box>
      </Paper>
    </Stack>

    <Drawer opened={listOpen} onClose={() => setListOpen(false)} title={t('agent.previousChats')} size="80%" hiddenFrom="sm">
      <Stack gap="xs" style={{ minHeight: 0 }}>
        <ChatList {...listProps} />
      </Stack>
    </Drawer>

    <ConfirmModal
      opened={Boolean(deleteTarget)}
      onClose={() => setDeleteTarget(null)}
      onConfirm={removeChat}
      loading={deleting}
      title={t('agent.deleteChat')}
      text={t('agent.deleteConfirm', { title: deleteTarget?.title || t('agent.untitled') })}
      hint={t('agent.deleteHint')}
      confirmLabel={t('common.delete')}
    />
  </Box>
}
