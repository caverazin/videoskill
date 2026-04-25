param(
    [Parameter(Mandatory = $true)]
    [string]$Url,

    [string]$OutputReport
)

$ErrorActionPreference = 'Stop'

function Get-VideoId {
    param([string]$InputUrl)

    try {
        $uri = [System.Uri]$InputUrl
    }
    catch {
        return $null
    }

    if ($uri.Host -match 'youtu\.be$') {
        return $uri.AbsolutePath.Trim('/')
    }

    if ($uri.Query) {
        $query = $uri.Query.TrimStart('?').Split('&', [System.StringSplitOptions]::RemoveEmptyEntries)
        foreach ($pair in $query) {
            $parts = $pair.Split('=', 2)
            if ($parts.Count -eq 2 -and $parts[0] -eq 'v') {
                return [System.Uri]::UnescapeDataString($parts[1])
            }
        }
    }

    return $null
}

function Invoke-WebString {
    param([string]$TargetUrl)

    try {
        $result = & curl.exe -L -sS --max-time 30 --user-agent 'Mozilla/5.0' $TargetUrl 2>$null
        if ($LASTEXITCODE -eq 0 -and $null -ne $result) {
            return (($result | Out-String).Trim())
        }
    }
    catch {
    }

    try {
        return (Invoke-WebRequest -UseBasicParsing -MaximumRedirection 5 -Headers @{
                'User-Agent' = 'Mozilla/5.0'
            } -Uri $TargetUrl).Content
    }
    catch {
        return $null
    }
}

function Add-Section {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Title,
        [string[]]$Body
    )

    $Lines.Add("## $Title")
    foreach ($line in $Body) {
        $Lines.Add($line)
    }
    $Lines.Add('')
}

$videoId = Get-VideoId -InputUrl $Url
if (-not $videoId) {
    throw "Could not derive a YouTube video ID from: $Url"
}

$reportLines = [System.Collections.Generic.List[string]]::new()
$reportLines.Add("# Video inspection report")
$reportLines.Add('')
$reportLines.Add("- URL: $Url")
$reportLines.Add("- Video ID: $videoId")
$reportLines.Add("- Generated at: $(Get-Date -Format s)")
$reportLines.Add('')

$encodedUrl = [System.Uri]::EscapeDataString($Url)

$oembedRaw = Invoke-WebString -TargetUrl "https://www.youtube.com/oembed?url=$encodedUrl&format=json"
$title = $null
$author = $null
if ($oembedRaw) {
    try {
        $oembed = $oembedRaw | ConvertFrom-Json
        $title = $oembed.title
        $author = $oembed.author_name
    }
    catch {
    }
}

Add-Section -Lines $reportLines -Title 'Metadata' -Body @(
    ('- Title: ' + $(if ($title) { "`"$title`"" } else { '<unavailable>' })),
    ('- Channel: ' + $(if ($author) { "`"$author`"" } else { '<unavailable>' }))
)

$transcriptApiUrl = "https://transcript-api.com/web/transcript?video_url=$encodedUrl"
$transcriptApiRaw = Invoke-WebString -TargetUrl $transcriptApiUrl
Add-Section -Lines $reportLines -Title 'transcript-api.com' -Body @(
    "- URL: $transcriptApiUrl",
    ('- Result: ' + $(if ($transcriptApiRaw) { 'response received' } else { 'no response captured' })),
    '',
    '```json',
    ($(if ($transcriptApiRaw) { $transcriptApiRaw } else { 'null' })),
    '```'
)

$twooutubeUrl = "https://2outube.com/api/transcript?v=$videoId"
$twooutubeRaw = Invoke-WebString -TargetUrl $twooutubeUrl
Add-Section -Lines $reportLines -Title '2outube' -Body @(
    "- URL: $twooutubeUrl",
    ('- Result: ' + $(if ($twooutubeRaw) { 'response received' } else { 'no response captured' })),
    '',
    '```json',
    ($(if ($twooutubeRaw) { $twooutubeRaw } else { 'null' })),
    '```'
)

$watchHtml = Invoke-WebString -TargetUrl "https://www.youtube.com/watch?v=$videoId"
$captionMatch = $null
$storyboardMatch = $null
if ($watchHtml) {
    $captionMatch = [regex]::Match($watchHtml, 'captionTracks\":\[(.*?)\]')
    $storyboardMatch = [regex]::Match($watchHtml, 'playerStoryboardSpecRenderer\":\{\"spec\":\"(.*?)\"')
}

$captionSnippet = if ($captionMatch -and $captionMatch.Success) { $captionMatch.Value } else { $null }
$storyboardSnippet = if ($storyboardMatch -and $storyboardMatch.Success) { $storyboardMatch.Groups[1].Value } else { $null }

Add-Section -Lines $reportLines -Title 'YouTube watch HTML' -Body @(
    ('- HTML fetched: ' + $(if ($watchHtml) { 'yes' } else { 'no' })),
    ('- captionTracks found: ' + $(if ($captionSnippet) { 'yes' } else { 'no' })),
    ('- storyboard spec found: ' + $(if ($storyboardSnippet) { 'yes' } else { 'no' }))
)

if ($captionSnippet) {
    Add-Section -Lines $reportLines -Title 'Caption snippet' -Body @(
        '```text',
        ($captionSnippet.Substring(0, [Math]::Min($captionSnippet.Length, 1200))),
        '```'
    )
}

if ($storyboardSnippet) {
    Add-Section -Lines $reportLines -Title 'Storyboard snippet' -Body @(
        '```text',
        ($storyboardSnippet.Substring(0, [Math]::Min($storyboardSnippet.Length, 1200))),
        '```'
    )
}

$timedtextUrl = "https://www.youtube.com/api/timedtext?v=$videoId&lang=en&kind=asr&fmt=vtt"
$timedtextBody = Invoke-WebString -TargetUrl $timedtextUrl
Add-Section -Lines $reportLines -Title 'Direct timedtext check' -Body @(
    "- URL: $timedtextUrl",
    ('- Body captured: ' + $(if ($timedtextBody) { 'yes' } else { 'no or empty' }))
)

Add-Section -Lines $reportLines -Title 'Interpretation' -Body @(
    "- If transcript services fail but captionTracks exists, captions are available in metadata.",
    "- If storyboard spec exists, YouTube exposes frame-print/storyboard sources.",
    "- Empty timedtext body or blocked storyboard fetch should be reported as client-side or anti-bot restriction, not as proof that captions or prints do not exist."
)

$report = $reportLines -join [Environment]::NewLine

if ($OutputReport) {
    $parent = Split-Path -Parent $OutputReport
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -Path $OutputReport -Value $report -Encoding UTF8
    Write-Output "Report written to $OutputReport"
}
else {
    Write-Output $report
}
