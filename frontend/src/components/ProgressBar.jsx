export default function ProgressBar({ value, label }) {
  const safeValue = Math.max(0, Math.min(value, 100))

  return (
    <div className="progress-bar" aria-label={label}>
      <div className="progress-bar-fill" style={{ width: `${safeValue}%` }} />
    </div>
  )
}
