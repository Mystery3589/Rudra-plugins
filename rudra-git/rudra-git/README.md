# rudra-git

An advanced git workflow plugin for [rudra](https://github.com/Mystery3589/rudra).

## Install

```bash
rudra plugin install rudra-git
# or from local clone:
rudra plugin install ./rudra-git
```

## Commands

```
rudra git status          Rich colour-coded status
rudra git status --short  One-liner branch + sync state
rudra git info            Full repo dashboard

rudra git branch                    List branches
rudra git branch feature/x          Create + switch
rudra git branch feature/x --from main
rudra git branch old-thing -d       Delete merged
rudra git branch --clean            Delete all merged branches

rudra git commit "message"          Smart commit with staging check
rudra git commit --conv             Interactive conventional commit builder
rudra git commit --amend            Amend last commit
rudra git commit --amend --no-edit  Amend without changing message
rudra git commit "msg" --push       Commit + push in one shot
rudra git fixup <hash>              Create fixup commit (pick from log if omitted)
rudra git fixup --rebase            Fixup + immediate autosquash

rudra git sync                      Pull (rebase), auto-stash dirty tree
rudra git sync --push               Pull then push
rudra git sync --upstream           Fork workflow: pull upstream → push origin
rudra git push                      Push current branch
rudra git pull                      Pull current branch

rudra git log                       Rich commit table
rudra git log --graph               Branch graph
rudra git log --file src/x.py       File history
rudra git log --patch               Full diff view
rudra git file-log src/x.py         File history with rename tracking

rudra git undo                      Soft undo last commit (keep staged)
rudra git undo 3                    Undo 3 commits
rudra git undo --hard               Hard reset (destructive)
rudra git restore src/x.py          Discard changes to file
rudra git restore --staged          Unstage files
rudra git reset HEAD~2 --soft       Reset to ref

rudra git stash "wip: ..."          Stash with name
rudra git stash-pop                 Pop (prompts if multiple)
rudra git stash-apply               Apply without removing
rudra git stash-list                List with index numbers
rudra git stash-drop --all          Clear the whole stack

rudra git remote                    Inspect/fix 'origin' (SSH↔HTTPS)
rudra git remote --all              All remotes
rudra git remote --ssh              Force SSH
rudra git remote --add <url>        Add a new remote, auto-converts

# Fun / automation commands
rudra git wip                       Commit everything as WIP, switch context
rudra git wip --push                WIP + push
rudra git unwip                     Undo the last WIP commit cleanly
rudra git ship "feat: login"        sync → check → commit → push in one flow
rudra git ship --check "pytest"     Run tests before shipping
rudra git oops                      Fix last commit (forgotten file / typo)
rudra git oops -m "fix: typo"       Also fix the message
rudra git nuke feature/old          Delete branch locally + remote 💥
rudra git yeet                      Force-push with dramatic confirmation 🚀
rudra git panic                     Something broke — interactive recovery menu 😱
rudra git contrib                   Contribution stats by author
rudra git contrib --since "3 months ago"
rudra git time-travel               Pick any commit, go there 🕰️
rudra git time-travel --file x.py   Restore one file from any commit
rudra git changelog                 Auto-generate changelog since last tag
rudra git changelog --output CHANGELOG.md
```
