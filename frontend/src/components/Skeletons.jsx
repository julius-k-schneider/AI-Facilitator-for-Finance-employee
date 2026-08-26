import { Group, Paper, Skeleton, SimpleGrid, Stack } from '@mantine/core'

// One loading vocabulary for the whole app: a placeholder shaped like the
// content that is about to arrive, instead of a bare "loading" line on one page
// and a spinner on the next.

export function CardGridSkeleton({ count = 2, cols = { base: 1, md: 2 } }) {
  return (
    <SimpleGrid cols={cols} spacing="lg">
      {Array.from({ length: count }, (_, index) => (
        <Paper key={index} withBorder radius="lg" p="xl" bg="white">
          <Stack gap="lg">
            <Group justify="space-between">
              <Skeleton height={48} width={48} radius="md" />
              <Skeleton height={20} width={90} radius="xl" />
            </Group>
            <Stack gap={8}>
              <Skeleton height={18} width="70%" radius="sm" />
              <Skeleton height={12} radius="sm" />
              <Skeleton height={12} width="55%" radius="sm" />
            </Stack>
            <Skeleton height={36} radius="md" />
          </Stack>
        </Paper>
      ))}
    </SimpleGrid>
  )
}

export function RowsSkeleton({ count = 4 }) {
  return (
    <Stack gap="sm">
      {Array.from({ length: count }, (_, index) => (
        <Paper key={index} withBorder radius="md" p="md" bg="white">
          <Group gap="md" wrap="nowrap">
            <Skeleton height={40} circle />
            <Stack gap={7} style={{ flex: 1 }}>
              <Skeleton height={13} width="35%" radius="sm" />
              <Skeleton height={11} width="20%" radius="sm" />
            </Stack>
            <Skeleton height={24} width={70} radius="xl" />
          </Group>
        </Paper>
      ))}
    </Stack>
  )
}

export function StatValueSkeleton() {
  return <Skeleton height={30} width={64} radius="sm" mt={4} />
}
