import {
  Badge,
  Box,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconArrowRight,
  IconBolt,
  IconFlame,
  IconSparkles,
  IconTrophy,
} from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'

const STATS = [
  { labelKey: 'home.stats.points', value: '1.240', icon: IconBolt, color: 'brand' },
  { labelKey: 'home.stats.streak', value: '7', icon: IconFlame, color: 'accent' },
  { labelKey: 'home.stats.rank', value: '#4', icon: IconTrophy, color: 'secondary' },
]

function StatCard({ stat }) {
  const { t } = useTranslation()
  const Icon = stat.icon
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text fz="sm" c="dimmed" fw={500}>
            {t(stat.labelKey)}
          </Text>
          <Text fz={30} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">
            {stat.value}
          </Text>
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={stat.color}>
          <Icon size={23} stroke={1.7} />
        </ThemeIcon>
      </Group>
    </Paper>
  )
}

export default function Home({ user }) {
  const { t } = useTranslation()
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      {/* Hero */}
      <Paper
        radius="xl"
        p={{ base: 'xl', md: 44 }}
        mb="xl"
        style={{
          position: 'relative',
          overflow: 'hidden',
          background:
            'linear-gradient(135deg, var(--mantine-color-secondary-7) 0%, var(--mantine-color-secondary-6) 55%, var(--mantine-color-brand-7) 135%)',
          color: '#fff',
        }}
      >
        <Box
          style={{
            position: 'absolute',
            top: '-30%',
            right: '-6%',
            width: 360,
            height: 360,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(var(--gold-rgb),0.22) 0%, rgba(var(--gold-rgb),0) 68%)',
          }}
        />
        <Stack gap="lg" style={{ position: 'relative', maxWidth: 640 }}>
          <Badge
            variant="light"
            color="yellow"
            size="lg"
            radius="sm"
            leftSection={<IconSparkles size={14} />}
            style={{ background: 'rgba(var(--gold-rgb),0.16)', color: 'var(--gold-soft)' }}
          >
            {t('home.badge')}
          </Badge>
          <Title order={1} fz={{ base: 32, md: 44 }} fw={600} lh={1.1}>
            {t('home.title', { name: user?.first_name || t('home.fallbackName') })}
          </Title>
          <Text fz={{ base: 17, md: 20 }} c="rgba(255,255,255,0.78)" lh={1.5}>
            {t('home.subtitle')}
          </Text>
          <Group gap="md" mt={4}>
            <Button
              size="md"
              variant="white"
              c="secondary.9"
              fw={700}
              rightSection={<IconArrowRight size={18} />}
            >
              {t('home.ctaContinue')}
            </Button>
            <Button size="md" variant="default" color="gray">
              {t('home.ctaMissions')}
            </Button>
          </Group>
        </Stack>
      </Paper>

      {/* Stats */}
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" mb="xl">
        {STATS.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </SimpleGrid>

    </Box>
  )
}
