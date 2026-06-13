import { useState, useEffect } from 'react'
import { markResourceRead, hasReadResource } from '../services/progressService'
import {
  Badge,
  Box,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
  ThemeIcon,
  Anchor,
} from '@mantine/core'
import {
  IconBooks,
  IconBrain,
  IconChartBar,
  IconFileText,
  IconLink,
  IconShield,
} from '@tabler/icons-react'
import PageShell from './PageShell'

const RESOURCES = [
  {
    title: 'Wie funktionieren LLMs?',
    description: 'Eine verständliche Erklärung großer Sprachmodelle und warum sie Fehler machen — wichtig vor dem Einsatz von AI in Finanzberichten.',
    category: 'AI Grundlagen',
    color: 'brand',
    icon: IconBrain,
    url: 'https://www.anthropic.com/news/core-views-on-ai-safety',
  },
  {
    title: 'Prompts für Finance-Profis',
    description: 'Wie man effektive Prompts schreibt für Aufgaben wie Berichts-Zusammenfassungen, Abgrenzungsbuchungen oder Abweichungsanalysen.',
    category: 'Prompting',
    color: 'blue',
    icon: IconFileText,
    url: 'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview',
  },
  {
    title: 'AI im Rechnungswesen: Anwendungsfälle',
    description: 'Praxisbeispiele für den Einsatz von AI beim Monatsabschluss, der Abstimmung und der Finanzplanung.',
    category: 'Anwendungsfälle',
    color: 'green',
    icon: IconChartBar,
    url: 'https://www.pwc.com/gx/en/issues/technology/artificial-intelligence/what-is-responsible-ai.html',
  },
  {
    title: 'Datenschutz & DSGVO mit AI',
    description: 'Was Finanzangestellte wissen müssen, bevor sie Unternehmensdaten in AI-Tools eingeben. Compliance- und Vertraulichkeitsregeln.',
    category: 'Compliance',
    color: 'red',
    icon: IconShield,
    url: 'https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/kuenstliche-intelligenz_node.html',
  },
  {
    title: 'Halluzinationen erkennen',
    description: 'Praktische Checkliste zur Überprüfung von AI-generierten Zahlen, Zusammenfassungen und Empfehlungen vor der Verwendung in Berichten.',
    category: 'AI Grundlagen',
    color: 'brand',
    icon: IconBrain,
    url: 'https://www.ibm.com/topics/ai-hallucinations',
  },
  {
    title: 'SAP & AI: Was sich ändert',
    description: 'Überblick darüber, wie SAP AI in Finance-Workflows integriert und was Controller und Buchhalter erwarten können.',
    category: 'Tools',
    color: 'violet',
    icon: IconLink,
    url: 'https://www.sap.com/products/artificial-intelligence.html',
  },
]


function ResourceCard({ title, description, category, color, icon: Icon, url, resourceId, userId }) {
  const [read, setRead] = useState(() => hasReadResource(userId, resourceId))

  useEffect(() => {
    const handler = () => setRead(hasReadResource(userId, resourceId))
    window.addEventListener('ai-facilitator-progress-updated', handler)
    return () => window.removeEventListener('ai-facilitator-progress-updated', handler)
  }, [userId, resourceId])


  const handleRead = () => {
    markResourceRead(userId, resourceId)
    setRead(true)
    window.open(url, '_blank')
  }

  return (
    <Card withBorder radius="lg" p="lg" bg="white" h="100%">
      <Stack gap="sm" h="100%">
        <Group justify="space-between" align="flex-start">
          <ThemeIcon size={40} radius="md" variant="light" color={color}>
            <Icon size={22} />
          </ThemeIcon>
          <Badge size="sm" radius="sm" color={color} variant="light">
            {category}
          </Badge>
        </Group>
        <Text fw={600} c="secondary.9" fz="md">
          {title}
        </Text>
        <Text fz="sm" c="dimmed" style={{ flex: 1 }}>
          {description}
        </Text>
        <Group justify="space-between" align="center">
          <Anchor onClick={handleRead} fz="sm" fw={600} c={color} style={{ cursor: 'pointer' }}>
            Mehr lesen →
          </Anchor>
          {read && (
            <Badge size="sm" color="green" variant="light">
              ✓ Gelesen
            </Badge>
          )}
        </Group>
      </Stack>
    </Card>
  )
}

export default function Resources({ user }) {
  const userId = user?.id || user?.email || user?.username || ''
  console.log('Resources userId:', userId)
  return (
    <PageShell title="Ressourcen" icon={IconBooks}>
      <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }}>
        <Stack gap={6} mb="xl">
          <Title order={2} fz={{ base: 22, md: 28 }} c="secondary.9">
            AI-Ressourcen für Finance
          </Title>
          <Text fz="lg" c="dimmed">
            Kuratierte Artikel, Leitfäden und Tools, um AI effektiv und sicher in der täglichen Arbeit einzusetzen.
          </Text>
        </Stack>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {RESOURCES.map((resource) => (
            <ResourceCard key={resource.title} {...resource} resourceId={resource.title} userId={userId} />
          ))}
        </SimpleGrid>
      </Box>
    </PageShell>
  )
}