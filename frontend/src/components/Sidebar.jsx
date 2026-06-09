import { Avatar, Box, Image, Stack, Text, Tooltip, UnstyledButton } from '@mantine/core'
import { IconLogout } from '@tabler/icons-react'
import { branding } from '../branding'
import { NAV_ITEMS } from '../nav'
import { hasPermission } from '../auth/permissions'

function initials(user) {
  const a = user?.first_name?.[0] || user?.username?.[0] || '?'
  const b = user?.last_name?.[0] || ''
  return `${a}${b}`.toUpperCase()
}

function NavLink({ item, active, onClick }) {
  const Icon = item.icon
  return (
    <UnstyledButton
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        width: '100%',
        padding: '11px 14px',
        borderRadius: 12,
        position: 'relative',
        color: active ? '#fff' : 'rgba(255,255,255,0.62)',
        background: active ? 'rgba(255,255,255,0.10)' : 'transparent',
        transition: 'background 160ms ease, color 160ms ease',
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = 'transparent'
      }}
    >
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
        {item.label}
      </span>
    </UnstyledButton>
  )
}

export default function Sidebar({ page, onNavigate, user, onLogout }) {
  const visibleItems = NAV_ITEMS.filter((item) => !item.permission || hasPermission(user, item.permission))

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
      {/* Dezenter Gold-Schimmer oben rechts */}
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
          AI FACILITATOR
        </Text>
      </Box>

      {/* Navigation */}
      <Stack gap={4} px="md" style={{ flex: 1 }}>
        {visibleItems.map((item) => (
          <NavLink
            key={item.value}
            item={item}
            active={page === item.value}
            onClick={() => onNavigate(item.value)}
          />
        ))}
      </Stack>

      {/* User-Karte + Logout */}
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
            <Text c="rgba(255,255,255,0.5)" fz={12} truncate>
              {user?.email}
            </Text>
          </Box>
          <Tooltip label="Logout" position="top" withArrow>
            <UnstyledButton
              onClick={onLogout}
              aria-label="Logout"
              style={{
                display: 'grid',
                placeItems: 'center',
                width: 34,
                height: 34,
                borderRadius: 10,
                color: 'rgba(255,255,255,0.7)',
                transition: 'background 160ms ease, color 160ms ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.12)'
                e.currentTarget.style.color = '#fff'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.color = 'rgba(255,255,255,0.7)'
              }}
            >
              <IconLogout size={19} stroke={1.8} />
            </UnstyledButton>
          </Tooltip>
        </Box>
      </Box>
    </Box>
  )
}
