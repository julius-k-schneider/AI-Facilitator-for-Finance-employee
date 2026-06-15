/* eslint-disable react-refresh/only-export-components */
import { useState } from 'react'
import { Badge, Button, Group, NumberInput, Paper, Radio, Stack, Text, TextInput } from '@mantine/core'
import { IconMessage, IconSend } from '@tabler/icons-react'
import { sendTrainingChatMessage, submitTrainingChatChallenge } from '../../../services/trainingService'

function Runner({ mission, answer, setAnswer, result, t }) {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [remaining, setRemaining] = useState(3)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const send = async () => {
    if (!message.trim() || remaining <= 0) return
    const userMessage = message.trim()
    setSending(true); setError(''); setMessage('')
    try {
      const data = await sendTrainingChatMessage(mission.session_id, userMessage, mission.language)
      setMessages((current) => [...current, { role: 'user', text: userMessage }, { role: 'assistant', text: data.reply }])
      setRemaining(data.remaining_prompts)
    } catch (nextError) { setError(nextError.message) } finally { setSending(false) }
  }
  return <Stack gap="lg">
    <Paper withBorder radius="md" p="md"><Text fw={700} mb="xs">{t('training.chat.caseData')}</Text><Stack gap={4}>{mission.content.case_data.map((item, index) => <Text key={index} fz="sm">- {item}</Text>)}</Stack></Paper>
    <Paper withBorder radius="md" p="md"><Group justify="space-between"><Group gap="xs"><IconMessage size={19} /><Text fw={700}>{t('training.chat.title')}</Text></Group><Badge variant="light">{t('training.chat.remaining', { count: remaining })}</Badge></Group><Stack gap="sm" mt="md">{messages.map((item, index) => <Paper key={index} radius="md" p="sm" bg={item.role === 'user' ? 'brand.0' : 'gray.0'}><Text fz="xs" fw={700}>{item.role === 'user' ? t('training.chat.you') : t('training.chat.assistant')}</Text><Text fz="sm">{item.text}</Text></Paper>)}{messages.length === 0 && <Text c="dimmed" fz="sm">{t('training.chat.empty')}</Text>}</Stack><Group mt="md" align="flex-end"><TextInput style={{ flex: 1 }} label={t('training.chat.message')} value={message} disabled={remaining <= 0 || Boolean(result)} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') send() }} /><Button leftSection={<IconSend size={16} />} loading={sending} disabled={!message.trim() || remaining <= 0 || Boolean(result)} onClick={send}>{t('training.chat.send')}</Button></Group>{error && <Text c="red" fz="sm" mt="xs">{error}</Text>}</Paper>
    <Stack gap="md"><Text fw={700}>{t('training.chat.finalAnswers')}</Text>{mission.content.final_questions.map((question) => <Paper key={question.id} withBorder radius="md" p="md"><Text fw={600} mb="sm">{question.prompt}</Text>{question.type === 'number' ? <NumberInput value={answer[question.id] ?? ''} disabled={Boolean(result)} onChange={(value) => setAnswer((current) => ({ ...current, [question.id]: value }))} /> : <Radio.Group value={answer[question.id] === undefined ? '' : String(answer[question.id])} onChange={(value) => setAnswer((current) => ({ ...current, [question.id]: question.type === 'single_choice' ? Number(value) : question.type === 'evidence_boolean' ? value === 'true' : value }))}><Stack gap="xs">{question.options.map((option) => <Radio key={String(option.value)} value={String(option.value)} label={option.label} disabled={Boolean(result)} />)}</Stack></Radio.Group>}</Paper>)}</Stack>
  </Stack>
}

function ResultDetails({ result, t }) {
  return <Stack gap="xs">{result.items.map((item) => <Paper key={item.id} withBorder radius="md" p="sm"><Text fw={700} c={item.correct ? 'green.8' : 'red.7'}>{item.correct ? t('missions.result.correctPrefix') : t('missions.result.wrongPrefix')}</Text><Text fz="sm">{item.feedback}</Text></Paper>)}</Stack>
}

export default {
  id: 'ai_chat_challenge', labelKey: 'aiChatChallenge', trainingOnly: true,
  initialAnswer: () => ({}),
  isAnswerComplete: (answer) => Object.values(answer).filter((value) => value !== '' && value !== null && value !== undefined).length >= 2,
  Runner, ResultDetails,
  submitTraining: async (mission, answer, language) => ({ ...(await submitTrainingChatChallenge(mission.session_id, answer, language)), feedback: '' }),
}
