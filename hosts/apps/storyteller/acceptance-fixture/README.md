# Storyteller alignment acceptance fixture

This tiny user-owned fixture exists only to exercise Storyteller's complete
readaloud pipeline without spending hours transcribing the retained ten-hour
Alice audiobook.

Build the EPUB with `build-epub.sh`. Generate speech from `speech.txt` with a
local text-to-speech engine, encode it as M4B, and retain both inputs with the
phase evidence. The author/title key is exactly:

```text
Phase Six Acceptance/Short Alignment Fixture
```

Do not place this fixture in Shelfarr's canonical ebook or audiobook roots.
Run the reconciler with explicit isolated source roots and publish through
Storyteller's normal inbox.
