import {
  Box,
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
} from '@mantine/core'
import {
  IconArrowRight,
  IconBolt,
  IconFlame,
  IconLock,
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

export default function Home({ user, onNavigate }) {
  const { t } = useTranslation()
  const onboardingDone = Boolean(user?.onboarding_completed)
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      {/* Hinweis: Daily Challenges erst nach abgeschlossenem Onboarding */}
      {!onboardingDone && (
        <Paper withBorder radius="lg" p={{ base: 'lg', md: 'xl' }} mb="xl" bg="white">
          <Group justify="space-between" align="center" wrap="wrap" gap="md">
            <Group gap="md" wrap="nowrap" align="flex-start">
              <ThemeIcon size={44} radius="md" variant="light" color="accent">
                <IconLock size={22} stroke={1.7} />
              </ThemeIcon>
              <Box>
                <Text fw={700} c="secondary.9">
                  {t('home.locked.title')}
                </Text>
                <Text fz="sm" c="dimmed" maw={520}>
                  {t('home.locked.text')}
                </Text>
              </Box>
            </Group>
            <Button
              color="brand"
              rightSection={<IconArrowRight size={18} />}
              onClick={() => onNavigate?.('grundlagen')}
            >
              {t('home.locked.cta')}
            </Button>
          </Group>
        </Paper>
      )}

      {/* Stats */}
      <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg" mb="xl">
        {STATS.map((stat) => (
          <StatCard key={stat.label} stat={stat} />
        ))}
      </SimpleGrid>

    </Box>
  )
}
