# Legacy launcher (Tkinter) — reference only

This is the El Dorado launcher as released on `main` (Python + Tkinter: `uncharted_launcher.pyw`, the
home screen `eldorado_hub.py`, and their helpers). On the `launcher-v2` branch it is **not run, packaged
or maintained**: it is kept here only to read how each feature works while the new launcher is written
(see `docs/LAUNCHER_V2_ROADMAP.md`).

- Do not fix bugs here: fix them on `main`, where this launcher still ships.
- Paths inside these files assume they live in `launcher/` (for example `ROOT = Path(__file__).parent.parent`);
  from this folder they no longer resolve, by design.
- This folder is deleted when the new launcher reaches parity (roadmap phase 6).
