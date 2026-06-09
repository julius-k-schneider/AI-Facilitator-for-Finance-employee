import {
  Badge,
  Box,
  Button,
  Group,
  Paper,
  Progress,
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
  IconRoute,
  IconSparkles,
  IconTargetArrow,
  IconTrophy,
} from '@tabler/icons-react'

const STATS = [
  { label: 'Punkte', value: '1.240', icon: IconBolt, color: 'brand' },
  { label: 'Tagesstreak', value: '7', icon: IconFlame, color: 'accent' },
  { label: 'Team-Rang', value: '#4', icon: IconTrophy, color: 'secondary' },
]

const ACTIONS = [
  {
    title: 'Setze deinen Learning Path fort',
    text: 'Modul „Prompting für Finance-Analysen“ wartet auf dich.',
    icon: IconRoute,
    cta: 'Weiterlernen',
  },
  {
    title: 'Neue Mission verfügbar',
    text: 'Erstelle eine automatisierte Reporting-Zusammenfassung mit AI.',
    icon: IconTargetArrow,
    cta: 'Mission starten',
  },
]

function StatCard({ stat }) {
  const Icon = stat.icon
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text fz="sm" c="dimmed" fw={500}>
            {stat.label}
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
            AI ENABLEMENT
          </Badge>
          <Title order={1} fz={{ base: 32, md: 44 }} fw={600} lh={1.1}>
            Willkommen zurück, {user?.first_name || 'Kollege'}.
          </Title>
          <Text fz={{ base: 17, md: 20 }} c="rgba(255,255,255,0.78)" lh={1.5}>
            Baue die AI-Skills von morgen – Schritt für Schritt, mit echten
            Cases aus deinem Finance-Alltag.
          </Text>
          <Group gap="md" mt={4}>
            <Button
              size="md"
              variant="white"
              c="secondary.9"
              fw={700}
              rightSection={<IconArrowRight size={18} />}
            >
              Weiterlernen
            </Button>
            <Button size="md" variant="default" color="gray">
              Missionen ansehen
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

      {/* Fortschritt + Aktionen */}
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <Paper withBorder radius="lg" p="xl" bg="white">
          <Group justify="space-between" mb="md">
            <Text fw={600} fz="lg" c="secondary.9">
              Dein Wochenziel
            </Text>
            <Text fz="sm" c="dimmed">
              3 / 5 Module
            </Text>
          </Group>
          <Progress value={60} color="brand" size="lg" radius="xl" mb="lg" />
          <Text c="dimmed" fz="sm">
            Noch 2 Module bis zu deinem nächsten Badge. Bleib dran – du bist auf
            einem starken Streak!
          </Text>
        </Paper>

        <Stack gap="lg">
          {ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <Paper key={action.title} withBorder radius="lg" p="lg" bg="white">
                <Group wrap="nowrap" align="flex-start" gap="md">
                  <ThemeIcon size={46} radius="md" variant="light" color="brand">
                    <Icon size={24} stroke={1.7} />
                  </ThemeIcon>
                  <Box style={{ flex: 1 }}>
                    <Text fw={600} c="secondary.9">
                      {action.title}
                    </Text>
                    <Text fz="sm" c="dimmed" mt={2}>
                      {action.text}
                    </Text>
                  </Box>
                  <Button
                    variant="subtle"
                    color="brand"
                    size="compact-sm"
                    rightSection={<IconArrowRight size={15} />}
                  >
                    {action.cta}
                  </Button>
                </Group>
              </Paper>
            )
          })}
        </Stack>
      </SimpleGrid>
    </Box>
  )
}
