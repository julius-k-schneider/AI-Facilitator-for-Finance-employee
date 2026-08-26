import { Badge, Box, Group, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { useTranslation } from 'react-i18next'

/**
 * The frame every page sits in: outer padding, badge, title, description and an
 * optional action area on the right.
 *
 * Before this, the same px/py pair was copy-pasted into eight pages and the
 * title sizes had started to drift apart. Pages should only bring their content.
 */
export default function PageShell({ title, description, badge, actions, icon: Icon, children }) {
  const { t } = useTranslation()

  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} w="100%">
      <Group justify="space-between" align="flex-start" gap="lg" mb="xl" wrap="wrap">
        <Stack gap={6} style={{ flex: '1 1 320px', minWidth: 0 }}>
          {badge && <Badge variant="light" color="brand" w="fit-content">{badge}</Badge>}
          <Title order={2} fz={{ base: 28, md: 34 }} c="secondary.9">
            {title}
          </Title>
          {description && <Text fz="lg" c="dimmed" maw={700}>{description}</Text>}
        </Stack>
        {actions && <Group gap="sm" wrap="wrap">{actions}</Group>}
      </Group>

      {children || (
        <Paper withBorder radius="lg" p={{ base: 'xl', md: 56 }} bg="white">
          <Stack align="center" gap="md" py="lg">
            {Icon && <ThemeIcon size={64} radius="xl" variant="light" color="brand"><Icon size={30} /></ThemeIcon>}
            <Stack align="center" gap={4}>
              <Text fz="lg" fw={600}>{t('pages.comingSoon')}</Text>
              <Text c="dimmed" ta="center" maw={420}>{t('pages.comingSoonText')}</Text>
            </Stack>
          </Stack>
        </Paper>
      )}
    </Box>
  )
}
