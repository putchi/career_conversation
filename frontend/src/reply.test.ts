import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Hoist mock so reply.ts import of hammerjs gets the mock
vi.mock('hammerjs', () => {
  const recognizeWith = vi.fn()
  const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
  const Swipe = vi.fn(function () { return { recognizeWith } })
  const Press = vi.fn(function () { return { recognizeWith } })
  const Pan = vi.fn(function () { return { recognizeWith } })
  return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
})

// ── null-guard branches: called before initReply ──────────────

describe('null guards (before initReply)', () => {
  let mod: typeof import('./reply.js')

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const recognizeWith = vi.fn()
      const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
      const Swipe = vi.fn(function () { return { recognizeWith } })
      const Press = vi.fn(function () { return { recognizeWith } })
      const Pan = vi.fn(function () { return { recognizeWith } })
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    // NOTE: initReply is intentionally NOT called here so bannerEl stays null
  })

  it('clearReply does not throw when bannerEl is null', () => {
    expect(() => mod.clearReply()).not.toThrow()
  })

  it('showReplyBanner returns early when bannerEl is null', () => {
    expect(() => mod.showReplyBanner('user', 'test')).not.toThrow()
    expect(mod.getReplyPrefix()).toBeNull()
  })
})

// ── getReplyPrefix / clearReply / showReplyBanner (no DOM) ────

describe('getReplyPrefix / clearReply', () => {
  let mod: typeof import('./reply.js')
  let inputArea: HTMLElement

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const recognizeWith = vi.fn()
      const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
      const Swipe = vi.fn(function () { return { recognizeWith } })
      const Press = vi.fn(function () { return { recognizeWith } })
      const Pan = vi.fn(function () { return { recognizeWith } })
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('returns null when no reply is active', () => {
    expect(mod.getReplyPrefix()).toBeNull()
  })

  it('returns correct prefix after showReplyBanner', () => {
    mod.showReplyBanner('assistant', 'Hello world')
    expect(mod.getReplyPrefix()).toBe('[Replying to "Hello world"]\n\n')
  })

  it('truncates content at 80 chars', () => {
    const long = 'a'.repeat(100)
    mod.showReplyBanner('user', long)
    expect(mod.getReplyPrefix()).toBe(`[Replying to "${'a'.repeat(80)}…"]\n\n`)
  })

  it('returns null after clearReply', () => {
    mod.showReplyBanner('user', 'test')
    mod.clearReply()
    expect(mod.getReplyPrefix()).toBeNull()
  })
})

// ── initReply / banner DOM ────────────────────────────────────

describe('initReply / banner DOM', () => {
  let mod: typeof import('./reply.js')
  let inputArea: HTMLElement

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const recognizeWith = vi.fn()
      const Manager = vi.fn(() => ({ add: vi.fn(), on: vi.fn() }))
      const Swipe = vi.fn(function () { return { recognizeWith } })
      const Press = vi.fn(function () { return { recognizeWith } })
      const Pan = vi.fn(function () { return { recognizeWith } })
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('injects #reply-banner into inputArea', () => {
    expect(inputArea.querySelector('#reply-banner')).not.toBeNull()
  })

  it('banner is hidden by default', () => {
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })

  it('showReplyBanner makes banner visible', () => {
    mod.showReplyBanner('assistant', 'Hello')
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(false)
  })

  it('showReplyBanner sets role text to "Digital Twin" for assistant', () => {
    mod.showReplyBanner('assistant', 'Hello')
    expect(inputArea.querySelector('.reply-banner-role')!.textContent).toBe('Digital Twin')
  })

  it('showReplyBanner sets role text to "You" for user', () => {
    mod.showReplyBanner('user', 'Hello')
    expect(inputArea.querySelector('.reply-banner-role')!.textContent).toBe('You')
  })

  it('showReplyBanner sets snippet text', () => {
    mod.showReplyBanner('assistant', 'Hello world')
    expect(inputArea.querySelector('.reply-banner-text')!.textContent).toBe('Hello world')
  })

  it('banner bar has --user class when quoting user', () => {
    mod.showReplyBanner('user', 'hi')
    expect(inputArea.querySelector('.reply-banner-bar')!.classList.contains('reply-banner-bar--user')).toBe(true)
  })

  it('banner bar has --assistant class when quoting assistant', () => {
    mod.showReplyBanner('assistant', 'hi')
    expect(inputArea.querySelector('.reply-banner-bar')!.classList.contains('reply-banner-bar--assistant')).toBe(true)
  })

  it('showReplyBanner sets --user color class on role element', () => {
    mod.showReplyBanner('user', 'Hello')
    const roleEl = inputArea.querySelector('.reply-banner-role')!
    expect(roleEl.classList.contains('reply-banner-role--user')).toBe(true)
    expect(roleEl.classList.contains('reply-banner-role--assistant')).toBe(false)
  })

  it('showReplyBanner sets --assistant color class on role element', () => {
    mod.showReplyBanner('assistant', 'Hello')
    const roleEl = inputArea.querySelector('.reply-banner-role')!
    expect(roleEl.classList.contains('reply-banner-role--assistant')).toBe(true)
    expect(roleEl.classList.contains('reply-banner-role--user')).toBe(false)
  })

  it('clearReply hides the banner', () => {
    mod.showReplyBanner('user', 'test')
    mod.clearReply()
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })

  it('getActiveReply returns null when no reply is active', () => {
    expect(mod.getActiveReply()).toBeNull()
  })

  it('getActiveReply returns the active reply context after showReplyBanner', () => {
    mod.showReplyBanner('assistant', 'Hello world')
    expect(mod.getActiveReply()).toEqual({ role: 'assistant', content: 'Hello world' })
  })

  it('close button click hides the banner', () => {
    mod.showReplyBanner('user', 'test')
    ;(inputArea.querySelector('.reply-banner-close') as HTMLButtonElement).click()
    expect((inputArea.querySelector('#reply-banner') as HTMLElement).hidden).toBe(true)
  })
})

