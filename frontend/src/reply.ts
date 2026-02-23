import Hammer from 'hammerjs'

interface ReplyContext {
  role: 'user' | 'assistant'
  content: string
}

let activeReply: ReplyContext | null = null
let bannerEl: HTMLElement | null = null
let bannerRoleEl: HTMLElement | null = null
let bannerTextEl: HTMLElement | null = null
let bannerBarEl: HTMLElement | null = null

function truncate(text: string): string {
  return text.length > 80 ? text.slice(0, 80) + '…' : text
}

export function getReplyPrefix(): string | null {
  if (!activeReply) return null
  return `[Replying to "${truncate(activeReply.content)}"]\n\n`
}

export function clearReply(): void {
  activeReply = null
  if (bannerEl) bannerEl.hidden = true
}

export function getActiveReply(): { role: 'user' | 'assistant'; content: string } | null {
  return activeReply
}

export function showReplyBanner(role: 'user' | 'assistant', content: string): void {
  if (!bannerEl || !bannerRoleEl || !bannerTextEl || !bannerBarEl) return
  activeReply = { role, content }
  bannerRoleEl.textContent = role === 'user' ? 'You' : 'Digital Twin'
  bannerRoleEl.className = `reply-banner-role reply-banner-role--${role}`
  bannerTextEl.textContent = truncate(content)
  bannerBarEl.className = `reply-banner-bar reply-banner-bar--${role}`
  // Force animation restart even if banner is already visible
  bannerEl.hidden = true
  void bannerEl.offsetWidth  // trigger reflow so animation replays
  bannerEl.hidden = false
}

export function initReply(inputArea: HTMLElement): void {
  bannerEl = document.createElement('div')
  bannerEl.id = 'reply-banner'
  bannerEl.className = 'reply-banner'
  bannerEl.hidden = true

  bannerBarEl = document.createElement('div')
  bannerBarEl.className = 'reply-banner-bar'

  const body = document.createElement('div')
  body.className = 'reply-banner-body'

  bannerRoleEl = document.createElement('span')
  bannerRoleEl.className = 'reply-banner-role'

  bannerTextEl = document.createElement('span')
  bannerTextEl.className = 'reply-banner-text'

  const closeBtn = document.createElement('button')
  closeBtn.className = 'reply-banner-close'
  closeBtn.setAttribute('aria-label', 'Cancel reply')
  closeBtn.textContent = '✕'
  closeBtn.addEventListener('click', clearReply)

  body.append(bannerRoleEl, bannerTextEl)
  bannerEl.append(bannerBarEl, body, closeBtn)
  inputArea.prepend(bannerEl)
}

export function attachReplyGestures(
  msgEl: HTMLElement,
  role: 'user' | 'assistant',
  content: string
): void {
  // Desktop: reply button shown on CSS hover
  const replyBtn = document.createElement('button')
  replyBtn.className = 'reply-btn'
  replyBtn.setAttribute('aria-label', 'Reply')
  replyBtn.textContent = '↩\uFE0E'
  replyBtn.addEventListener('click', () => showReplyBanner(role, content))
  msgEl.appendChild(replyBtn)

  // Mobile: HammerJS swipe-right + long-press
  const mc = new Hammer.Manager(msgEl, { touchAction: 'pan-y' })
  const swipe = new Hammer.Swipe({ direction: Hammer.DIRECTION_RIGHT, threshold: 10, velocity: 0.3 })
  const press = new Hammer.Press({ time: 500 })
  const pan = new Hammer.Pan({ direction: Hammer.DIRECTION_RIGHT, threshold: 10 })
  swipe.recognizeWith(pan)
  pan.recognizeWith(swipe)
  mc.add([swipe, press, pan])

  const bubble = msgEl.querySelector('.message-bubble') as HTMLElement | null

  mc.on('swiperight press', () => {
    if ('vibrate' in navigator) navigator.vibrate(50)
    showReplyBanner(role, content)
  })

  mc.on('panright', (ev: HammerInput) => {
    if (!bubble) return
    bubble.style.transform = `translateX(${Math.min(ev.deltaX, 40)}px)`
  })

  mc.on('panend pancancel', () => {
    if (!bubble) return
    bubble.style.transform = ''
  })
}
