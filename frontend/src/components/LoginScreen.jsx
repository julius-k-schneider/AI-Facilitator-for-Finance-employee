import {
  Alert,
  Box,
  Button,
  Group,
  Image,
  PasswordInput,
  SegmentedControl,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { IconArrowRight, IconSparkles } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { branding } from '../branding'

export default function LoginScreen({ mode, onModeChange, form, onFieldChange, onSubmit, message }) {
  const { t } = useTranslation()
  const isLogin = mode === 'login'
  const highlights = t('login.highlights', { returnObjects: true })
  const roleOptions = [
    { value: 'controller', label: t('roles.controller') },
    { value: 'accountant', label: t('roles.accountant') },
  ]

  return (
    <Box
      style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1.05fr) minmax(0, 1fr)',
      }}
    >
      {/* Left brand panel */}
      <Box
        visibleFrom="md"
        style={{
          position: 'relative',
          overflow: 'hidden',
          padding: '56px 60px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          background:
            'linear-gradient(155deg, var(--mantine-color-secondary-6) 0%, var(--mantine-color-secondary-7) 55%, var(--mantine-color-secondary-9) 100%)',
          color: '#fff',
        }}
      >
        <Box
          style={{
            position: 'absolute',
            top: '-12%',
            right: '-8%',
            width: 420,
            height: 420,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(var(--gold-rgb),0.22) 0%, rgba(var(--gold-rgb),0) 68%)',
            animation: 'floatGlow 9s ease-in-out infinite',
          }}
        />
        <Box
          style={{
            position: 'absolute',
            bottom: '-18%',
            left: '-10%',
            width: 360,
            height: 360,
            borderRadius: '50%',
            background:
              'radial-gradient(circle, rgba(var(--blue-rgb),0.55) 0%, rgba(var(--blue-rgb),0) 70%)',
          }}
        />

        <Box
          className="fade-in"
          bg="white"
          px="md"
          py={12}
          w="fit-content"
          style={{ borderRadius: 14, position: 'relative', boxShadow: '0 10px 30px rgba(0,0,0,0.25)' }}
        >
          <Image src={branding.logo} alt={branding.logoAlt} h={28} w="auto" fit="contain" />
        </Box>

        <Stack gap="xl" style={{ position: 'relative', maxWidth: 460 }}>
          <Stack gap="md">
            <Group gap={8} c="var(--gold)">
              <IconSparkles size={18} />
              <Text fz={13} fw={600} style={{ letterSpacing: '0.16em' }}>
                {t('login.platform')}
              </Text>
            </Group>
            <Title order={1} fz={46} fw={600} lh={1.08} className="fade-up" style={{ animationDelay: '0.05s' }}>
              {t('login.heroTitle')}
            </Title>
            <Text fz={18} c="rgba(255,255,255,0.72)" lh={1.5} className="fade-up" style={{ animationDelay: '0.12s' }}>
              {t('login.heroSubtitle', { tagline: branding.tagline })}
            </Text>
          </Stack>

          <Stack gap="sm" className="fade-up" style={{ animationDelay: '0.2s' }}>
            {highlights.map((item) => (
              <Group key={item} gap={12} wrap="nowrap">
                <Box
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    background: 'var(--gold)',
                    flexShrink: 0,
                  }}
                />
                <Text fz={15} c="rgba(255,255,255,0.85)">
                  {item}
                </Text>
              </Group>
            ))}
          </Stack>
        </Stack>

        <Text fz={13} c="rgba(255,255,255,0.4)" style={{ position: 'relative' }}>
          {t('login.footer')}
        </Text>
      </Box>

      {/* Right form panel */}
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '48px 28px',
          background: '#fff',
        }}
      >
        <Box w="100%" maw={400} className="fade-up">
          <Image
            src={branding.logo}
            alt={branding.logoAlt}
            h={26}
            w="auto"
            fit="contain"
            mb={36}
            hiddenFrom="md"
          />

          <Title order={2} fz={30} c="secondary.9" mb={6}>
            {isLogin ? t('login.welcomeBack') : t('login.createAccount')}
          </Title>
          <Text c="dimmed" mb="xl">
            {isLogin ? t('login.loginSubtitle') : t('login.registerSubtitle')}
          </Text>

          <SegmentedControl
            fullWidth
            radius="md"
            color="brand"
            value={mode}
            onChange={onModeChange}
            data={[
              { value: 'login', label: t('login.tabLogin') },
              { value: 'register', label: t('login.tabRegister') },
            ]}
            mb="xl"
          />

          <form onSubmit={onSubmit}>
            <Stack gap="md">
              {!isLogin && (
                <Group grow gap="md">
                  <TextInput
                    label={t('login.firstName')}
                    placeholder={t('login.placeholderFirstName')}
                    value={form.first_name}
                    onChange={onFieldChange('first_name')}
                  />
                  <TextInput
                    label={t('login.lastName')}
                    placeholder={t('login.placeholderLastName')}
                    value={form.last_name}
                    onChange={onFieldChange('last_name')}
                  />
                </Group>
              )}
              {!isLogin && (
                <Select
                  label={t('login.role')}
                  data={roleOptions}
                  value={form.role}
                  onChange={(value) => onFieldChange('role')({ target: { value: value ?? '' } })}
                  allowDeselect={false}
                  checkIconPosition="right"
                />
              )}
              <TextInput
                label={t('login.email')}
                type="email"
                placeholder={t('login.placeholderEmail')}
                value={form.email}
                onChange={onFieldChange('email')}
              />
              <PasswordInput
                label={t('login.password')}
                placeholder="••••••••"
                value={form.password}
                onChange={onFieldChange('password')}
              />
              <Button
                type="submit"
                color="brand"
                fullWidth
                size="md"
                mt="xs"
                rightSection={<IconArrowRight size={18} />}
              >
                {isLogin ? t('login.submitLogin') : t('login.submitRegister')}
              </Button>
            </Stack>
          </form>

          {message && (
            <Alert color="red" variant="light" mt="lg" radius="md">
              {message}
            </Alert>
          )}
        </Box>
      </Box>
    </Box>
  )
}
