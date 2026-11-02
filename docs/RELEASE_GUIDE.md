# Publishing the prepared release safely

This guide is for the maintainer, not an assertion that publication has happened.
The current project directory was supplied without `.git`. Do not initialize it
and replace remote history with an unrelated root commit. A private local backup
was created before release edits. Keep it private.

## Authorization and backup

The initial integration lacked write permission. The maintainer subsequently
installed Git/GitHub CLI, authorized repository/workflow access and provided a
clean clone. Normal Git access now works. The remote backup branch
`backup/main-before-harness-release-20261103` preserves the original main commit.
No alternate credential bypass, force push or history rewrite is used.

## History-preserving publication

1. Re-read `refs/heads/main`. The inspected original is
   `0edc63aa3b74b817d573c265c39d0e719fa791e2`. If it has moved, inspect the new
   commits and reconcile differences before updating it.
2. Create a remote backup branch pointing to that exact current commit. Confirm
   the branch exists before publishing any replacement content.
3. Use a separate fresh clone (when Git is available), or the GitHub Git-data API
   with that commit as the parent. Keep the original working directory intact.
4. Overlay the reviewed source candidate. Preserve unrecognized remote-only
   files pending review. Never overwrite a remote change silently. The remote
   legacy root modules are not the canonical launch path of this release.
5. Inspect tracked `config.yaml` on the remote before publication. `.gitignore`
   does not untrack an existing file or remove secrets from history. Publish only
   placeholder configuration; if an actual credential is present in public
   history, tell its owner to rotate it. Do not print the credential.
6. Check the full staged diff, filenames, secret scan, test evidence and workflows.
   Make a normal commit with the prior main commit as its ancestor; push normally.
   Respect branch protection and stop on conflicts or authorization failures.
7. Observe both test and Pages workflow runs. A successful local build does not
   prove a remote Action has succeeded. Configure Settings → Pages → GitHub
   Actions if required; never claim deployment before its URL is checked.
8. Record the actual commit SHA, Action run URLs and deployment URL in
   `docs/RELEASE_CHECKS.md` and evidence JSON after successful publication.

Expected showcase: <https://bj-liu.github.io/resumeagent/>.

## Local candidate

```bash
python scripts/prepare_release.py
```

This creates `release-dist/resumeagent-source.zip`, checksums, a file manifest and
a value-redacted secret-audit summary. The explicit allowlist excludes private
configuration and runtime data. Review the candidate rather than uploading the
entire workspace or its private backup. The original user files, generated pages
and historical reports remain on disk; excluding them from a new public package
does not delete them. Existing public remote demo videos are not newly uploaded
or relabeled as a current recording.
