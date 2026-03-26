# Janito4 Documentation

This directory contains the MkDocs documentation for Janito4.

## Prerequisites

Install the documentation dependencies:

```bash
pip install -r requirements.txt
```

## Building

Build the documentation:

```bash
mkdocs build
```

## Local Development Server

Start a local development server:

```bash
mkdocs serve
```

The documentation will be available at `http://localhost:8000`.

## Deployment

Deploy to GitHub Pages:

```bash
mkdocs gh-deploy
```

## Project Structure

```
docs/
├── mkdocs.yml           # MkDocs configuration
├── docs/
│   ├── index.md         # Home page
│   ├── getting-started/ # Getting started guide
│   ├── configuration/   # Configuration documentation
│   ├── usage/           # Usage documentation
│   ├── tools/           # Tools documentation
│   ├── development/     # Development guide
│   └── reference/       # Reference documentation
└── requirements.txt     # Documentation dependencies
```

## Editing

1. Make changes to the `.md` files in `docs/docs/`
2. Preview locally with `mkdocs serve`
3. Commit and push changes
4. The documentation will be automatically deployed to GitHub Pages
