import { useState, useEffect } from 'react'
import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core'
import {
  IconArrowRight,
  IconBook,
  IconCheck,
  IconLock,
  IconRoute,
} from '@tabler/icons-react'
import { hasReadResource } from '../services/progressService'
import LerncheckHalluzinationen from './lerncheck/LerncheckHalluzinationen'

const LEARNING_ITEMS = [
  {
    id: 'halluzinationen',
    title: 'Halluzinationen erkennen',
    description: 'Lerne, was AI-Halluzinationen sind und wie du sie im Finanzbereich erkennst.',
    resourceId: 'Halluzinationen erkennen',
    lerncheckId: 'lerncheck-halluzinationen',
    color: 'brand',
  },
]

function LearningCard({ item, userId, onStartLerncheck }) {
  const [hasRead, setHasRead] = useState(() => hasReadResource(userId, item.resourceId))

  useEffect(() => {
    const handler = () => setHasRead(hasReadResource(userId, item.resourceId))
    window.addEventListener('ai-facilitator-progress-updated', handler)
    return () => window.removeEventListener('ai-facilitator-progress-updated', handler)
  }, [userId, item.resourceId])


  return (
    <Card withBorder radius="lg" p="lg" bg="white" h="100%">
      <Stack gap="sm" h="100%">
        <Group justify="space-between" align="flex-start">
          <ThemeIcon size={40} radius="md" variant="light" color={item.color}>
            <IconBook size={22} />
          </ThemeIcon>
          {hasRead ? (
            <Badge size="sm" color="green" variant="light">
              ✓ Gelesen
            </Badge>
          ) : (
            <Badge size="sm" color="gray" variant="light">
              Noch nicht gelesen
            </Badge>
          )}
        </Group>

        <Text fw={600} c="secondary.9" fz="md">
          {item.title}
        </Text>
        <Text fz="sm" c="dimmed" style={{ flex: 1 }}>
          {item.description}
        </Text>

        <Button
          color="brand"
          variant={hasRead ? 'filled' : 'light'}
          disabled={!hasRead}
          rightSection={hasRead ? <IconArrowRight size={17} /> : <IconLock size={17} />}
          onClick={() => onStartLerncheck(item.lerncheckId)}
        >
          {hasRead ? 'Lerncheck starten' : 'Zuerst den Artikel lesen'}
        </Button>
      </Stack>
    </Card>
  )
}

export default function LearningPath({ user }) {
  const userId = user?.id || user?.email || user?.username || ''
  const [activeLerncheckId, setActiveLerncheckId] = useState(null)

  if (activeLerncheckId === 'lerncheck-halluzinationen') {
    return (
      <LerncheckHalluzinationen
        userId={userId}
        onBack={() => setActiveLerncheckId(null)}
      />
    )
  }

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      <Stack gap={6} mb="xl">
        <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
          Learning Path
        </Title>
        <Text fz="lg" c="dimmed" maw={680}>
          Lies die Artikel in Ressourcen, dann teste dein Wissen mit dem Lerncheck.
        </Text>
      </Stack>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        {LEARNING_ITEMS.map((item) => (
          <LearningCard
            key={item.id}
            item={item}
            userId={userId}
            onStartLerncheck={setActiveLerncheckId}
          />
        ))}
      </SimpleGrid>
    </Box>
  )
}