try {
    $raw = [System.Console]::In.ReadToEnd()
    $event = $raw | ConvertFrom-Json
    $file = $event.tool_input.file_path
} catch {
    exit 0
}

if (-not $file -or $file -notmatch '\.py$' -or $file -match '[/\\]migrations[/\\]') {
    exit 0
}

$issues = @()

$lintOut = uv run ruff check $file
if ($LASTEXITCODE -ne 0) { $issues += $lintOut }

$fmtOut = uv run ruff format --check $file
if ($LASTEXITCODE -ne 0) { $issues += $fmtOut }

$typeOut = uv run mypy $file --ignore-missing-imports --no-error-summary
if ($LASTEXITCODE -ne 0) { $issues += $typeOut }

if ($issues.Count -gt 0) {
    $issues | ForEach-Object { [Console]::Error.WriteLine($_) }
    exit 2
}
