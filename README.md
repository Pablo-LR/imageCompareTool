# Loc Screenshot Checker

A desktop tool for comparing localization screenshots across language folders. Uses one language as the source of truth and highlights missing, extra, and matched images with a side-by-side view.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey)

## Features

- **Side-by-side comparison** — Source and target images displayed together
- **Missing detection** — Images in source but not in target
- **Extra detection** — Images in target but not in source
- **Sidebar file list** — Color-coded status icons for every image
- **Filter by status** — Show all, matched only, missing only, or extra only
- **Delete from app** — Remove target screenshots directly (sends to trash if `send2trash` is installed)
- **Keyboard navigation** — Arrow keys, Space, Home/End, Delete

## Install

```bash
pip install Pillow
```

Optional (sends deleted files to trash instead of permanent delete):
```bash
pip install send2trash
```

## Usage

```bash
python loc_screenshot_checker.py
```

1. Click **Source Folder** — select your reference language folder (e.g. `en/`)
2. Click **Target Folder** — select the language to check (e.g. `es/`, `ar/`)
3. Browse images with arrow keys or click the sidebar list

### Status Icons

| Icon | Meaning |
|------|---------|
| ● green | Image exists in both folders |
| ◑ yellow | Missing in target (source only) |
| ◐ blue | Extra in target (not in source) |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` `↓` `←` `→` | Navigate images |
| `Space` | Next image |
| `Home` / `End` | Jump to first / last |
| `Delete` / `Backspace` | Delete target image |
