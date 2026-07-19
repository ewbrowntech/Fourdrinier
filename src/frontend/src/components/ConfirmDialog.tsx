import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface ConfirmDialogProps {
  title: string
  children: ReactNode
  confirmLabel: string
  confirmingLabel?: string
  confirming?: boolean
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}

function focusableIn(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  )
}

/**
 * Modal confirm dialog with initial focus, Tab cycling, Escape to dismiss,
 * focus restore on close, and `inert` on `#root` so chrome behind the overlay
 * is not reachable.
 */
function ConfirmDialog({
  title,
  children,
  confirmLabel,
  confirmingLabel,
  confirming = false,
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDivElement>(null)
  const cancelRef = useRef<HTMLButtonElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  const confirmingRef = useRef(confirming)
  const onCancelRef = useRef(onCancel)

  confirmingRef.current = confirming
  onCancelRef.current = onCancel

  useEffect(() => {
    previouslyFocused.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null

    const root = document.getElementById('root')
    root?.setAttribute('inert', '')

    const focusFrame = requestAnimationFrame(() => {
      cancelRef.current?.focus()
    })

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        if (!confirmingRef.current) {
          event.preventDefault()
          onCancelRef.current()
        }
        return
      }

      if (event.key !== 'Tab') return

      const dialog = dialogRef.current
      if (!dialog) return

      const focusable = focusableIn(dialog)
      if (focusable.length === 0) {
        event.preventDefault()
        dialog.focus()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (event.shiftKey) {
        if (active === first || !dialog.contains(active)) {
          event.preventDefault()
          last.focus()
        }
      } else if (active === last || !dialog.contains(active)) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      cancelAnimationFrame(focusFrame)
      window.removeEventListener('keydown', onKeyDown)
      root?.removeAttribute('inert')
      previouslyFocused.current?.focus()
    }
  }, [])

  // While the action runs both buttons are disabled; park focus on the dialog
  // so it isn't dropped onto the inert page behind the overlay.
  useEffect(() => {
    if (confirming) dialogRef.current?.focus()
  }, [confirming])

  return createPortal(
    <div
      className="modal-overlay"
      role="presentation"
      onClick={() => {
        if (!confirming) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId}>{title}</h2>
        {children}
        <div className="form-actions">
          <button
            ref={cancelRef}
            type="button"
            className="btn"
            onClick={onCancel}
            disabled={confirming}
          >
            Cancel
          </button>
          <button
            type="button"
            className={danger ? 'btn danger' : 'btn primary'}
            onClick={onConfirm}
            disabled={confirming}
          >
            {confirming && confirmingLabel ? confirmingLabel : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default ConfirmDialog
