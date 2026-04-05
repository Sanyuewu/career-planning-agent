import DOMPurify from 'dompurify'

const ALLOWED_TAGS = ['b', 'i', 'u', 'strong', 'em', 'br', 'p', 'span', 'div']
const ALLOWED_ATTR = ['class', 'style']

export function sanitizeHtml(dirty: string): string {
  if (!dirty) return ''
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: false,
  })
}

export function sanitizeText(text: string): string {
  if (!text) return ''
  return DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
}

export function escapeHtml(text: string): string {
  if (!text) return ''
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}
