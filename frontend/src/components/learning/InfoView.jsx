import { Alert, Image, List, Stack, Text, Title } from '@mantine/core'
import { IconAlertTriangle, IconBulb, IconInfoCircle } from '@tabler/icons-react'

/**
 * Data-driven info rendering for a learning unit.
 *
 * Expects an array of typed blocks (`blocks`). The format is deliberately
 * schema-based (no HTML/Markdown): safe by design and reusable 1:1 as a
 * JSON schema for AI-generated content (daily challenges).
 *
 * Supported block types:
 *   { type: 'heading',   text }
 *   { type: 'paragraph', text }
 *   { type: 'list',      ordered?, items: [] }
 *   { type: 'callout',   variant: 'tip'|'info'|'warning', title?, text }
 *   { type: 'image',     url, alt, caption? }
 *
 * Unknown types are ignored (forward-compatible).
 */

const CALLOUT_CONFIG = {
  tip: { color: 'accent', icon: IconBulb },
  info: { color: 'brand', icon: IconInfoCircle },
  warning: { color: 'orange', icon: IconAlertTriangle },
}

function Block({ block }) {
  switch (block.type) {
    case 'heading':
      return (
        <Title order={3} fz={{ base: 20, md: 22 }} c="secondary.9">
          {block.text}
        </Title>
      )
    case 'paragraph':
      return (
        <Text fz={{ base: 15, md: 16 }} c="secondary.9" lh={1.65}>
          {block.text}
        </Text>
      )
    case 'list':
      return (
        <List
          type={block.ordered ? 'ordered' : 'unordered'}
          spacing="xs"
          c="secondary.9"
          fz={{ base: 15, md: 16 }}
        >
          {(block.items || []).map((item, i) => (
            <List.Item key={i}>{item}</List.Item>
          ))}
        </List>
      )
    case 'callout': {
      const cfg = CALLOUT_CONFIG[block.variant] || CALLOUT_CONFIG.info
      const Icon = cfg.icon
      return (
        <Alert
          color={cfg.color}
          variant="light"
          radius="md"
          icon={<Icon size={18} />}
          title={block.title}
        >
          {block.text}
        </Alert>
      )
    }
    case 'image':
      return (
        <Stack gap={6}>
          <Image src={block.url} alt={block.alt || ''} radius="md" />
          {block.caption && (
            <Text fz="sm" c="dimmed" ta="center">
              {block.caption}
            </Text>
          )}
        </Stack>
      )
    default:
      return null
  }
}

export default function InfoView({ blocks = [] }) {
  return (
    <Stack gap="md">
      {blocks.map((block, i) => (
        <Block key={i} block={block} />
      ))}
    </Stack>
  )
}
