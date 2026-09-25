# Uploads dist\Holos-Setup-<version>.exe to GitHub Releases of canadianproducer/holos.
# Uses the GitHub login that Git already has (Git Credential Manager) - no extra tokens to create.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Start-Transcript -Path ".build\upload.log" -Force | Out-Null
trap { Write-Host "ERROR: $_"; Write-Host $_.ScriptStackTrace; Stop-Transcript | Out-Null; exit 1 }
$repo = "canadianproducer/holos"
$ver = (Select-String -Path "app\common.py" -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
$asset = "dist\Holos-Setup-$ver.exe"
if (-not (Test-Path $asset)) { throw "Not found: $asset. Run build-release.bat first." }

# Ask Git Credential Manager for the saved GitHub login.
# Input goes through a plain ASCII file: piping from PowerShell can prepend a BOM
# ("refusing to work with credential missing protocol field").
$credIn = Join-Path $env:TEMP "holos-cred.txt"
[IO.File]::WriteAllText($credIn, "protocol=https`nhost=github.com`n`n", [Text.Encoding]::ASCII)
$cred = cmd /c "git credential fill < `"$credIn`""
Remove-Item $credIn -ErrorAction SilentlyContinue
$token = (($cred | Where-Object { $_ -like "password=*" }) -replace "^password=", "")
if (-not $token) { throw "No GitHub login in Git. Run publish.bat first." }
$h = @{ Authorization = "Bearer $token"; Accept = "application/vnd.github+json"; "User-Agent" = "holos-release" }

$notes = if (Test-Path "release_notes.md") { [IO.File]::ReadAllText("release_notes.md", [Text.Encoding]::UTF8) } else { "" }
$tag = "v$ver"
try {
    $rel = Invoke-RestMethod -Headers $h -Uri "https://api.github.com/repos/$repo/releases/tags/$tag"
    Write-Host "Release $tag already exists: updating notes and the file"
    $patch = @{ body = $notes; name = "Holos $ver" } | ConvertTo-Json
    $rel = Invoke-RestMethod -Method Patch -Headers $h -Uri "https://api.github.com/repos/$repo/releases/$($rel.id)" `
        -Body ([Text.Encoding]::UTF8.GetBytes($patch)) -ContentType "application/json; charset=utf-8"
} catch {
    $body = @{ tag_name = $tag; target_commitish = "main"; name = "Holos $ver"; body = $notes } | ConvertTo-Json
    $rel = Invoke-RestMethod -Method Post -Headers $h -Uri "https://api.github.com/repos/$repo/releases" `
        -Body ([Text.Encoding]::UTF8.GetBytes($body)) -ContentType "application/json; charset=utf-8"
    Write-Host "Created release $tag"
}
$name = [IO.Path]::GetFileName($asset)
foreach ($a in $rel.assets) { if ($a.name -eq $name) {
    Invoke-RestMethod -Method Delete -Headers $h -Uri "https://api.github.com/repos/$repo/releases/assets/$($a.id)" | Out-Null } }
$size = [math]::Round((Get-Item $asset).Length / 1MB)
Write-Host "Uploading $name ($size MB)... this can take a few minutes"
Invoke-RestMethod -Method Post -Headers $h -InFile $asset -ContentType "application/octet-stream" `
    -Uri "https://uploads.github.com/repos/$repo/releases/$($rel.id)/assets?name=$name" -TimeoutSec 7200 | Out-Null
Write-Host ""
Write-Host "DONE: $($rel.html_url)"
Stop-Transcript | Out-Null
