# sync-pull.ps1 —— 开工时跑：git pull，再把仓库里的学习状态铺回本机工作区 + Claude 记忆目录
#
# 用法（双击 sync-pull.bat 即可；或命令行）：
#   powershell -ExecutionPolicy Bypass -File scripts\sync-pull.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\sync-pull.ps1 -NoGit   # 不 pull，只把仓库现有内容铺回本机
#
# 拷贝规则和 push 一样："新者为准、不删除"。所以顺序一定是：开工先 pull，收工再 push。

param([switch]$NoGit)

. "$PSScriptRoot\common.ps1"
Assert-Git

Write-Host "工作区   : $Workspace"
Write-Host "同步仓库 : $RepoRoot"
Write-Host "记忆目录 : $MemoryDir"

if (-not $NoGit) {
  Write-Section '0/4 git pull'
  Push-Location $RepoRoot
  try {
    & git pull --rebase --autostash
    if ($LASTEXITCODE -ne 0) { throw 'git pull 失败（网络？或本地有冲突：git status 看一下）' }
  } finally { Pop-Location }
}

# 1. Claude 记忆：仓库 memory/ -> ~/.claude/projects/<slug>/memory/
Write-Section '1/4 memory/ -> Claude 记忆目录'
if (-not (Test-Path $MemoryDir)) { New-Item -ItemType Directory -Force -Path $MemoryDir | Out-Null; Write-Host "  [新建] $MemoryDir" }
Invoke-Robocopy -Src (Join-Path $RepoRoot 'memory') -Dst $MemoryDir -Masks @('*.md')

# 2. 笔记 / 简历 / 练习项目
Write-Section '2/4 笔记、简历、练习项目 -> 工作区'
foreach ($p in $DirPairs) {
  Invoke-Robocopy -Src (Join-Path $RepoRoot $p.repo) -Dst (Join-Path $Workspace $p.ws)
}

# 3. 课件文本（push 时已过滤，这里原样铺回；pushOnly 的条目是上一条的子目录，不用再拷）
Write-Section '3/4 课件 -> 工作区'
foreach ($p in $CoursePairs) {
  if ($p.pushOnly) { continue }
  Invoke-Robocopy -Src (Join-Path $RepoRoot $p.repo) -Dst (Join-Path $Workspace $p.ws)
}

# 4. 单文件
Write-Section '4/4 计划、工作区配置、早期笔记 -> 工作区'
foreach ($p in $FilePairs) {
  Copy-FileNewer -Src (Join-Path $RepoRoot $p.repo) -Dst (Join-Path $Workspace $p.ws)
}

Write-Host ""
Write-Host "完成。现在可以在 $Workspace 下启动 Claude Code 开始学习。" -ForegroundColor Green
Write-Host "课程代码仓库（zhifu-platform / harness_zbt 等）不在这里同步；首次安装请跑 setup-company.bat。"
