# OpenCourser

Offline course progress tracker — scan local media courses, browse files, track watch progress, and manage completion.

Built with Django 5.2, HTMX, Alpine.js, and Bootstrap 5 (dark theme).

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
tests/               pytest unit tests for domain skills
```

Each app follows a **presentation → application → domain** layering:
- Views handle HTTP (presentation)
- Services orchestrate operations (application)
- Domain skills implement pure logic (domain)

---

## Features

- **Workspace management** — add/remove workspaces pointing to local directories
- **Filesystem scanning** — incremental and full scans detect new, modified, and deleted files
- **Course browsing** — view courses as cards with progress bars, sort by name or progress
- **File player** — browser-native video/audio player with resume, position tracking, auto-complete on end
- **Progress tracking** — per-file watched duration, completion toggle, course-level aggregation
- **Metadata extraction** — ffprobe-based media info with pure-Python fallback (MP4/MKV header parsing)
- **HTMX-driven UI** — no full page reloads for scan, completion toggle, or progress updates
- **Cover images** — upload cover art for workspaces and courses
- **Responsive** — mobile-friendly layout down to 360px viewport
- **Docker** — ready to deploy with Docker Compose

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
docker compose up -d
```

The Docker image includes ffprobe for richer metadata extraction.

---

## Usage

1. Create a **Workspace** pointing to a local directory containing course folders
2. Click **Scan Now** to discover courses and media files
3. Browse a course, play files, track progress
4. Use **Mark Complete / Undo** to manually set completion

---

## Tests

```bash
python -m pytest --tb=short -q          # all tests
python -m pytest tests/                 # domain skill tests only
python manage.py test                   # Django integration tests
```

## Developer

Developed by [Mohammad .H Abedi](https://www.linkedin.com/in/abedimhosein/)

---

## License

MIT
