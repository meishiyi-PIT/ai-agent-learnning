# common.ps1 —— 被 sync-push.ps1 / sync-pull.ps1 / setup-company.ps1 点源(dot-source)引用
# 这里只放"配置 + 公共函数"，不执行任何动作。
#
# 约定：本仓库必须 clone 在工作区的下一级，例如 C:\workspace\ai-agent-learnning
#       工作区 = 仓库的上一级目录（自动推导，两台机器都放 C:\workspace 最省事）

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$RepoRoot  = Split-Path -Parent $PSScriptRoot
$Workspace = Split-Path -Parent $RepoRoot
# Claude Code 自动记忆目录的命名规则：把工作区路径里的 ":" 和 "\" 都换成 "-"
#   C:\workspace  ->  C--workspace
$Slug      = ($Workspace -replace '[:\\/]', '-')
$MemoryDir = Join-Path $env:USERPROFILE ".claude\projects\$Slug\memory"

# ---------- 永远不同步的东西 ----------
$ExcludeDirs  = @('.venv', '.git', '__pycache__', '.pytest_cache', 'node_modules', '.idea', '.claude',
                  'data', 'model', 'models', 'report-history', 'evaluate-main', 'chroma_db*')
$ExcludeFiles = @('.env', '.gitignore', '*.pyc', '*.pth', '*.bin', '*.safetensors', '*.ckpt',
                  '*.zip', '*.tar.gz', '*.tgz', '*.gz', '*.mp4', '*.sz')
# 注：子项目自带的 .gitignore 不拷（否则它会把 dist/ 之类的练习脚本挡掉），密钥/venv 由仓库根 .gitignore 统一挡

# ---------- 整目录同步（工作区相对路径 <-> 仓库相对路径） ----------
$DirPairs = @(
  @{ ws = '学习笔记';                   repo = '学习笔记' },
  @{ ws = '画图';                       repo = '画图' },
  @{ ws = 'resume-refs';                repo = 'resume-refs' },
  @{ ws = 'python-for-agents';          repo = 'practice\python-for-agents' },
  @{ ws = 'fastapi-practice';           repo = 'practice\fastapi-practice' },
  @{ ws = 'DeepAgent-novapay-practice'; repo = 'practice\DeepAgent-novapay-practice' },
  @{ ws = 'nlp-practice';               repo = 'practice\nlp-practice' },
  @{ ws = 'tools';                      repo = 'practice\tools' },
  @{ ws = 'deepLearning';               repo = 'practice\deepLearning' }
)

# ---------- 课件：只同步文本类文件（md/图/docx），视频 .sz/.mp4 和 PDF 不进仓库 ----------
$CourseMasks = @('*.md', '*.png', '*.jpg', '*.jpeg', '*.txt', '*.docx', '*.json', '*.yml', '*.yaml')
$CoursePairs = @(
  @{ ws = 'AI大模型应用开发';     repo = '课件\AI大模型应用开发';
     masks = $CourseMasks; xd = @('zhifu-courseware', 'SZPlayer*'); xf = @('*(1).*'); pushOnly = $false },
  @{ ws = 'AI大模型应用开发课件'; repo = '课件\AI大模型应用开发课件';
     masks = $CourseMasks; xd = @('SZPlayer*');                     xf = @('*(1).*'); pushOnly = $false },
  # 智服中台网页课件：整套带走（课程正文 lesson-01~06 的 md/html + 图），只去掉 64MB 的源码快照和 24MB 的下载包
  @{ ws = 'AI大模型应用开发\1.智服中台：企业级客服中台Agent系统\zhifu-courseware';
     repo = '课件\AI大模型应用开发\1.智服中台：企业级客服中台Agent系统\zhifu-courseware';
     masks = @('*.*'); xd = @('code', 'downloads'); xf = @(); pushOnly = $true }
)

