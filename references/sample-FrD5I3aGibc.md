# Video inspection report

- URL: https://www.youtube.com/watch?v=FrD5I3aGibc
- Video ID: FrD5I3aGibc
- Generated at: 2026-04-24T21:50:13

## Metadata
- Title: "Use Office 365 Connectors in Microsoft Teams"
- Channel: "Microsoft 365 Developer"

## transcript-api.com
- URL: https://transcript-api.com/web/transcript?video_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DFrD5I3aGibc
- Result: response received

```json
{"detail":"Transcript not found for video: FrD5I3aGibc"}
```

## 2outube
- URL: https://2outube.com/api/transcript?v=FrD5I3aGibc
- Result: response received

```json
{"videoId":"FrD5I3aGibc","transcript":[],"available":false,"failureReason":"bot_detection","failureMessage":"YouTube requires sign-in for this video. This may be temporary."}
```

## YouTube watch HTML
- HTML fetched: yes
- captionTracks found: yes
- storyboard spec found: yes

## Caption snippet
```text
captionTracks":[{"baseUrl":"https://www.youtube.com/api/timedtext?v=FrD5I3aGibc\u0026ei=4w_saae-BquN-LAPl9--wQg\u0026caps=asr\u0026opi=112496729\u0026exp=xpe\u0026xoaf=5\u0026xowf=1\u0026hl=pt\u0026ip=0.0.0.0\u0026ipbits=0\u0026expire=1777103443\u0026sparams=ip,ipbits,expire,v,ei,caps,opi,exp,xoaf\u0026signature=A65387B8971085E2DBA7479C325F3F299DE1F27F.88F74FAB54EA93BD79E420291F13EB9660567040\u0026key=yt8\u0026kind=asr\u0026lang=en","name":{"simpleText":"Inglês (gerada automaticamente)"},"vssId":"a.en","languageCode":"en","kind":"asr","isTranslatable":true,"trackName":""}]
```

## Storyboard snippet
```text
https://i.ytimg.com/sb/FrD5I3aGibc/storyboard3_L$L/$N.jpg?sqp=-oaymwGhAUg48quKqQOYAYgBAZUBAAAEQpgBMqABPKgBBLIBQBANDBAVHyYtDg4PEhcrLCkPDhAVHyoyKQ8RFBgmPTgtERQeKjFLRzYVHCkuOUdNPyUuNz1HUlFFM0BCQ0xERkO6AUARERUjRENDQxETFi9DQ0NDFRYpQ0NDQ0MjL0NDQ0NDQ0RDQ0NDQ0JCQ0NDQ0NCQkJDQ0NDQkJCQkNDQ0JCQkJCovOX_wMGCNnI_4UG|48#27#100#10#10#0#default#rs$AOn4CLAZov9-IOimxDGz3ork8UIAzlKTdA|80#45#72#10#10#5000#M$M#rs$AOn4CLDnbjzHtnyztu-6A0IGFo8tPOwang|160#90#72#5#5#5000#M$M#rs$AOn4CLC0TkxK2b3Y0JpdTtuboM2bkV8Kqg
```

## Direct timedtext check
- URL: https://www.youtube.com/api/timedtext?v=FrD5I3aGibc&lang=en&kind=asr&fmt=vtt
- Body captured: no or empty

## Interpretation
- If transcript services fail but captionTracks exists, captions are available in metadata.
- If storyboard spec exists, YouTube exposes frame-print/storyboard sources.
- Empty timedtext body or blocked storyboard fetch should be reported as client-side or anti-bot restriction, not as proof that captions or prints do not exist.

