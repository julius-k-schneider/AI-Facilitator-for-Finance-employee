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

const RESOURCE_LINKS = [
  { key: 'llmBasics', color: 'brand', icon: IconBrain, url: 'https://www.anthropic.com/news/core-views-on-ai-safety' },
  { key: 'prompting', color: 'blue', icon: IconFileText, url: 'https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview' },
  { key: 'useCases', color: 'green', icon: IconChartBar, url: 'https://www.pwc.com/gx/en/issues/technology/artificial-intelligence/what-is-responsible-ai.html' },
  { key: 'privacy', color: 'red', icon: IconShield, url: 'https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/kuenstliche-intelligenz_node.html' },
  { key: 'hallucinations', color: 'brand', icon: IconBrain, url: 'https://www.ibm.com/topics/ai-hallucinations' },
  { key: 'sap', color: 'violet', icon: IconLink, url: 'https://www.sap.com/products/artificial-intelligence.html' },
]

function ResourceCard({ resourceKey, color, icon: Icon, url, t }) {
  return (
    <Card withBorder radius="lg" p="lg" bg="white" h="100%">
      <Stack gap="sm" h="100%">
        <Group justify="space-between" align="flex-start">
          <ThemeIcon size={40} radius="md" variant="light" color={color}>
            <Icon size={22} />
          </ThemeIcon>
          <Badge size="sm" radius="sm" color={color} variant="light">
            {t(`pages.library.resources.${resourceKey}.category`)}
          </Badge>
        </Group>
        <Text fw={600} c="secondary.9" fz="md">
          {t(`pages.library.resources.${resourceKey}.title`)}
        </Text>
        <Text fz="sm" c="dimmed" style={{ flex: 1 }}>
          {t(`pages.library.resources.${resourceKey}.description`)}
        </Text>
        <Anchor href={url} target="_blank" fz="sm" fw={600} c={color}>
          {t('pages.library.readMore')} →
        </Anchor>
      </Stack>
    </Card>
  )
}

export default function Library() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.library.title')}
      description={t('pages.library.description')}
      icon={IconBooks}
    >
      <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }}>
        <Stack gap={6} mb="xl">
          <Title order={2} fz={{ base: 22, md: 28 }} c="secondary.9">
            {t('pages.library.sectionTitle')}
          </Title>
          <Text fz="lg" c="dimmed">
            {t('pages.library.sectionSubtitle')}
          </Text>
        </Stack>
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {RESOURCE_LINKS.map((resource) => (
            <ResourceCard key={resource.key} resourceKey={resource.key} color={resource.color} icon={resource.icon} url={resource.url} t={t} />
          ))}
        </SimpleGrid>
      </Box>
    </PageShell>
  )
}