// ── attachReplyGestures ───────────────────────────────────────

describe('attachReplyGestures', () => {
  let mod: typeof import('./reply.js')

  beforeEach(async () => {
    vi.resetModules()
    vi.mock('hammerjs', () => {
      const recognizeWith = vi.fn()
      const Manager = vi.fn(function () { return { add: vi.fn(), on: vi.fn() } })
      const Swipe = vi.fn(function () { return { recognizeWith } })
      const Press = vi.fn(function () { return { recognizeWith } })
      const Pan = vi.fn(function () { return { recognizeWith } })
      return { default: { Manager, Swipe, Press, Pan, DIRECTION_RIGHT: 4 } }
    })
    mod = await import('./reply.js')
    const inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('injects .reply-btn into the message element', () => {
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'assistant', 'Hello')
    expect(msgEl.querySelector('.reply-btn')).not.toBeNull()
  })

  it('clicking .reply-btn activates reply state', () => {
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'assistant', 'Hello world')
    ;(msgEl.querySelector('.reply-btn') as HTMLButtonElement).click()
    expect(mod.getReplyPrefix()).toContain('Hello world')
  })

  it('constructs Hammer.Manager on the message element with pan-y touch action', async () => {
    const { default: Hammer } = await import('hammerjs')
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'user', 'test')
    expect(Hammer.Manager).toHaveBeenCalledWith(msgEl, expect.objectContaining({ touchAction: 'pan-y' }))
  })

  it('registers swiperight and press event handler on Hammer', async () => {
    const { default: Hammer } = await import('hammerjs')
    const mockOn = vi.fn()
    vi.mocked(Hammer.Manager).mockImplementation(function () { return { add: vi.fn(), on: mockOn } } as any)
    const msgEl = document.createElement('div')
    mod.attachReplyGestures(msgEl, 'user', 'test')
    expect(mockOn).toHaveBeenCalledWith('swiperight press', expect.any(Function))
  })

  it('swiperight press handler calls showReplyBanner and vibrate when supported', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    Object.defineProperty(navigator, 'vibrate', { value: vi.fn(), configurable: true, writable: true })
    const msgEl = document.createElement('div')
    const inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
    mod.attachReplyGestures(msgEl, 'assistant', 'Hello swipe')
    handlers['swiperight press']()
    expect(navigator.vibrate).toHaveBeenCalledWith(50)
    expect(mod.getReplyPrefix()).toContain('Hello swipe')
  })

  it('swiperight press handler calls showReplyBanner even without vibrate support', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    const vibrateDescriptor = Object.getOwnPropertyDescriptor(navigator, 'vibrate')
    if (vibrateDescriptor) {
      // Temporarily remove vibrate so 'vibrate' in navigator is false
      delete (navigator as any).vibrate
    }
    const msgEl = document.createElement('div')
    const inputArea = document.createElement('div')
    document.body.appendChild(inputArea)
    mod.initReply(inputArea)
    mod.attachReplyGestures(msgEl, 'user', 'No vibrate')
    handlers['swiperight press']()
    expect(mod.getReplyPrefix()).toContain('No vibrate')
    if (vibrateDescriptor) {
      Object.defineProperty(navigator, 'vibrate', vibrateDescriptor)
    }
  })

  it('panright handler translates bubble by capped deltaX', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    const msgEl = document.createElement('div')
    const bubble = document.createElement('div')
    bubble.className = 'message-bubble'
    msgEl.appendChild(bubble)
    mod.attachReplyGestures(msgEl, 'user', 'pan test')
    handlers['panright']({ deltaX: 20 } as HammerInput)
    expect(bubble.style.transform).toBe('translateX(20px)')
    handlers['panright']({ deltaX: 100 } as HammerInput)
    expect(bubble.style.transform).toBe('translateX(40px)')
  })

  it('panright handler does nothing when bubble is absent', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    const msgEl = document.createElement('div') // no .message-bubble child
    mod.attachReplyGestures(msgEl, 'user', 'no bubble')
    expect(() => handlers['panright']({ deltaX: 30 } as HammerInput)).not.toThrow()
  })

  it('panend pancancel handler resets bubble transform', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    const msgEl = document.createElement('div')
    const bubble = document.createElement('div')
    bubble.className = 'message-bubble'
    bubble.style.transform = 'translateX(30px)'
    msgEl.appendChild(bubble)
    mod.attachReplyGestures(msgEl, 'user', 'pan end test')
    handlers['panend pancancel']()
    expect(bubble.style.transform).toBe('')
  })

  it('panend pancancel handler does nothing when bubble is absent', async () => {
    const { default: Hammer } = await import('hammerjs')
    const handlers: Record<string, Function> = {}
    vi.mocked(Hammer.Manager).mockImplementation(function () {
      return { add: vi.fn(), on: (ev: string, fn: Function) => { handlers[ev] = fn } }
    } as any)
    const msgEl = document.createElement('div') // no .message-bubble child
    mod.attachReplyGestures(msgEl, 'user', 'no bubble end')
    expect(() => handlers['panend pancancel']()).not.toThrow()
  })
})
