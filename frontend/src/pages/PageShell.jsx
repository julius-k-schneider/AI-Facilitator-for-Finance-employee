import { Box, Paper, Stack, Text, ThemeIcon, Title } from '@mantine/core'
import { useTranslation } from 'react-i18next'

export default function PageShell({ title, description, icon: Icon, children }) {
  const { t } = useTranslation()
  return (
    <Box px={{ base: 'lg', md: 40 }} py={{ base: 28, md: 40 }} maw={1180}>
      <Stack gap={6} mb="xl">
        <Title order={1} fz={{ base: 28, md: 34 }} c="secondary.9">
          {title}
        </Title>
        {description && (
          <Text fz="lg" c="dimmed" maw={620}>
            {description}
          </Text>
        )}
      </Stack>

      {children || (
        <Paper
          withBorder
          radius="lg"
          p={{ base: 'xl', md: 56 }}
          style={{ borderStyle: 'dashed', borderColor: 'var(--line)', background: '#fff' }}
        >
          <Stack align="center" gap="md" py="lg">
            {Icon && (
              <ThemeIcon
                size={64}
                radius="xl"
                variant="light"
                color="brand"
                style={{ background: 'var(--mantine-color-brand-0)' }}
              >
                <Icon size={30} stroke={1.6} />
              </ThemeIcon>
            )}
            <Stack align="center" gap={4}>
              <Text fz="lg" fw={600} c="secondary.9">
                {t('pages.comingSoon')}
              </Text>
              <Text c="dimmed" ta="center" maw={420}>
                {t('pages.comingSoonText')}
              </Text>
            </Stack>
          </Stack>
        </Paper>
      )}
    </Box>
  )
}
