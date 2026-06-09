import { IconTrophy } from '@tabler/icons-react'
import PageShell from './PageShell'

export default function Leaderboard() {
  return (
    <PageShell
      title="Leaderboard"
      description="Vergleiche deine Punkte mit deinen Kollegen"
      icon={IconTrophy}
    />
  )
}
