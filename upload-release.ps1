# Uploads dist\Holos-Setup-<version>.exe to GitHub Releases of canadianproducer/holos.
# Uses the GitHub login that Git already has (Git Credential Manager) - no extra tokens to create.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$repo = "canadianproducer/holos"
$ver = (Select-String -Path "app\common.py" -Pattern '^VERSION = "(.+)"').Matches[0].Groups[1].Value
$asset = "dist\Holos-Setup-$ver.exe"
if (-not (Test-Path $asset)) { throw "Not found: $asset. Run build-release.bat first." }

$cred = "protocol=https`nhost=github.com`n`n" | git credential fill
$token = (($cred | Where-Object { $_ -like "password=*" }) -replace "^password=", "")
if (-not $token) { throw "No GitHub login in Git. Run publish.bat first." }
$h = @{ Authorization = "Bearer $token"; Accept = "application/vnd.github+json"; "User-Agent" = "holos-release" }

$notes = if (Test-Path "release_notes.md") { [IO.File]::ReadAllText("release_notes.md", [Text.Encoding]::UTF8) } else { "" }
$tag = "v$ver"
try {
    $rel = Invoke-RestMethod -Headers $h -Uri "https://api.github.com/repos/$repo/releases/tags/$tag"
    Write-Host "Release $tag already exists, adding the file to it"
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
