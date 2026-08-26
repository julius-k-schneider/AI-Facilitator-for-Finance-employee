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
import PageShell from './PageShell'
import { notifySuccess } from '../services/notify'

const API_BASE = import.meta.env.VITE_API_BASE || ''

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
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ old_password: '', new_password: '' })

  const handlePasswordChange = async (event) => {
    event.preventDefault()
    setError('')
    setSaving(true)
    try {
      const response = await fetch(`${API_BASE}/api/auth/change-password/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(passwordForm),
      })
      // A 500 answers with HTML, not JSON. Parsing that unguarded used to throw
      // and leave the user without any feedback at all.
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        setError(data.error || t('profile.errorChange'))
        return
      }
      notifySuccess(t('profile.successChange'))
      setPasswordForm({ old_password: '', new_password: '' })
    } catch {
      setError(t('app.networkError'))
    } finally {
      setSaving(false)
    }
  }

  const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim()

  return (
    <PageShell title={t('profile.title')}>
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

        <SimpleGrid cols={{ base: 1, sm: 4 }} spacing="xl">
          <Field label={t('profile.fieldName')} value={fullName} />
          <Field label={t('profile.fieldEmail')} value={user.email} />
          <Field label={t('profile.fieldUser')} value={user.username} />
          <Field label={t('profile.fieldSkillLevel')} value={t(`skillLevels.${user.skill_level || 'beginner'}`)} />
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
              autoComplete="current-password"
              value={passwordForm.old_password}
              onChange={(event) =>
                setPasswordForm((current) => ({ ...current, old_password: event.target.value }))
              }
            />
            <PasswordInput
              label={t('profile.newPassword')}
              description={t('profile.passwordRules')}
              autoComplete="new-password"
              value={passwordForm.new_password}
              onChange={(event) =>
                setPasswordForm((current) => ({ ...current, new_password: event.target.value }))
              }
            />
            <Button
              type="submit"
              color="brand"
              mt="xs"
              w="fit-content"
              loading={saving}
              disabled={!passwordForm.old_password || !passwordForm.new_password}
            >
              {t('profile.changePassword')}
            </Button>
            {error && (
              <Alert color="red" variant="light" radius="md">
                {error}
              </Alert>
            )}
          </Stack>
        </form>
      </Paper>
    </PageShell>
  )
}

export default Profile
