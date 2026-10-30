# Issue tracker: GitHub

Issues and specs live in https://github.com/scwlkr/dev-den/issues.
Use the `gh` CLI from this repository.

## Conventions

- Create: `gh issue create --title "..." --body-file <path>`.
- Read: `gh issue view <number> --json number,title,body,labels,comments`.
- List: `gh issue list --state open --json number,title,body,labels`.
- Comment: `gh issue comment <number> --body-file <path>`.
- Apply or remove labels: `gh issue edit <number> --add-label "..."`
  or `--remove-label "..."`.
- Close: `gh issue close <number> --comment "..."`.

Use temporary files for multiline bodies and remove them afterward.
Infer the repository from the origin remote.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## Skill instructions

"Publish to the issue tracker" means create a GitHub issue.
"Fetch the relevant ticket" means read the referenced GitHub issue.

## Wayfinding

Use a `wayfinder:map` issue for the map and GitHub sub-issues for
child tickets. If sub-issues are unavailable, use a task list in
the map and `Part of #<parent>` in each child.

Use native GitHub issue dependencies for blockers when available;
otherwise put `Blocked by: #<number>` at the top of the issue body.
Claim tickets by assigning yourself. Resolve them with a result
comment, close them, and record the result in the map.
