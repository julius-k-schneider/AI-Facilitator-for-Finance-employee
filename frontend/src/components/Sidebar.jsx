import { Avatar, Box, Group, Image, Stack, Text, Tooltip, UnstyledButton } from '@mantine/core'
import { IconLogout, IconSettings } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { branding } from '../branding'
import { NAV_ITEMS, isNavItemActive } from '../nav'
import { PERMISSIONS, hasPermission } from '../auth/permissions'

function initials(user) {
  const a = user?.first_name?.[0] || user?.username?.[0] || '?'
  const b = user?.last_name?.[0] || ''
  return `${a}${b}`.toUpperCase()
}

function roleLabel(user, t) {
  if (user?.role_display) return user.role_display
  return user?.role ? t(`roles.${user.role}`, { defaultValue: '' }) : ''
}

function NavLink({ item, active, onClick }) {
  const { t } = useTranslation()
  const Icon = item.icon
  return (
    <UnstyledButton onClick={onClick} className={`sidebar-nav-link${active ? ' is-active' : ''}`}>
      <Box
        style={{
          position: 'absolute',
          left: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 3,
          height: active ? 22 : 0,
          borderRadius: 4,
          background: 'var(--gold)',
          transition: 'height 200ms ease',
        }}
      />
      <Icon size={21} stroke={1.8} color={active ? branding.colors.accent : 'currentColor'} />
      <span style={{ fontSize: 15, fontWeight: active ? 600 : 500, letterSpacing: '-0.01em' }}>
        {t(item.labelKey, { defaultValue: item.label })}
      </span>
    </UnstyledButton>
  )
}

export default function Sidebar({ user, onLogout }) {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const visibleItems = NAV_ITEMS.filter(
    (item) =>
      (!item.permission || hasPermission(user, item.permission)) &&
      (!item.requiresOnboarding || user?.onboarding_completed || hasPermission(user, PERMISSIONS.CREATE_CONTENT)),
  )
  return (
    <Box
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background:
          'linear-gradient(180deg, var(--mantine-color-secondary-6) 0%, var(--mantine-color-secondary-7) 58%, var(--mantine-color-secondary-9) 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Subtle gold glow in the top right */}
      <Box
        style={{
          position: 'absolute',
          top: -90,
          right: -70,
          width: 220,
          height: 220,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(var(--gold-rgb),0.20) 0%, rgba(var(--gold-rgb),0) 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Logo */}
      <Box px="lg" pt={26} pb={22} style={{ position: 'relative' }}>
        <Box
          bg="white"
          px="md"
          py={12}
          w="fit-content"
          maw="100%"
          style={{ borderRadius: 14, boxShadow: '0 6px 18px rgba(0,0,0,0.18)' }}
        >
          <Image
            src={branding.logo}
            alt={branding.logoAlt}
            w={156}
            h="auto"
            fit="contain"
            style={{ maxWidth: '100%' }}
          />
        </Box>
        <Text c="rgba(255,255,255,0.45)" fz={11} fw={600} mt={14} style={{ letterSpacing: '0.14em' }}>
          {t('sidebar.subtitle')}
        </Text>
      </Box>

      {/* Navigation */}
      <Stack gap={4} px="md" style={{ flex: 1 }}>
        {visibleItems.map((item) => (
          <NavLink
            key={item.value}
            item={item}
            active={isNavItemActive(item, location.pathname)}
            onClick={() => navigate(item.path)}
          />
        ))}
      </Stack>

      {/* User card + logout */}
      <Box p="md">
        <Box
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: 12,
            borderRadius: 14,
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <Avatar radius="xl" size={40} color="dark" style={{ background: 'var(--gold)', color: 'var(--ink)', fontWeight: 700 }}>
            {initials(user)}
          </Avatar>
          <Box style={{ minWidth: 0, flex: 1 }}>
            <Text c="white" fz={14} fw={600} truncate>
              {user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username}
            </Text>
            {roleLabel(user, t) && (
              <Box
                mt={6}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '2px 9px',
                  borderRadius: 999,
                  background: 'rgba(var(--gold-rgb),0.16)',
                  border: '1px solid rgba(var(--gold-rgb),0.35)',
                }}
              >
                <Text c="var(--gold)" fz={11} fw={600} style={{ letterSpacing: '0.04em' }}>
                  {roleLabel(user, t)}
                </Text>
              </Box>
            )}
          </Box>
          <Group gap={6} wrap="nowrap">
            <Tooltip label={t('sidebar.tooltipProfile')} position="top" withArrow>
              <UnstyledButton
                onClick={() => navigate('/profile')}
                aria-label={t('sidebar.tooltipProfile')}
                className="sidebar-icon-button"
              >
                <IconSettings size={19} stroke={1.8} />
              </UnstyledButton>
            </Tooltip>
            <Tooltip label={t('sidebar.tooltipLogout')} position="top" withArrow>
              <UnstyledButton
                onClick={onLogout}
                aria-label={t('sidebar.tooltipLogout')}
                className="sidebar-icon-button"
              >
                <IconLogout size={19} stroke={1.8} />
              </UnstyledButton>
            </Tooltip>
          </Group>
        </Box>
      </Box>
    </Box>
  )
}
