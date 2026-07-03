# OpenCourser

<p align="center">
    <a href="#"><img src="https://img.shields.io/badge/python-3.12-blue?style=flat-square" alt="Python 3.12"></a>
    <a href="#"><img src="https://img.shields.io/badge/django-5.2-%23092E20?style=flat-square" alt="Django 5.2"></a>
    <a href="#"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License"></a>
    <a href="#"><img src="https://img.shields.io/badge/status-stable-%2300B4D8?style=flat-square" alt="Status: Stable"></a>
</p>

<p align="center">
    <strong>Offline course progress tracker</strong> — scan local media courses, browse files, track watch progress, and manage completion. All data stays on your machine.
</p>

---

## Overview

OpenCourser is a self-hosted Django web application that helps you organize, browse, and track progress through local media course directories. Point it at a folder of courses, scan for media files, and get a clean web UI with progress tracking, completion toggling, and a browser-native media player — no cloud, no subscriptions, no data leaving your computer.

---

## Features

| Category | Feature | Description |
|----------|---------|-------------|
| **Workspaces** | CRUD management | Create, edit, delete workspaces with optional cover images |
| | Filesystem scanning | Incremental and full scans detect new, modified, deleted files |
| | Course count | Shows number of courses per workspace |
| **Courses** | Browsing | Card-based layout with progress bars, paginated (15/page) |
| | Editing | Rename courses, change workspace, upload cover images, sort by name or progress |
| | Search | Global search across all workspaces |
| **Notes** | Markdown notes | Add notes to any file/video with full Markdown support |
| | Note search | Search all notes with workspace and course filters |
| | Inline editing | Edit notes in-place with live preview toggle |
| **Media** | Player | Browser-native video/audio player with resume and auto-complete |
| | Metadata | ffprobe extraction with pure-Python fallback for MP4/MKV |
| **Progress** | Tracking | Per-file watched duration, completion toggle, course-level aggregation |
| | Auto-tracking | Position recorded every 3s; auto-completes when playback ends |
| | Activity charts | Bar and line charts showing daily/weekly watch activity with trend lines |
| **UI/UX** | HTMX-driven | No full-page reloads for scans, completion, or progress updates |
| | Dark theme | Bootstrap 5 dark mode throughout |
| | Responsive | Supports down to 360px viewport (Galaxy S8+) with hamburger menus |
| | Icons | Font Awesome 6 on every button and interactive element |
| **Deployment** | Docker | Ready-to-deploy with Docker Compose, multiple host directory bind mounts |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5.2, Python 3.12 |
| Database | SQLite |
| Frontend | Bootstrap 5 (dark), HTMX, Alpine.js |
| Icons | Font Awesome 6 |
| Media | ffmpeg / ffprobe |
| Notes | Markdown rendering with fenced code, tables, lists |
| Server | Gunicorn (production) |
| Container | Docker, Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.12+
- pip
- Virtual environment (recommended)
- ffmpeg (optional, for richer media metadata)

### Local Development

```bash
# Clone the repository
git clone https://github.com/abedimhosein/open-courser.git
cd open-courser

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Start the development server
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Docker

```bash
# Define course root directories in .env
cat <<EOF > .env
COURSE_ROOT_0=C:\Users\You\Downloads
COURSE_ROOT_1=D:\Courses
EOF

# Build and start
docker compose up -d
```

The application is available at [http://localhost:8000](http://localhost:8000).

> **How it works:** Each `COURSE_ROOT_N` env var maps to a read-only volume mount at `/courses/N` inside the container. When you click **Browse** in the workspace/course create form, only the configured roots are shown as starting points — not the entire container filesystem.

> **Adding more roots:** Add a new `COURSE_ROOT_N` line in `.env` and a matching volume mount in `docker-compose.yml`, then restart.

### Docker Volumes

| Volume | Purpose |
|--------|---------|
| `./data:/app/data` | SQLite database persistence |
| `./media:/app/media` | Uploaded cover images |
| `${COURSE_ROOT_0}:/courses/0:ro` | First host course directory (read-only) |
| `${COURSE_ROOT_1}:/courses/1:ro` | Second host course directory (read-only) |

---

## Usage

1. **Create a Workspace** — give it a name and optionally point it to a course root directory (Docker shows configured roots; local dev browses the filesystem).
2. **Upload a Cover Image** *(optional)* — via the Edit page for each workspace or course.
3. **Scan Now** — discovers courses, media files, and extracts metadata.
4. **Browse Courses** — cards show progress bars; sort by name or progress; paginated 15/page.
5. **Search** — use the navbar search to find courses across all workspaces.
6. **Play a File** — browser-native player with auto-resume and position tracking every 3 seconds.
7. **Add Notes** — click on any video/file, then use the Notes section to add Markdown notes.
8. **Search Notes** — use the Notes link in the navbar to search all notes with workspace/course filters.
9. **Track Progress** — use **Mark Complete / Undo** buttons, or let the player auto-complete when playback ends.
10. **Activity** — view daily/weekly watch charts with trend lines on the Activity page.
11. **Edit Titles & Covers** — use the **Edit** button on any workspace or course.

---

## Project Structure

```
config/              Django project configuration (settings, urls, wsgi)
apps/
  workspaces/        Workspace CRUD, directory browsing, filesystem scanning
  courses/           Course/file browsing, completion toggling
  media/             Media streaming (byte-range), metadata extraction
  progress/          Watch history recording, progress computation
  notes/             Markdown notes with search and filtering
domain/skills/       Pure domain logic (no Django imports)
  storage_mapping.py       Path resolution, traversal prevention
  content_discovery.py     Filesystem scanning, change detection
  media_understanding.py   ffprobe/binary metadata extraction
  progress_tracking.py     Progress computation, thresholds
  learning_structure.py    Navigation tree builder
  integrity_management.py  Consistency checks
  background_processing.py Thread-pool job runner
templates/           Django templates (HTMX partials, Bootstrap)
static/              Static assets (logo.svg, CSS, JS)
tests/               pytest unit tests for domain skills
media/               User-uploaded cover images
```

Each app follows a **presentation → application → domain** layering:
- **Views** handle HTTP (presentation)
- **Services** orchestrate operations (application)
- **Domain skills** implement pure logic (domain)

---

## Testing

```bash
# Run all tests (66+)
python -m pytest --tb=short -q

# Domain skill tests only
python -m pytest tests/

# Django integration tests
python manage.py test

# Notes tests only
python manage.py test apps.notes
```

---

## Contributing

Contributions are welcome! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -am 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

Please ensure tests pass before submitting.

---

## Author

**Mohammad H. Abedi**  
[LinkedIn](https://www.linkedin.com/in/abedimhosein/) · [GitHub](https://github.com/abedimhosein)

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
