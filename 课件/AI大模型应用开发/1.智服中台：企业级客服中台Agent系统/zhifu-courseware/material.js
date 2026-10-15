;(function () {
CourseMaterialDiagrams.initializeDownloads()
const headings = [...document.querySelectorAll('.article-body h2[id]')]
const headingByHash = new Map(headings.map(heading => [`#${heading.id}`, heading]))
const tocLinks = [...document.querySelectorAll('.desktop-toc a, .material-toc nav a')]
const progress = document.querySelector('.reading-progress span')
const mobileToc = document.querySelector('.mobile-toc.material-toc')
const copyStatus = document.querySelector('.copy-status')
const header = document.querySelector('.site-header')
const buttonTimers = new WeakMap()
let frameScheduled = false
let statusTimer
let navigationVersion = 0

function updateReadingPosition() {
  frameScheduled = false
  const maximumScroll = document.documentElement.scrollHeight - innerHeight
  const percentage = maximumScroll > 0 ? scrollY / maximumScroll * 100 : 100
  progress.style.width = `${Math.min(100, Math.max(0, percentage))}%`
  const threshold = Math.max(150, header.getBoundingClientRect().bottom + 24)
  let selected = headings.findLast(heading => heading.getBoundingClientRect().top <= threshold) || headings[0]
  if (maximumScroll > 0 && scrollY >= maximumScroll - 2) selected = headings.at(-1)
  for (const link of tocLinks) {
    if (selected && link.hash === `#${selected.id}`) link.setAttribute('aria-current', 'location')
    else link.removeAttribute('aria-current')
  }
}

function scheduleReadingPosition() {
  if (frameScheduled) return
  frameScheduled = true
  requestAnimationFrame(updateReadingPosition)
}

function locateHeading(hash, focus = false) {
  const heading = headingByHash.get(hash)
  if (!heading) return
  if (mobileToc) mobileToc.open = false
  // 手机目录收起会改变正文位置，使用收起后的标题坐标完成定位。
  const top = scrollY + heading.getBoundingClientRect().top - header.getBoundingClientRect().height - 30
  scrollTo({ top: Math.max(0, top), behavior: 'instant' })
  if (focus) {
    heading.tabIndex = -1
    heading.focus({ preventScroll: true })
  }
  updateReadingPosition()
}

for (const link of tocLinks) {
  link.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return
    if (!headingByHash.has(link.hash)) return
    event.preventDefault()
    ++navigationVersion
    if (location.hash !== link.hash) history.pushState(null, '', link.hash)
    locateHeading(link.hash, true)
  })
}

addEventListener('scroll', scheduleReadingPosition, { passive: true })
addEventListener('resize', scheduleReadingPosition)
addEventListener('pageshow', scheduleReadingPosition)
addEventListener('hashchange', () => {
  ++navigationVersion
  locateHeading(location.hash)
  scheduleReadingPosition()
})
if (mobileToc) mobileToc.addEventListener('toggle', scheduleReadingPosition)

function notify(message, kind = 'success') {
  clearTimeout(statusTimer)
  copyStatus.dataset.kind = kind
  copyStatus.textContent = message
  statusTimer = setTimeout(() => {
    copyStatus.textContent = ''
    delete copyStatus.dataset.kind
  }, kind === 'error' ? 5000 : 2400)
}

function restoreButton(button, label) {
  clearTimeout(buttonTimers.get(button))
  buttonTimers.set(button, setTimeout(() => {
    button.textContent = label
    buttonTimers.delete(button)
  }, 2400))
}

for (const button of document.querySelectorAll('.copy-code')) {
  const label = button.textContent
  button.addEventListener('click', async () => {
    const code = button.closest('.code-example').querySelector('pre code')
    // textContent保留高亮前的空格、换行和全部可见代码，显示换行不改变复制内容。
    const text = code.textContent
    clearTimeout(buttonTimers.get(button))
    button.disabled = true
    button.textContent = '正在复制…'
    try {
      await CourseMaterialDiagrams.copyText(text)
      button.textContent = '已复制'
      notify('代码已完整复制')
    } catch (error) {
      button.textContent = '复制失败'
      notify('复制失败，请检查浏览器的剪贴板权限后重试。', 'error')
      throw error
    } finally {
      button.disabled = false
      restoreButton(button, label)
    }
  })
}

updateReadingPosition()
const initialHash = location.hash
const initialNavigation = navigationVersion
const figures = [...document.querySelectorAll('figure.diagram:not(.static-diagram)')]
figures.forEach(figure => { figure.querySelector('.diagram-expand').disabled = true })
// 普通脚本已包含图解依赖，按当前页面内容初始化查看器。
const diagramsReady = figures.length || document.querySelector('.static-diagram')
  ? CourseMaterialDiagrams.initializeDiagrams()
  : Promise.resolve()
const recordReadingAction = () => { ++navigationVersion }
const recordReadingKey = event => {
  if (['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' '].includes(event.key)) recordReadingAction()
}
// 图解和字体加载期间保留用户的滚动与导航选择。
addEventListener('wheel', recordReadingAction, { passive: true })
addEventListener('touchstart', recordReadingAction, { passive: true })
addEventListener('pointerdown', recordReadingAction, { passive: true })
addEventListener('keydown', recordReadingKey)
Promise.all([document.fonts.ready, diagramsReady]).then(() => {
  document.documentElement.dataset.diagramsReady = 'true'
  if (navigationVersion === initialNavigation && location.hash === initialHash) locateHeading(initialHash)
  scheduleReadingPosition()
}).finally(() => {
  removeEventListener('wheel', recordReadingAction)
  removeEventListener('touchstart', recordReadingAction)
  removeEventListener('pointerdown', recordReadingAction)
  removeEventListener('keydown', recordReadingKey)
})
})()
