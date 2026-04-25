# YouTube HTML fallback

Use this path when free transcript services fail or when you need to prove that captions or storyboard prints exist.

## 1. Pull the watch HTML

```powershell
curl.exe -L "https://www.youtube.com/watch?v=VIDEO_ID"
```

## 2. Check captions

Look for:

- `captionTracks`
- `playerCaptionsTracklistRenderer`

Example:

```powershell
$html = (curl.exe -L "https://www.youtube.com/watch?v=VIDEO_ID") -join "`n"
[regex]::Match($html, 'captionTracks\":\[(.*?)\]')
```

Interpretation:

- match found: captions exist in metadata
- no match: no caption tracks detected from the fetched HTML

## 3. Check storyboard / frame prints

Look for:

- `playerStoryboardSpecRenderer.spec`

Example:

```powershell
$html = (curl.exe -L "https://www.youtube.com/watch?v=VIDEO_ID") -join "`n"
[regex]::Match($html, 'playerStoryboardSpecRenderer\":\{\"spec\":\"(.*?)\"')
```

Interpretation:

- match found: YouTube exposed storyboard sheets for frame prints
- no match: storyboard source not detected from the fetched HTML

## 4. Direct fetch caveat

Even when `captionTracks` or `storyboard` are present:

- timedtext can return `200` with empty body
- storyboard sheet fetch can return `403`

That does not mean the source is absent.

It means:

- the source exists in metadata
- the current client is blocked or not allowed to fetch the concrete media body

Report that difference clearly.
