# OpenCourser

Offline course progress tracker — scan local media courses, browse files, track watch progress, and manage completion.

Built with Django 5.2, HTMX, Alpine.js, Bootstrap 5 (dark theme), and Font Awesome 6.

---

## Architecture

```
config/              Django project configuration (settings, urls, wsgi)
apps/
  workspaces/        Workspace CRUD, directory browsing, filesystem scanning
  courses/           Course/file browsing, completion toggling
  media/             Media streaming (byte-range), metadata extraction
  progress/          Watch history recording, progress computation
domain/skills/       Pure domain logic (no Django imports)
  storage_mapping.py       Path resolution, traversal prevention
  content_discovery.py     Filesystem scanning, change detection
  media_understanding.py   ffprobe/binary metadata extraction
  progress_tracking.py     Progress computation, thresholds
  learning_structure.py    Navigation tree builder
  integrity_management.py  Consistency checks
  background_processing.py Thread-pool job runner
templates/           Django templates (HTMX partials, Bootstrap)
static/              Static assets (logo.svg)
tests/               pytest unit tests for domain skills
media/               User-uploaded cover images
```

Each app follows a **presentation → application → domain** layering:
- Views handle HTTP (presentation)
- Services orchestrate operations (application)
- Domain skills implement pure logic (domain)

---

## Features

- **Workspace management** — add/remove/edit workspaces with cover images, sortable by name or creation date
- **Course management** — rename courses, upload cover images, sort by name or progress
- **Filesystem scanning** — incremental and full scans detect new, modified, and deleted files
- **Course browsing** — view courses as cards with progress bars, numbered and paginated (15/page)
- **File player** — browser-native video/audio player with resume, position tracking, auto-complete on end
- **Progress tracking** — per-file watched duration, completion toggle, course-level aggregation
- **Metadata extraction** — ffprobe-based media info with pure-Python fallback (MP4/MKV header parsing)
- **HTMX-driven UI** — no full page reloads for scan, completion toggle, or progress updates
- **Cover images** — upload cover art for workspaces and courses
- **Responsive** — mobile-friendly layout down to 360px viewport (Galaxy S8+)
- **Pagination** — 15 items per page on workspace list and course list
- **Professional UI** — Font Awesome 6 icons on all buttons, custom SVG logo
- **Docker** — ready to deploy with Docker Compose, host filesystem bind mount
- **Dark theme** — Bootstrap 5 dark mode throughout

---

## Quick Start

### Local Development

```bash
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
pip install Pillow          # cover image support
python manage.py migrate
python manage.py runserver
```

### Docker

```bash
# Set your courses directory (optional, defaults to ./courses)
echo "COURSE_ROOT=C:\Users\me\Courses" > .env

docker compose up -d
```

Set `COURSE_ROOT` in `.env` to the absolute path of your courses directory. It is mounted at `/courses` inside the container. When creating a workspace in Docker, use `course_root = "/courses"`.

---

## Usage

1. Create a **Workspace** — give it a name and point it to a local directory containing course folders
2. Upload a **cover image** — optional, via the Edit page for each workspace or course
3. Click **Scan Now** — discovers courses and media files, extracts metadata
4. Browse courses — cards show progress bars, sortable by name or progress, paginated 15/page
5. Play a file — browser-native player with auto-resume, position tracking every 3 seconds
6. Track progress — use **Mark Complete / Undo** buttons, or let the player auto-complete on end
7. Edit titles & covers — use the **Edit** button on any workspace or course

---

## Tests

```bash
python -m pytest --tb=short -q          # all tests (40+)
python -m pytest tests/                 # domain skill tests only
python manage.py test                   # Django integration tests
```

---

## Docker

The Docker image includes ffprobe for richer metadata extraction. The `.dockerignore` keeps the build context lean by excluding virtualenvs, caches, and IDE files.

| Volume | Purpose |
|--------|---------|
| `./data:/app/data` | SQLite database persistence |
| `./media:/app/media` | Uploaded cover images |
| `${COURSE_ROOT}:/courses:ro` | Host course directory (read-only) |

---

## Developer

Developed by [Mohammad .H Abedi](https://www.linkedin.com/in/abedimhosein/)

---

## License

MIT
