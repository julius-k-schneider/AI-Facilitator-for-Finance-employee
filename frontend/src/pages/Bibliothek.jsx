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
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'

const RESOURCES = [
  {
    title: 'How LLMs Work',
    description: 'A plain-language explanation of large language models and why they make mistakes — essential before using AI in financial reports.',
    category: 'AI Basics',
    color: 'brand',
    icon: IconBrain,
    url: 'https://www.anthropic.com/news/core-views-on-ai-safety',
  },
  {
    title: 'Prompting for Finance Professionals',
    description: 'How to write effective prompts for tasks like summarizing reports, drafting accruals, or explaining variances.',
    category: 'Prompting',
    color: 'blue',
    icon: IconFileText,
    url: 'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview',
  },
  {
    title: 'AI in Accounting: Use Cases',
    description: 'Real-world examples of AI applied to month-end closing, reconciliation, and financial forecasting.',
    category: 'Use Cases',
    color: 'green',
    icon: IconChartBar,
    url: 'https://www.pwc.com/gx/en/issues/technology/artificial-intelligence/what-is-responsible-ai.html',
  },
  {
    title: 'Data Privacy & GDPR with AI',
    description: 'What financial employees must know before entering company data into AI tools. Compliance and confidentiality rules.',
    category: 'Compliance',
    color: 'red',
    icon: IconShield,
    url: 'https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/kuenstliche-intelligenz_node.html',
  },
  {
    title: 'Hallucinations: How to Spot Them',
    description: 'Practical checklist for verifying AI-generated numbers, summaries, and recommendations before using them in reports.',
    category: 'AI Basics',
    color: 'brand',
    icon: IconBrain,
    url: 'https://www.ibm.com/topics/ai-hallucinations',
  },
  {
    title: 'SAP & AI: What\'s Changing',
    description: 'Overview of how SAP is integrating AI into finance workflows and what controllers and accountants can expect.',
    category: 'Tools',
    color: 'violet',
    icon: IconLink,
    url: 'https://www.sap.com/products/artificial-intelligence.html',
  },
]

function ResourceCard({ title, description, category, color, icon: Icon, url }) {
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
        <Anchor href={url} target="_blank" fz="sm" fw={600} c={color}>
          Read more →
        </Anchor>
      </Stack>
    </Card>
  )
}

export default function Bibliothek() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.bibliothek.title')}
      description={t('pages.bibliothek.description')}
      icon={IconBooks}
    >
      <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }}>
        <Stack gap={6} mb="xl">
          <Title order={2} fz={{ base: 22, md: 28 }} c="secondary.9">
            AI Resources for Finance
          </Title>
          <Text fz="lg" c="dimmed">
            Curated articles, guides and tools to help you use AI effectively and safely in your daily work.
          </Text>
        </Stack>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {RESOURCES.map((resource) => (
            <ResourceCard key={resource.title} {...resource} />
          ))}
        </SimpleGrid>
      </Box>
    </PageShell>
  )
}