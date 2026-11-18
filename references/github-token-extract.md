# Extracting GitHub Token from Windows Credential Manager

When pushing to GitHub from a Windows environment, the token may be stored in the Windows Credential Manager (`wincred`) under the `git:https://github.com` target.

## Method 1: `git credential fill` (recommended)

This method asks the git credential helper (Git Credential Manager / Windows Credential Manager) to return the stored credentials:

```bash
git credential fill <<< "protocol=https
host=github.com
username=hylal
"
```

Output (example):

```
protocol=https
host=github.com
username=hylal
password=ghp_xxxxxxxxxxxxxxxxxxxx
```

Extract the `password=` line and use it as the GitHub token.

**Note:** Do not use `--dry-run` — the credential helper will not return the password. Use plain `git credential fill` without `--dry-run`.

## Method 2: PowerShell

```powershell
cmdkey /list
# Find the entry for "git:https://github.com"
cmdkey /delete:git:https://github.com
# Then authenticate interactively
```

## Security Notes

- The token is sensitive — never echo it to the terminal or log it.
- Store it in `.env` (added to `.gitignore`) or use CI secrets on GitHub.
- For local development, `git config --global credential.helper manager` or `manager-core` enables Windows Credential Manager integration.
