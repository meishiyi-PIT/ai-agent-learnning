# setup-company.ps1 —— 新电脑（公司机）首次安装，只跑一次
#
# 前提：已经把本仓库 clone 到  C:\workspace\ai-agent-learnning
#   mkdir C:\workspace
#   cd C:\workspace
#   git clone https://github.com/meishiyi-PIT/ai-agent-learnning.git
# 然后双击 scripts\setup-company.bat（或命令行跑本文件）。
#
# 它做四件事：
#   1. 把仓库内容铺回 C:\workspace（笔记、课件文本、练习项目、工作区 CLAUDE.md）
#   2. 把 Claude 记忆装到 %USERPROFILE%\.claude\projects\C--workspace\memory\
#   3. 用 repos\*.bundle 还原课程代码仓库（zhifu-platform / harness_zbt / DeepAgent / meishiyi），
#      切到学习用的分支，并把本地未提交的作业改动打回去
#   4. 打印验证步骤

. "$PSScriptRoot\common.ps1"
Assert-Git

Write-Section '环境检查'
Write-Host "工作区   : $Workspace"
Write-Host "同步仓库 : $RepoRoot"
Write-Host "记忆目录 : $MemoryDir"
if ($Workspace -ne 'C:\workspace') {
  Write-Host "  [提醒] 工作区不是 C:\workspace。也能用，但记忆/笔记里写的绝对路径（C:\workspace\...）需要你口头告诉 AI 换成 $Workspace" -ForegroundColor Yellow
}

# 1 + 2：铺回工作区 + 装记忆
& "$PSScriptRoot\sync-pull.ps1" -NoGit

# 3：还原课程代码仓库
Write-Section '还原课程代码仓库（从 repos\*.bundle）'
$reposDir = Join-Path $RepoRoot 'repos'
foreach ($r in $Repos) {
  $dst    = Join-Path $Workspace $r.name
  $bundle = Join-Path $reposDir "$($r.name).bundle"
  if (Test-Path (Join-Path $dst '.git')) { Write-Host "  [已存在] $dst，跳过 clone"; continue }
  if (-not (Test-Path $bundle)) { Write-Host "  [没有 bundle] $bundle，跳过（可改用: git clone $($r.url) $dst）" -ForegroundColor Yellow; continue }

  & git clone -q $bundle $dst
  if ($LASTEXITCODE -ne 0) { throw "clone bundle 失败: $bundle" }
  & git -C $dst checkout -q $r.branch 2>$null
  if ($LASTEXITCODE -ne 0) { & git -C $dst checkout -q -b $r.branch "origin/$($r.branch)" }
  # bundle 里的 origin/* 分支都带着了；把 origin 改回真实地址，方便将来能上网时 git fetch
  & git -C $dst remote set-url origin $r.url
  Write-Host "  [ok] $($r.name) -> $dst (分支 $($r.branch))"

  # 本地未提交改动（作业 / 随堂注释）
  $lc = Join-Path $reposDir "local-changes\$($r.name)"
  if (Test-Path $lc) {
    $patch = Join-Path $lc 'tracked.patch'
    if ((Test-Path $patch) -and ((Get-Item $patch).Length -gt 0)) {
      & git -C $dst apply --3way $patch
      if ($LASTEXITCODE -ne 0) { Write-Host "  [警告] patch 没能完全打上，手动看: $patch" -ForegroundColor Yellow }
      else { Write-Host "  [ok] 已打上未提交改动 tracked.patch" }
    }
    $un = Join-Path $lc 'untracked'
    if (Test-Path $un) {
      & robocopy $un $dst /E /NFL /NDL /NJH /NJS /NP | Out-Null
      if ($LASTEXITCODE -ge 8) { throw "拷贝 untracked 失败: $un" }
      Write-Host "  [ok] 已放回新增文件（untracked）"
    }
  }
}

Write-Section '下一步（手动）'
Write-Host @"
1. 安装 Claude Code（需要 Node.js 18+）：  npm install -g @anthropic-ai/claude-code
   公司网络如装不上，用别的 AI 也行：把  启动提示词.md  整段贴给它，并让它读 memory\MEMORY.md。
2. 验证记忆是否装对：
   cd $Workspace
   claude
   然后发这句话：  读一下你的记忆索引和学习笔记里各计划文件末尾的进度锚点，告诉我现在学到哪、下一步该做什么。
   能答出"智服中台第一课 §5 用 order-list-01 从 accept_message 走执行流程"之类的内容，就说明同步成功。
3. 各项目的 .env（API key）不在仓库里，需要跑代码时按 README.md "密钥" 一节手动新建。
4. 以后每天：开工双击 scripts\sync-pull.bat，收工双击 scripts\sync-push.bat。
"@
