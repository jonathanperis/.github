# .github — Agent Guide

Organization-wide default community health files for all jonathanperis repositories. Files here are inherited by repos that don't have their own.

---

## Structure

```
.github/
├── CODE_OF_CONDUCT.md              # Contributor Covenant v2.1
├── CONTRIBUTING.md                 # Fork → branch → commit → test → PR workflow
├── SECURITY.md                     # Private vulnerability reporting (48h acknowledgment)
├── SUPPORT.md                      # Support resources + issue templates
├── LICENSE                         # MIT License (2026 Jonathan Peris)
├── README.md                       # Repository overview
└── .github/
    ├── FUNDING.yml                 # GitHub Sponsors + Buy Me A Coffee
    ├── pull_request_template.md    # PR template (Summary, Changes, Test Plan)
    └── ISSUE_TEMPLATE/
        ├── bug_report.yml          # Bug report (auto-labeled "bug")
        └── feature_request.yml     # Feature request (auto-labeled "enhancement")
```

---

## How It Works

GitHub automatically applies these files to all repositories in the `jonathanperis` account that don't define their own:
- Code of Conduct
- Contributing guidelines
- Security policy
- Support resources
- PR template
- Issue templates
- Funding links

---

## Editing Guidelines

- Changes here affect **all repos** that don't override these files
- Keep templates generic — project-specific instructions belong in the project's own `.github/`
- Issue templates use YAML format (GitHub native forms)
- PR template uses Markdown
- Security policy directs to GitHub's private vulnerability reporting
