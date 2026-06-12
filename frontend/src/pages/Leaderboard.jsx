import { IconTrophy } from '@tabler/icons-react'
import { useTranslation } from 'react-i18next'
import PageShell from './PageShell'

export default function Leaderboard() {
  const { t } = useTranslation()
  return (
    <PageShell
      title={t('pages.leaderboard.title')}
      description={t('pages.leaderboard.description')}
      icon={IconTrophy}
    />
  )
}
