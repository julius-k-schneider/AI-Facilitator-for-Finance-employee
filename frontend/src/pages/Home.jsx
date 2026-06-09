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
  IconChecklist,
  IconSparkles,
  IconTargetArrow,
  IconTrophy,
} from '@tabler/icons-react'
import { MISSIONS } from '../data/missions'
import { useUserProgress } from '../hooks/useUserProgress'
import { getLevel } from '../services/progressService'

function displayName(user) {
  const fullName = `${user?.first_name || ''} ${user?.last_name || ''}`.trim()
  return fullName || user?.username || user?.email || 'Kollege'
}

function StatCard({ label, value, icon: Icon, color = 'brand' }) {
  return (
    <Paper withBorder radius="lg" p="lg" bg="white">
      <Group justify="space-between" align="flex-start">
        <Stack gap={2}>
          <Text fz="sm" c="dimmed" fw={500}>
            {label}
          </Text>
          <Text fz={30} fw={700} c="secondary.9" lh={1} ff="var(--font-display)">
            {value}
          </Text>
        </Stack>
        <ThemeIcon size={44} radius="md" variant="light" color={color}>
          <Icon size={23} stroke={1.7} />
        </ThemeIcon>
      </Group>
    </Paper>
  )
}

function DashboardSection({ title, children }) {
  return (
    <Stack gap="md">
      <Title order={2} fz={22} c="secondary.9">
        {title}
      </Title>
      {children}
    </Stack>
  )
}

function NextMissionCard({ mission, onStart }) {
  if (!mission) {
    return (
      <Paper withBorder radius="lg" p="xl" bg="white">
        <Group gap="md" align="flex-start">
          <ThemeIcon size={48} radius="md" variant="light" color="accent">
            <IconTrophy size={25} stroke={1.7} />
          </ThemeIcon>
          <Stack gap={6} style={{ flex: 1 }}>
            <Text fw={700} c="secondary.9">
              Alle Missions abgeschlossen
            </Text>
            <Text fz="sm" c="dimmed">
              Du hast die aktuell verfuegbaren Finance-Missions abgeschlossen. Neue Missions
              koennen spaeter ueber die zentrale Registry ergaenzt werden.
            </Text>
          </Stack>
        </Group>
      </Paper>
    )
  }

  return (
    <Paper withBorder radius="lg" p="xl" bg="white">
      <Group align="flex-start" justify="space-between" gap="lg">
        <Group gap="md" align="flex-start" wrap="nowrap" style={{ flex: 1 }}>
          <ThemeIcon size={48} radius="md" variant="light" color="brand">
            <IconTargetArrow size={25} stroke={1.7} />
          </ThemeIcon>
          <Stack gap={8} style={{ flex: 1 }}>
            <Group gap="xs">
              <Badge color="brand" variant="light">
                {mission.category}
              </Badge>
              <Badge color="secondary" variant="light">
                {mission.difficulty}
              </Badge>
            </Group>
            <Box>
              <Text fw={700} c="secondary.9" fz="lg">
                {mission.title}
              </Text>
              <Text fz="sm" c="dimmed" mt={3}>
                {mission.description}
              </Text>
            </Box>
            <Text fz="sm" c="dimmed">
              {mission.estimatedTime} · bis zu {mission.maxPoints} Punkte
            </Text>
          </Stack>
        </Group>
        <Button color="brand" rightSection={<IconArrowRight size={17} />} onClick={onStart}>
          Mission starten
        </Button>
      </Group>
    </Paper>
  )
}

export default function Home({ user, navigate }) {
  const { progress, nextMission } = useUserProgress(user)
  const level = getLevel(progress.totalPoints)

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
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
            background:
              'radial-gradient(circle, rgba(var(--gold-rgb),0.22) 0%, rgba(var(--gold-rgb),0) 68%)',
          }}
        />
        <Stack gap="lg" style={{ position: 'relative', maxWidth: 680 }}>
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
            Willkommen zurueck, {displayName(user)}.
          </Title>
          <Text fz={{ base: 17, md: 20 }} c="rgba(255,255,255,0.78)" lh={1.5}>
            Trainiere deine AI-Skills mit kurzen Finance-Missions und sammle Punkte.
          </Text>
          <Group gap="md" mt={4}>
            <Button
              size="md"
              variant="white"
              c="secondary.9"
              fw={700}
              rightSection={<IconArrowRight size={18} />}
              onClick={() =>
                navigate('missions', nextMission ? { startMissionId: nextMission.id } : {})
              }
            >
              {nextMission ? 'Naechste Mission starten' : 'Missions ansehen'}
            </Button>
            <Button size="md" variant="default" color="gray" onClick={() => navigate('leaderboard')}>
              Leaderboard ansehen
            </Button>
          </Group>
        </Stack>
      </Paper>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg" mb="xl">
        <StatCard label="Gesamtpunkte" value={progress.totalPoints} icon={IconBolt} color="brand" />
        <StatCard
          label="Abgeschlossene Missions"
          value={progress.completedMissions.length}
          icon={IconChecklist}
          color="accent"
        />
        <StatCard label="Verfuegbare Missions" value={MISSIONS.length} icon={IconTargetArrow} color="secondary" />
        <StatCard label="Level" value={level} icon={IconTrophy} color="brand" />
      </SimpleGrid>

      <DashboardSection title="Next Mission">
        <NextMissionCard
          mission={nextMission}
          onStart={() => navigate('missions', { startMissionId: nextMission?.id })}
        />
      </DashboardSection>
    </Box>
  )
}
