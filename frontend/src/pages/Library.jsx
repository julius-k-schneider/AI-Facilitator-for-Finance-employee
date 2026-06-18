import { IconBooks } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'

export default function Library() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.library.title')}
      description={t('pages.library.description')}
      icon={IconBooks}
    />
  )
}
