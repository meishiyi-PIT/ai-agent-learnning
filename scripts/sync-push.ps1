# sync-push.ps1 —— 收工时跑：把本机工作区的学习状态拷进仓库，然后 commit + push
#
# 用法（在任一台机器上，双击 sync-push.bat 即可；或命令行）：
#   powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1               # 日常：记忆 + 笔记 + 计划 + 简历 + 练习 + 课件文本
#   powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1 -WithRepos    # 另外刷新课程代码仓库的 bundle 和本地未提交改动（偶尔用）
#   powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1 -NoGit        # 只拷文件不碰 git（自己检查后再提交）
#   powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1 -Message "..." # 自定义提交信息

param(
  [switch]$WithRepos,
  [switch]$NoGit,
  [string]$Message = ''
)

. "$PSScriptRoot\common.ps1"
Assert-Git

Write-Host "工作区   : $Workspace"
Write-Host "同步仓库 : $RepoRoot"
Write-Host "记忆目录 : $MemoryDir"

# 1. Claude 记忆（这是"学到哪 + 怎么教我"的核心，最重要的一步）
Write-Section '1/5 Claude 记忆 -> memory/'
Invoke-Robocopy -Src $MemoryDir -Dst (Join-Path $RepoRoot 'memory') -Masks @('*.md')

# 2. 笔记 / 简历 / 练习项目
Write-Section '2/5 笔记、简历、练习项目'
foreach ($p in $DirPairs) {
  Invoke-Robocopy -Src (Join-Path $Workspace $p.ws) -Dst (Join-Path $RepoRoot $p.repo)
}

# 3. 课件文本
Write-Section '3/5 课件（只带 md / 图 / docx）'
foreach ($p in $CoursePairs) {
  Invoke-Robocopy -Src (Join-Path $Workspace $p.ws) -Dst (Join-Path $RepoRoot $p.repo) -Masks $p.masks -XD $p.xd -XF $p.xf
}

# 4. 单文件
Write-Section '4/5 计划、工作区配置、早期笔记'
foreach ($p in $FilePairs) {
  Copy-FileNewer -Src (Join-Path $Workspace $p.ws) -Dst (Join-Path $RepoRoot $p.repo)
}

# 5. 课程代码仓库（可选）：bundle + 本地未提交的改动
if ($WithRepos) {
  Write-Section '5/5 课程代码仓库 bundle + 本地改动（-WithRepos）'
  $reposDir = Join-Path $RepoRoot 'repos'
  New-Item -ItemType Directory -Force -Path $reposDir | Out-Null
  foreach ($r in $Repos) {
    $src = Join-Path $Workspace $r.name
    if (-not (Test-Path (Join-Path $src '.git'))) { Write-Host "  [跳过] 不是 git 仓库: $src"; continue }

    # 5a. 全部分支/标签打成一个 bundle 文件（公司机器用 git clone xxx.bundle 还原）
    $bundle = Join-Path $reposDir "$($r.name).bundle"
    & git -C $src bundle create $bundle --all 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "git bundle 失败: $src" }
    Write-Host "  [ok] bundle: $bundle ($([math]::Round((Get-Item $bundle).Length/1MB,1)) MB)"

    # 5b. 工作区里尚未提交的改动（作业、随堂注释）：已跟踪文件 -> patch；新文件 -> 原样拷贝
    $lc = Join-Path $reposDir "local-changes\$($r.name)"
    if (Test-Path $lc) { Remove-Item -LiteralPath $lc -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $lc | Out-Null
    $head = (& git -C $src rev-parse HEAD).Trim()
    $br   = (& git -C $src rev-parse --abbrev-ref HEAD).Trim()
    "HEAD=$head`nBRANCH=$br`nDATE=$(Get-Date -Format s)" | Out-File -LiteralPath (Join-Path $lc 'HEAD.txt') -Encoding ascii
    # 用 cmd 重定向写 patch，避免 PowerShell 写出 UTF-16
    & cmd /c "git -C `"$src`" -c core.quotepath=false diff --binary > `"$lc\tracked.patch`""
    $untracked = & git -C $src -c core.quotepath=false ls-files --others --exclude-standard
    $n = 0
    foreach ($rel in $untracked) {
      if ([string]::IsNullOrWhiteSpace($rel)) { continue }
      $from = Join-Path $src $rel
      if (-not (Test-Path -LiteralPath $from)) { continue }
      if ((Get-Item -LiteralPath $from).Length -gt 5MB) { Write-Host "  [跳过>5MB] $rel"; continue }
      $to = Join-Path $lc "untracked\$rel"
      $toDir = Split-Path -Parent $to
      if (-not (Test-Path -LiteralPath $toDir)) { New-Item -ItemType Directory -Force -Path $toDir | Out-Null }
      Copy-Item -LiteralPath $from -Destination $to -Force
      $n++
    }
    Write-Host "  [ok] local-changes: $($r.name) (patch + $n 个新文件)"
  }
} else {
  Write-Section '5/5 课程代码仓库：本次未刷新（需要时加 -WithRepos）'
}