# ---------- 单文件同步 ----------
$FilePairs = @(
  @{ ws = '学习计划-冲刺9.12.md';         repo = '学习计划-冲刺9.12.md' },
  @{ ws = 'CLAUDE.md';                    repo = 'workspace-config\CLAUDE.md' },
  @{ ws = 'AGENTS.md';                    repo = 'workspace-config\AGENTS.md' },
  @{ ws = '.claude\settings.local.json';  repo = 'workspace-config\.claude\settings.local.json' },
  @{ ws = 'a2a 学习.md';                  repo = '早期笔记\a2a 学习.md' },
  @{ ws = 'agentic_rag_project.md';       repo = '早期笔记\agentic_rag_project.md' },
  @{ ws = 'deepagents 学习.md';           repo = '早期笔记\deepagents 学习.md' },
  @{ ws = 'langgraph_course.md';          repo = '早期笔记\langgraph_course.md' },
  @{ ws = 'multi-agent 学习.md';          repo = '早期笔记\multi-agent 学习.md' },
  @{ ws = 'rag 学习.md';                  repo = '早期笔记\rag 学习.md' },
  @{ ws = '神经网络学习.md';              repo = '早期笔记\神经网络学习.md' }
)

# ---------- 课程代码仓库：以 git bundle 形式带走（公司网络可能访问不了课程 GitLab） ----------
$Repos = @(
  @{ name = 'zhifu-platform'; url = 'https://git.miaoatech.cn/liugang/zhifu-platform.git';   branch = 'course/09-course-delivery' },
  @{ name = 'harness_zbt';    url = 'https://git.miaoatech.cn/yangxiaolong/harness_zbt.git'; branch = 'phaseThree' },
  @{ name = 'DeepAgent';      url = 'https://git.miaoatech.cn/yangxiaolong/DeepAgent.git';   branch = 'master' },
  @{ name = 'meishiyi';       url = 'https://git.miaoatech.cn/meishiyi/meishiyi.git';        branch = 'master' }
)

# ---------- 公共函数 ----------

# robocopy 包装：/E 递归、/XO 只拷"源比目标新"的文件（两边都不删除，新者为准）
function Invoke-Robocopy {
  param(
    [string]$Src, [string]$Dst,
    [string[]]$Masks = @('*.*'),
    [string[]]$XD = @(), [string[]]$XF = @()
  )
  if (-not (Test-Path $Src)) { Write-Host "  [跳过] 源不存在: $Src"; return }
  $rcArgs = @($Src, $Dst) + $Masks + @('/E', '/XO', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:2', '/W:1')
  $xdAll = $ExcludeDirs + $XD
  $xfAll = $ExcludeFiles + $XF
  if ($xdAll.Count -gt 0) { $rcArgs += '/XD'; $rcArgs += $xdAll }
  if ($xfAll.Count -gt 0) { $rcArgs += '/XF'; $rcArgs += $xfAll }
  & robocopy @rcArgs | Out-Null
  $code = $LASTEXITCODE
  if ($code -ge 8) { throw "robocopy 失败(退出码 $code): $Src -> $Dst" }
  Write-Host "  [ok] $Src -> $Dst"
}

# 单文件：目标不存在或源更新才拷
function Copy-FileNewer {
  param([string]$Src, [string]$Dst)
  if (-not (Test-Path $Src)) { Write-Host "  [跳过] 源不存在: $Src"; return }
  $dir = Split-Path -Parent $Dst
  if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  if ((Test-Path $Dst) -and ((Get-Item $Dst).LastWriteTime -ge (Get-Item $Src).LastWriteTime)) { return }
  Copy-Item -LiteralPath $Src -Destination $Dst -Force
  Write-Host "  [ok] $Src -> $Dst"
}

function Assert-Git {
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw '没找到 git，请先安装 Git for Windows: https://git-scm.com/download/win' }
}

function Write-Section($text) { Write-Host ""; Write-Host "==== $text ====" -ForegroundColor Cyan }
