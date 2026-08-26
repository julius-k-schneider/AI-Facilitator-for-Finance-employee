import { notifications } from '@mantine/notifications'

// Central place for transient feedback. Inline alerts stay reserved for errors
// that belong next to the form field that caused them; everything a user
// triggers from a button reports back here, so the message is visible no matter
// how far the user has scrolled.
export function notifySuccess(message) {
  notifications.show({ color: 'green', message, autoClose: 4000 })
}

export function notifyError(message) {
  notifications.show({ color: 'red', message, autoClose: 8000 })
}
