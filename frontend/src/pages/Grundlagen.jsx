import { IconSchool } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'

export default function Grundlagen() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.grundlagen.title')}
      description={t('pages.grundlagen.description')}
      icon={IconSchool}
    />
  )
}
