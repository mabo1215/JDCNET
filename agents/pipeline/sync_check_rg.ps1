$ErrorActionPreference = "Stop"

$UseRg = [bool](Get-Command rg -ErrorAction SilentlyContinue)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot

$script:failed = 0

function Get-MatchCount {
    param(
        [string]$Pattern,
        [string[]]$Targets
    )

    if ($UseRg) {
        $matches = rg -n --glob '!**/.git/**' $Pattern @Targets 2>$null
        if ($matches) {
            return ($matches | Measure-Object).Count
        }

        return 0
    }

    $count = 0
    foreach ($target in $Targets) {
        if (-not (Test-Path $target)) {
            continue
        }

        $results = Select-String -Path $target -Pattern $Pattern -AllMatches -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($results) {
            foreach ($result in $results) {
                $count += $result.Matches.Count
            }
        }
    }

    return $count
}

function Invoke-RgCheck {
    param(
        [string]$Id,
        [string]$Title,
        [string]$Pattern,
        [string[]]$Targets,
        [int]$MinMatches = 1
    )

    $backend = if ($UseRg) { "rg" } else { "Select-String" }
    Write-Host ""
    Write-Host "[$Id] $Title"
    if ($UseRg) {
        $targetText = ($Targets -join " ")
        Write-Host "CMD: rg -n --glob '!**/.git/**' '$Pattern' $targetText"
    }
    else {
        $targetText = ($Targets -join ", ")
        Write-Host "CMD: Select-String -Pattern '$Pattern' -Path $targetText"
    }

    $matchCount = Get-MatchCount -Pattern $Pattern -Targets $Targets

    if ($matchCount -ge $MinMatches) {
        Write-Host "PASS ($matchCount matches; expected >= $MinMatches)" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL ($matchCount matches; expected >= $MinMatches)" -ForegroundColor Red
        $script:failed++
    }
}

function Invoke-PathCheck {
    param(
        [string]$Id,
        [string]$Title,
        [string[]]$Paths
    )

    Write-Host ""
    Write-Host "[$Id] $Title"

    $missing = @()
    foreach ($p in $Paths) {
        if (-not (Test-Path $p)) {
            $missing += $p
        }
    }

    if ($missing.Count -eq 0) {
        Write-Host "PASS (all paths exist)" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL (missing paths):" -ForegroundColor Red
        $missing | ForEach-Object { Write-Host "  - $_" }
        $script:failed++
    }
}

# 1) Version headers local vs upstream are present.
Invoke-RgCheck -Id "1" -Title "SKILL metadata headers present (local + upstream)" `
    -Pattern "^(  version:|  last_updated:)" `
    -Targets @(
        "agents/pipeline/deep-research/SKILL.md",
        "agents/pipeline/academic-paper/SKILL.md",
        "agents/pipeline/academic-paper-reviewer/SKILL.md",
        "agents/pipeline/academic-pipeline/SKILL.md",
        "docs/academic-research-skills/deep-research/SKILL.md",
        "docs/academic-research-skills/academic-paper/SKILL.md",
        "docs/academic-research-skills/academic-paper-reviewer/SKILL.md",
        "docs/academic-research-skills/academic-pipeline/SKILL.md"
    ) -MinMatches 16

# 2) PIPELINE_RULES index entries include all newly synced protocol anchors.
Invoke-RgCheck -Id "2" -Title "PIPELINE_RULES includes new protocol anchors" `
    -Pattern "collaboration_depth_agent|passport_as_reset_boundary|literature_corpus_consumers|sprint_contract_protocol|sprint_contract\\.schema\\.json|collaboration_depth_rubric" `
    -Targets @("agents/pipeline/PIPELINE_RULES.md") -MinMatches 6

# 3) Collaboration observer is wired in both index/specialization and files exist.
Invoke-RgCheck -Id "3a" -Title "Observer wiring appears in specialization/index" `
    -Pattern "collaboration_depth_agent|advisory|永不阻断|Agent Team \(4 Agents\)" `
    -Targets @(
        "agents/pipeline/academic-pipeline.md",
        "agents/pipeline/academic-pipeline/SKILL.md",
        "agents/pipeline/PIPELINE_RULES.md"
    ) -MinMatches 4
Invoke-PathCheck -Id "3b" -Title "Observer files exist" -Paths @(
    "agents/pipeline/academic-pipeline/agents/collaboration_depth_agent.md",
    "agents/pipeline/shared/collaboration_depth_rubric.md"
)

# 4) Resume chain is present from entrypoint to protocol reference.
Invoke-RgCheck -Id "4a" -Title "resume_from_passport appears in entry + specialization" `
    -Pattern "resume_from_passport" `
    -Targets @(
        "agents/AGENTS.md",
        "agents/pipeline/academic-pipeline.md",
        "agents/pipeline/PIPELINE_RULES.md"
    ) -MinMatches 4
Invoke-PathCheck -Id "4b" -Title "resume protocol file exists" -Paths @(
    "agents/pipeline/academic-pipeline/references/passport_as_reset_boundary.md"
)

# 5) literature_corpus consumer chain is present.
Invoke-RgCheck -Id "5a" -Title "literature_corpus chain appears in rules/specialization" `
    -Pattern "literature_corpus|CORPUS PARSE FAILURE|corpus" `
    -Targets @(
        "agents/pipeline/academic-pipeline.md",
        "agents/pipeline/PIPELINE_RULES.md"
    ) -MinMatches 4
Invoke-PathCheck -Id "5b" -Title "corpus consumer protocol file exists" -Paths @(
    "agents/pipeline/academic-pipeline/references/literature_corpus_consumers.md"
)

# 6) Reviewer sprint contract pair is present.
Invoke-RgCheck -Id "6a" -Title "reviewer sprint contract references present" `
    -Pattern "sprint_contract|hard gate|Schema 13|sprint_contract_protocol" `
    -Targets @(
        "agents/pipeline/academic-paper-reviewer/SKILL.md",
        "agents/pipeline/academic-paper-reviewer.md",
        "agents/pipeline/PIPELINE_RULES.md"
    ) -MinMatches 4
Invoke-PathCheck -Id "6b" -Title "reviewer contract files exist" -Paths @(
    "agents/pipeline/academic-paper-reviewer/references/sprint_contract_protocol.md",
    "agents/pipeline/shared/sprint_contract.schema.json"
)

# 7) Domain overlays remain present (do not get overwritten by pure upstream copies).
Invoke-RgCheck -Id "7" -Title "domain overlays still carry LLM/VLM/ML/CV specialization markers" `
    -Pattern "LLM|VLM|ML|CV|领域特化" `
    -Targets @(
        "agents/pipeline/deep-research.md",
        "agents/pipeline/academic-paper.md",
        "agents/pipeline/academic-paper-reviewer.md",
        "agents/pipeline/academic-pipeline.md"
    ) -MinMatches 8

Write-Host ""
if ($failed -eq 0) {
    Write-Host "All checks passed." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "$script:failed check group(s) failed." -ForegroundColor Red
    exit 2
}
