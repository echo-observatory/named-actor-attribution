# AGENTS.md

## About this repo

Builds a tiered English eval dataset for attributing text segments to named actors (the task of Karaage's attribution step), for use in the `evals` repo. `specification.md` is the dataset specification.

## Pipeline context

The `pipeline` repo's README is the single source for how the components fit together.
Read `../pipeline/README.md` before any work that touches another component or a shared interface.
If that file does not exist, tell the user that the `pipeline` repo needs to be cloned next to this one.
Do not copy its content into this repo.

## Conventions

- Work starts from an issue or a simple and straightforward task. If it looks like there is not much to explain, do not create an issue and document directly in the PR.
- Branch from `main` as `<issue-number>-short-description`. Never commit directly to `main`.
- Commit messages are short and imperative. No agent attribution (no `Co-Authored-By`, no "Generated with ..." lines) in commits or PRs.
- Never commit secrets, `.env` files or raw corpus data.
- Repo and file names are lowercase-kebab.
- Before every commit and before opening a PR, read and follow `COMMIT_CHECKLIST.md`.

## Documentation

`README.md` is the documentation for this repo: purpose, inputs, outputs, and how to set up, run and test.
Read it before working here, and keep it up to date as part of every change that affects it.
Do not repeat that content in this file.
