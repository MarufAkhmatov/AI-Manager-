# Agent avatar portraits

Drop one PNG per agent here. The dashboard's `AgentAvatar` component loads
`/avatars/<slug>.png` and silently falls back to the hand-drawn inline SVG
in `components/avatars/index.tsx` if the file is missing — so the UI works
either way.

Expected filenames (lowercase, exact slug match):

| Slug         | File                  |
|--------------|-----------------------|
| `manager`    | `manager.png`         |
| `architect`  | `architect.png`       |
| `metodist`   | `metodist.png`        |
| `searcher`   | `searcher.png`        |
| `secure`     | `secure.png`          |
| `shadow`     | `shadow.png`          |
| `regulyator` | `regulyator.png`      |

Recommended:
- Square aspect ratio (the UI crops to a circle).
- 256×256 or larger; PNG with transparent or solid background.
- Optimised (<60 KB each) so the dashboard stays snappy.
