# The CyberiadaPro Git Plugin Interface Specification

Document version: 0.1 (2026-11-10)

The interface of `hsm_git`: the command line the editor plugin runs, its exit
codes, the text of a diff, the commit session and the Python functions behind
them. The reasons are in `ARCHITECTURE.md`.

## The command line

    hsm-git stage DOCUMENT
    hsm-git unstage DOCUMENT
    hsm-git commit DOCUMENT --message-file FILE
    hsm-git commit DOCUMENT --session [--request FILE]
    hsm-git diff DOCUMENT [--current FILE] [--revision=REV] [--geometry]
    hsm-git --install-editor-plugin [DIR]

`python3 -m hsm_git` is `hsm-git`. `DOCUMENT` is the diagram file; git runs in
its directory.

* `stage` - `git add` of the file; prints its status line.
* `unstage` - takes the file out of the index, the file kept; prints its
  status line, or `nothing to unstage`.
* `commit --message-file FILE` - commits the index with the first line of
  FILE (UTF-8) as the message; prints the branch and the staged files, then
  git's output.
* `commit --session` - the commit session on stdin and stdout (see The commit
  session); `--request` is the `request.json` of the editor, read for
  `document.modified`.
* `diff` - prints the changes of the diagram since the revision (`HEAD` by
  default); `--current FILE` is the diagram to compare, the editor's
  `${input}` (DOCUMENT itself without it); `--geometry` adds the geometry, the
  ids and the view state.
* `--install-editor-plugin [DIR]` - copies `editor-plugin` into DIR or into
  the user plugin folder of CyberiadaPro, bound to the Python that runs it.

| Exit code | Meaning |
|---|---|
| 0 | done: staged, unstaged, committed, the diff printed (changes or none) |
| 1 | the commit declined or the session stopped: nothing committed |
| 2 | a usage error |
| 3 | nothing is staged |
| 4 | git, the repository, the revision or a diagram failed |

A failure prints one line on stderr, `git: <document>: <what>`, and git's own
stderr when git failed; nothing is printed on stdout after it.

## The text of a diff

```
--- HEAD:diagrams/light.graphml
+++ working
  state Red
-   entry: led.on(RED)
+   entry: led.on(RED)
+          buzzer.beep()
- state Green
-   entry: led.on(GREEN)
+ state Blink
+   entry: led.blink()
  transition Red -> Yellow [TICK]
-   do: timer.start(3000)
+   do: timer.start(2000)
  meta
-   platform: ArduinoUno
+   platform: ArduinoNano
3 changed, 1 added, 1 removed
```

* The header: `--- <revision>:<path>`, the path in the repository (the old
  path of a staged rename; `--- /dev/null (<path> is not in <revision>)` for a
  new file), and `+++ working`.
* A line starts with `  ` (the context: the element a change belongs to),
  `- ` (only in the revision) or `+ ` (only in the diagram), then two spaces
  per level of nesting.
* The elements, one line each: `state machine <name>` (only when the document
  has several or the machine itself changed), `state <name>`, `initial`,
  `final <name>`, `choice <name>`, `terminate`, `shallow history`,
  `deep history`, `entry point <name>`, `exit point <name>`,
  `submachine <name> -> <machine>`, `region <name>`, `comment`,
  `formal comment <name>`, `transition <source> -> <target> [<trigger>]`
  (without the brackets for a transition with no trigger),
  `link <comment> -> <element>`, `meta`. A name the document repeats gets the
  id: `state Idle (n7)`.
* The lines of an element, a level deeper: `entry:`, `exit:`, an internal
  transition `<trigger> [<guard>]: <behaviour>`, `guard:`, `do:`,
  `propagation:`, `in: <parent>` (the element moved), `color:`, `text:` (a
  comment), `<name>: <value>` (meta); with `--geometry` also `at:`,
  `route:`, `label:` and `id:`. A behaviour of several lines continues
  under its first one.
* An added or removed element is printed with all its lines and the elements
  inside it. A changed one is printed as the context with its differing
  lines, each differing line printed whole - a behaviour with all its lines -
  the old one `- `, then the new one `+ `; a renamed or re-targeted element
  gets its old line `- ` and its new line `+ ` instead of the context.
* The order: the elements of the diagram from the top down, the removed ones
  after the present children of their former parent, the transitions after the
  states of their machine, `meta` last.
* The last line counts the elements: `<n> changed, <n> added, <n> removed`,
  or `no changes since <revision>`.

## The commit session

The session is the supervised session of the editor (`PLUGIN-API.md`,
Sessions), JSON-RPC 2.0, one object per line.

| Direction | Message | Content |
|---|---|---|
| editor -> | `initialize` | replied `{"kind": "supervised", "controls": []}`: Stop only |
| -> editor | `state` | `running` with `text` (`reading the index`, `committing`), `waiting` while asking, `finished` with `committed <hash>` |
| -> editor | `log` | a staged file per message, `<status>  <path>`; git's output; a failure with `level: error` |
| -> editor | `ask` | `Commit <n> staged file(s) to <branch>? The answer is the message.`, the files below, and `<file> has unsaved edits: they are not committed.` when so |
| editor -> | the reply `accept` | the message: committed; an empty one is asked again; a changed index is listed and asked again |
| editor -> | the reply `decline`, `cancel`, `shutdown` | nothing committed, exit 1 |

At most `ASK_LISTED_FILES` files are listed in the question, then
`... and <n> more`; the log lists them all. Nothing staged ends the session
before the question with exit 3.

## Python modules

### `hsm_git.repo`

* `Repository.locate(document)` - the repository of a diagram file; raises
  `GitError` outside a work tree.
* `Repository.top`, `.path` (the file in the repository, with `/`),
  `.branch` (the branch, or `detached at <hash>`), `.has_commits`.
* `Repository.staged()` - the staged changes: a list of `(status, path)`.
* `Repository.revision(rev)` - the commit hash of a revision; raises
  `GitError` when there is none.
* `Repository.blob(commit, out)` - writes the file of the commit into `out`;
  returns the path it had there, or `None` when it is not in the commit.

### `hsm_git.diff`

* `load(path)` - the document of a file in any format the library reads; a
  missing or empty file is an empty document.
* `compare(old, new, geometry=False)` - the `CyberiadaML.DocumentDiff` of two
  documents.
* `text(old, new, result, revision, geometry=False)` - the lines of the diff
  after its header: the elements and the summary.

### `hsm_git.git`

* `run(args, cwd, stdin=None)` - runs git; returns the exit code, stdout as
  bytes and stderr as text.
* `GitError` - a failed git call or a refused input; its text is the one line
  printed.
