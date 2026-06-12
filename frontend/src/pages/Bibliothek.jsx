import { IconBooks } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'

export default function Bibliothek() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.bibliothek.title')}
      description={t('pages.bibliothek.description')}
      icon={IconBooks}
    />
  )
}
