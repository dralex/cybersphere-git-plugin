# The CyberiadaPro Git Plugin Interface Specification

Document version: 0.4 (2026-11-12)

The interface of `hsm_git`: the command line the editor plugin runs, its exit
codes, the text of a diff of a diagram and of a text, the findings, the
revision file of a diff tab, the history, the listing of the textconv driver,
the commit session and the Python functions behind them. The reasons are in `ARCHITECTURE.md`.

## The command line

    hsm-git stage DOCUMENT
    hsm-git unstage DOCUMENT
    hsm-git commit DOCUMENT --message-file FILE
    hsm-git commit DOCUMENT --session [--request FILE]
    hsm-git diff DOCUMENT [--current FILE] [--revision=REV | --index] [--geometry]
                 [--diagnostics FILE]
    hsm-git revision DOCUMENT [--revision=REV | --index] --output FILE
    hsm-git history DOCUMENT [--count N]
    hsm-git textconv FILE
    hsm-git --install-editor-plugin [DIR]

`python3 -m hsm_git` is `hsm-git`. `DOCUMENT` is the diagram or the text file;
git runs in its directory.

* `stage` - `git add` of the file; prints its status line.
* `unstage` - takes the file out of the index, the file kept; prints its
  status line, or `nothing to unstage`.
* `commit --message-file FILE` - commits the index with the first line of
  FILE (UTF-8) as the message; prints the branch and the staged files, then
  git's output.
* `commit --session` - the commit session on stdin and stdout (see The commit
  session); `--request` is the `request.json` of the editor, read for
  `document.modified`.
* `diff` - prints the changes of the file since the revision (`HEAD` by
  default) or against the index (`--index`); `--current FILE` is the file to
  compare, the editor's `${input}` (DOCUMENT itself without it). A `.graphml`
  file is compared as a diagram (The text of a diff), any other as a text (The
  text of a line diff). `--geometry` adds the geometry, the ids and the
  editor's own metainformation (the view state, the `regionGeometry` marker)
  of a diagram, left out without it as in the editor's diff tab.
  `--diagnostics FILE` also writes the changes as findings (The findings).
* `revision` - writes the diagram as the revision (`HEAD` by default) stored
  it into FILE, the editor's `${output}` of a `diff` result: the old path of a
  staged rename, an empty FILE when the diagram is not in the revision (or
  the repository has no commit yet); prints `<revision>:<path>`, or
  `<path> is not in <revision>`. `--index` writes the staged file instead:
  `index:<path>`, or `<path> is not in the index`; an unmerged file fails.
  Needs no `CyberiadaML`.
* `history` - prints the last N commits of the file (30 by default), a staged
  rename followed: `<hash>  <date>  <author>  <subject>` per commit, the
  newest first, or `<path> has no commits`.
* `textconv` - prints the diagram FILE as its listing (The listing), the
  textconv driver of git; a file it cannot read is printed as it is, with one
  warning line on stderr, and the exit code is 0.
* `--install-editor-plugin [DIR]` - copies `editor-plugin` into DIR or into
  the user plugin folder of CyberiadaPro, bound to the Python that runs it.

| Exit code | Meaning |
|---|---|
| 0 | done: staged, unstaged, committed, the diff printed (changes or none), the revision written (empty or not), the history or the listing printed |
| 1 | the commit declined or the session stopped: nothing committed |
| 2 | a usage error |
| 3 | nothing is staged |
| 4 | git, the repository, the revision, the index (an unmerged file) or a diagram failed |

A failure prints one line on stderr, `git: <document>: <what>`, and git's own
stderr when git failed; nothing is printed on stdout after it.

The messages of the run - the failures, the status lines, the history, the
commit session - follow `CYBERIADA_PRO_LANGUAGE` (`ru`: Russian; English
otherwise). The text of a diff, its findings and the listing are a format and
stay English.

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
  new file), and `+++ working`; against the index `--- index:<path>` and
  `--- /dev/null (<path> is not in the index)`.
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
  or `no changes since <revision>` (`no changes since the index`).