# 安全闸：仓库里绝不能出现真实 .env 或疑似 API key
Write-Section '安全检查'
$envFiles = Get-ChildItem -Path $RepoRoot -Recurse -Force -File -Filter '.env' -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch '\\\.git\\' }
foreach ($f in $envFiles) { Remove-Item -LiteralPath $f.FullName -Force; Write-Host "  [已删除] 混进来的密钥文件: $($f.FullName)" -ForegroundColor Yellow }
$hits = Get-ChildItem -Path (Join-Path $RepoRoot 'practice'), (Join-Path $RepoRoot 'repos\local-changes'), (Join-Path $RepoRoot 'memory'), (Join-Path $RepoRoot '学习笔记') `
          -Recurse -File -Include '*.py','*.md','*.json','*.toml','*.yaml','*.yml','*.txt','*.patch' -ErrorAction SilentlyContinue |
        Select-String -Pattern 'sk-[A-Za-z0-9]{20,}|tvly-[A-Za-z0-9]{10,}|lsv2_[A-Za-z0-9_]{10,}' -List
if ($hits) {
  foreach ($h in $hits) { Write-Host "  [疑似密钥] $($h.Path):$($h.LineNumber)" -ForegroundColor Red }
  throw '发现疑似 API key，已中止，请先清理再推送'
}
Write-Host '  [ok] 未发现密钥'

if ($NoGit) { Write-Host "`n-NoGit：文件已拷好，未提交。自己检查后 git add/commit/push。"; exit 0 }

# git：先提交本机改动，再 rebase 远端（另一台机器可能推过），最后 push
Write-Section 'git 提交并推送'
Push-Location $RepoRoot
try {
  & git add -A
  $staged = & git diff --cached --name-only
  if (-not $staged) {
    Write-Host '  没有新改动，只做一次 pull/push 同步'
  } else {
    if (-not $Message) { $Message = "sync: $(Get-Date -Format 'yyyy-MM-dd HH:mm') from $env:COMPUTERNAME" }
    & git commit -q -m $Message
    if ($LASTEXITCODE -ne 0) { throw 'git commit 失败' }
    Write-Host "  [ok] commit: $Message"
  }
  & git pull --rebase --autostash
  if ($LASTEXITCODE -ne 0) {
    throw "git pull --rebase 失败（两台机器改了同一个文件）。处理：git status 看冲突文件 -> 手动合并 -> git add -> git rebase --continue -> 再跑一次本脚本"
  }
  & git push
  if ($LASTEXITCODE -ne 0) { throw 'git push 失败（网络 / 登录问题？）' }
  Write-Host '  [ok] 已推送到 GitHub' -ForegroundColor Green
} finally { Pop-Location }
