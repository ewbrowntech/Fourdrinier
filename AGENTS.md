# Fourdrinier — Agent Instructions

## Overview

## Tech Stack

## Project Structure

## Commands

## Architecture

## Code Style

## Agent Rules

Detailed coding standards live in `docs/standards/`. Claude and Cursor load
path-scoped rules through symlinks in `.claude/rules/` and `.cursor/rules/`;
Codex and OpenCode follow the mandatory pointers in this file. Keep this file
concise and put detailed, task-specific guidance in the standards documents.

## Backend Coding Standards

Before modifying `src/backend/`, read and follow
[`docs/standards/backend.md`](docs/standards/backend.md). This is mandatory
for backend application code, tests, and Alembic migrations.

## Testing

## Configuration

## Agent Skills

This repo includes [Anthropic's `frontend-design` skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design) for distinctive, production-grade UI work (avoids generic AI aesthetics).

| Tool | Path |
|------|------|
| Canonical | `.agents/skills/frontend-design/` |
| Cursor | `.cursor/skills/frontend-design/` (symlink) |
| Claude Code | `.claude/skills/frontend-design/` (symlink) |

The agent should read and follow that skill when building or styling web UI (components, pages, layouts, dashboards, landing pages). Users can also invoke it explicitly (e.g. `/frontend-design` in Claude Code).

To refresh from upstream: `npx skills update frontend-design`

Lock file: `skills-lock.json` (used by `npx skills experimental_install`).
## Boundaries