## The text of a line diff

A text - a file that is not `.graphml` - is compared line by line:

```
--- HEAD:docs/notes.md
+++ working
@@ -1,3 +1,4 @@
 # Notes
-the light is red
+the light blinks
+at night
 the end
lines: 2 added, 1 removed
```

* The header is that of a diagram.
* The hunks are those of `diff -u` with 3 lines of context; the lines are
  compared without their line ends, the base read as UTF-8 with an undecodable
  byte replaced.
* The last line counts the lines: `lines: <n> added, <n> removed`, or
  `no changes since <revision>`.

## The findings

`--diagnostics FILE` writes the diagnostics file of the editor
(`PLUGIN-API.md`, The diagnostics file): a JSON array, one finding per changed
element of a diagram or per changed block of a text, in the order of the text.

```json
[
  {"severity": "info", "rule": "changed", "element": "n1",
   "message": "state Red changed: color"},
  {"severity": "info", "rule": "added", "element": "n3", "message": "state Blink added"},
  {"severity": "info", "rule": "removed", "message": "state Green removed"},
  {"severity": "info", "rule": "changed", "line": 2, "message": "line 2 changed"}
]
```

* `rule` is `added`, `changed` or `removed`.
* A diagram: `element` is the id in the compared diagram (`--current`); a
  removed element has none. The message is the line of the element in the text
  of a diff, then `added`, `removed`, or `changed` with the names of the
  differing lines (`entry`, `do`, `in`, ...); a renamed or re-targeted element
  adds `(was <its old line>)`. The metainformation is `meta changed: <names>`.
* A text: `line` is the first line of the block in the compared text (a
  removed block: the line after it); the message is `line <a> changed`,
  `lines <a>-<b> added`, `<n> line(s) removed`.
* No change writes an empty array.

## The listing

`hsm-git textconv FILE` prints the text of a diff of FILE against an empty
document without its header, its marks and its summary:

```
state machine Light
  state Red
    entry: led.on(RED)
  initial
  transition Red -> Yellow [TICK]
meta
  platform: ArduinoUno
```

* The order and the lines are those of The text of a diff; the geometry, the
  ids and the editor's own metainformation are left out.
* An empty FILE prints nothing.

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
* `Repository.index_blob(out)` - writes the staged file into `out`; returns
  its path, or `None` when the index lacks it; raises `GitError` for an
  unmerged file.
* `Repository.history(count)` - the last commits of the file, a staged rename
  followed: a list of `(hash, date, author, subject)`.

### `hsm_git.diff`

* `base(repo, revision, out)` - writes the diagram of the revision into
  `out`, empty when it is not there; returns its path in the repository, or
  `None`. The base of both `diff` and `revision`; needs no `CyberiadaML`.
* `base_index(repo, out)` - the same for the index.
* `fetch(repo, revision, out)` - `base` or, for a `None` revision,
  `base_index`; returns the path, the label and the name of the base.
* `load(path)` - the document of a file in any format the library reads; a
  missing or empty file is an empty document.
* `compare(old, new, geometry=False)` - the `CyberiadaML.DocumentDiff` of two
  documents.
* `changes(old, new, result, revision, geometry=False)` - the lines of the
  diff after its header (the elements and the summary) and its findings.
* `text(old, new, result, revision, geometry=False)` - the lines only.
* `listing(document)` - the lines of the listing of a document.

### `hsm_git.textdiff`

* `text(old, new, revision, findings=None)` - the lines of the line diff of
  two lists of lines after its header, and its findings.

### `hsm_git.i18n`

* `tr(text)` - the text in the language of `CYBERIADA_PRO_LANGUAGE`, the
  English text without a translation.

### `hsm_git.git`

* `run(args, cwd, stdin=None)` - runs git; returns the exit code, stdout as
  bytes and stderr as text.
* `GitError` - a failed git call or a refused input; its text is the one line
  printed.
