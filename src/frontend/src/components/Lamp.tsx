export type LampState = 'off' | 'testing' | 'ok' | 'fault'

const LAMP_TITLES: Record<LampState, string> = {
  off: 'Connection not verified yet',
  testing: 'Testing connection…',
  ok: 'Connection verified',
  fault: 'Last connection test failed',
}

interface LampProps {
  state: LampState
  delayMs?: number
}

function Lamp({ state, delayMs }: LampProps) {
  return (
    <span
      className={`lamp ${state}`}
      style={delayMs !== undefined ? { animationDelay: `${delayMs}ms` } : undefined}
      role="img"
      aria-label={LAMP_TITLES[state]}
      title={LAMP_TITLES[state]}
    />
  )
}

export default Lamp
