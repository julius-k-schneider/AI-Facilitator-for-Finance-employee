import { Button, Group, Modal, Stack, Text } from '@mantine/core'
import { useTranslation } from 'react-i18next'

/**
 * Confirmation dialog for destructive actions.
 *
 * Replaces window.confirm so that every "are you sure" in the app looks the
 * same, follows the app language, and can be styled. Pass `danger` for actions
 * that delete or reject something.
 */
export default function ConfirmModal({
  opened,
  onClose,
  onConfirm,
  title,
  text,
  hint,
  confirmLabel,
  loading = false,
  danger = true,
}) {
  const { t } = useTranslation()
  return (
    <Modal opened={opened} onClose={onClose} title={title} centered>
      <Stack gap="md">
        <Text c="secondary.9">{text}</Text>
        {hint && <Text fz="sm" c="dimmed">{hint}</Text>}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>{t('common.cancel')}</Button>
          <Button color={danger ? 'red' : 'brand'} loading={loading} onClick={onConfirm}>
            {confirmLabel || t('common.confirm')}
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
