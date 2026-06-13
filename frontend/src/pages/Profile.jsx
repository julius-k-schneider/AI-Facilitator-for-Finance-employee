import { useState } from 'react'
import {
  Alert,
  Avatar,
  Box,
  Button,
  Divider,
  Group,
  Paper,
  PasswordInput,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { IconLock } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function Field({ label, value }) {
  return (
    <Box>
      <Text fz="xs" fw={700} c="brand.6" mb={4} style={{ letterSpacing: '0.06em' }}>
        {label.toUpperCase()}
      </Text>
      <Text c="secondary.9" fw={500}>
        {value || '—'}
      </Text>
    </Box>
  )
}

function Profile({ user }) {
  const { t } = useTranslation()
  const [passwordMessage, setPasswordMessage] = useState(null)
  const [passwordForm, setPasswordForm] = useState({ old_password: '', new_password: '' })

  const handlePasswordChange = async (event) => {
    event.preventDefault()
    setPasswordMessage(null)
    const response = await fetch(`${API_BASE}/api/auth/change-password/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(passwordForm),
    })

    const data = await response.json()
    if (!response.ok) {
      setPasswordMessage({ type: 'error', text: data.error || t('profile.errorChange') })
      return
    }

    setPasswordMessage({ type: 'success', text: t('profile.successChange') })
    setPasswordForm({ old_password: '', new_password: '' })
  }

  const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim()

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={900}>
      <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9" mb="xl">
        {t('profile.title')}
      </Title>

      <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} mb="lg" bg="white">
        <Group mb="xl" gap="lg">
          <Avatar
            size={64}
            radius="xl"
            style={{ background: 'var(--ink)', color: '#fff', fontWeight: 700, fontSize: 22 }}
          >
            {(user.first_name?.[0] || user.username?.[0] || '?').toUpperCase()}
            {(user.last_name?.[0] || '').toUpperCase()}
          </Avatar>
          <Box>
            <Text fz="xl" fw={700} c="secondary.9">
              {fullName || user.username}
            </Text>
            <Text c="dimmed">{user.email}</Text>
          </Box>
        </Group>

        <Divider mb="xl" />

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="xl">
          <Field label={t('profile.fieldName')} value={fullName} />
          <Field label={t('profile.fieldEmail')} value={user.email} />
          <Field label={t('profile.fieldUser')} value={user.username} />
        </SimpleGrid>
      </Paper>

      <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} bg="white">
        <Group gap="sm" mb="lg">
          <IconLock size={20} stroke={1.8} color="var(--blue)" />
          <Title order={3} fz="lg" c="secondary.9">
            {t('profile.changePassword')}
          </Title>
        </Group>
        <form onSubmit={handlePasswordChange}>
          <Stack gap="md" maw={420}>
            <PasswordInput
              label={t('profile.currentPassword')}
              value={passwordForm.old_password}
              onChange={(event) =>
                setPasswordForm((current) => ({ ...current, old_password: event.target.value }))
              }
            />
            <PasswordInput
              label={t('profile.newPassword')}
              value={passwordForm.new_password}
              onChange={(event) =>
                setPasswordForm((current) => ({ ...current, new_password: event.target.value }))
              }
            />
            <Button type="submit" color="brand" mt="xs" w="fit-content">
              {t('profile.changePassword')}
            </Button>
            {passwordMessage && (
              <Alert
                color={passwordMessage.type === 'error' ? 'red' : 'green'}
                variant="light"
                radius="md"
              >
                {passwordMessage.text}
              </Alert>
            )}
          </Stack>
        </form>
      </Paper>
    </Box>
  )
}

export default Profile
