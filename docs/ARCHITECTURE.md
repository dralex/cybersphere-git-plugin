# The CyberiadaPro Git Plugin Architecture

Document version: 0.3 (2026-11-11)

The plugin brings the git repository of the open diagram into the CyberiadaPro
editor: it stages and unstages the diagram, commits the index after showing
what goes into the commit, and shows what changed in the diagram since a
revision - state by state and transition by transition, not line by line of
the GraphML file: as text, or on the canvas of a diff tab of the editor.

The plugin runs git as a program and compares the diagrams with the document
diff of libcyberiadaml, reached through the `CyberiadaML` module of
libcyberiadamlpp-py: it finds the files and the revision and writes the text,
it never matches the elements of two diagrams itself; for a diff tab it only
hands the revision to the editor, which compares with the same library. It
depends on git, the `CyberiadaML` module (for the text diff only) and the
Python 3 standard library.

```
 CyberiadaPro                      hsm_git (python3 -m hsm_git)            git
+----------------------------+   +--------------------------------+   +------------+
| Plugins > Git: greyed out  |   | cli.py      the commands       |   | rev-parse  |
| by requires, when, modes   |   |                                |   | add        |
|                            |-->| repo.py     the work tree, the |-->| restore    |
| argv, ${document},         |   |             path, the revision |   | commit     |
| ${input}, ${request}       |   |                                |<--| cat-file   |
|                            |<--| actions.py  stage, unstage,    |   | diff       |
| the output tab: stdout     |   |             the commit         |   +------------+
|                            |   |                                |     -C <dir>,
| the session tab: the       |<=>| session.py  the commit         |     -z output
| question and the answer    |   |             question           |
|                            |   |                                |
| the diff tab: ${output},   |<--| diff.py     the text of a      |
| the revision as the base   |   |             diff, the revision |
+----------------------------+   +--------------------------------+
                                                  | old.diff(new)
                                                  v
                                 +--------------------------------+
                                 | CyberiadaML: Document.diff     |
                                 | libcyberiadamlpp -> the        |
                                 | libcyberiadaml document diff:  |
                                 | the pairs of elements and what |
                                 | differs in each pair           |
                                 +--------------------------------+
```

## Usage requirements

| No | Requirement | Section |
|---|---|---|
| R1 | Be offered only where the actions can work: git installed, the document a file in a git work tree; Stage only for a saved diagram. | Conditions |
| R2 | Stage the saved diagram; unstage it, its file kept as it is. | Stage and unstage |
| R3 | Commit the whole index after showing the branch and the staged files; the message is the answer; a decline commits nothing. | The commit |
| R4 | Show the changes of the diagram since a revision (`HEAD` by default), the unsaved edits included, as text by the elements of the diagram. | The diff |
| R5 | Read the revision in every format the library reads: CyberiadaML-GraphML and the yEd dialects. | The diff |
| R6 | Run from the command line and as an editor plugin; ask nothing on stdin outside the session. | The command line, The plugin |
| R7 | Run on Python 3.8+ and git 2.23+, on Linux, Windows and macOS. | Testing |
| R8 | Show the same changes on the canvas: a diff tab of the editor, the revision against the diagram with its unsaved edits. | The compare |

## Conditions

The editor greys an action out, with the reason in its tooltip, when a
condition the plugin declares fails (`PLUGIN-API.md`, Conditions). What only
git can tell stays in the run.

| Condition | Declared | Checked by |
|---|---|---|
| git is installed | `requires.programs: ["git"]` | the editor, at the scan (`EDIT-PLUG-50`) |
| the document is a file in a git work tree | `when: ["git"]` | the editor: a `.git` directory in the file's directory or above it, no process (`EDIT-PLUG-55`) |
| Stage: the diagram is saved | `when: ["saved", "git"]` | the editor (`EDIT-PLUG-52`) |
| the tab holds a diagram, edited or inspected | `modes: ["hsm", "fa", "inspection"]` | the editor (`EDIT-PLUG-56`) |
| the work tree of the file, the revision, a staged change | - | the run: one line on stderr, the exit code |

The editor looks for the folder instead of running `git rev-parse`, so that
no process starts at every edit and selection. The run decides: a `.git`
folder of an unrelated repository above the file (a home directory under
git) or an ignored file fail there with git's own message.

## The repository of a document

```
 ${document}  ->  D = its directory
 git -C D rev-parse --show-toplevel            the work tree     (exit 128: not in one)
 git -C D rev-parse --show-prefix              the path of the file in the repository:
                                               the prefix + the base name, with '/'
 git -C D symbolic-ref --short -q HEAD         the branch        (else: detached at <hash>)
 git -C D rev-parse --verify -q HEAD^{commit}  the first commit made or not
```

* Every call runs `git -C D` with stdin closed (in the session stdin is the
  channel of the editor), `GIT_TERMINAL_PROMPT=0` and
  `GIT_LITERAL_PATHSPECS=1`.
* Only the `-z` output of git is parsed, never its messages: they are
  localized, and they pass to stderr as they are.
* The paths of git are compared with the paths of git only, so the
  `C:/...` form on Windows needs no conversion.

## Stage and unstage

| Action | git | The run |
|---|---|---|
| Stage | `git add -- NAME` | the diagram is saved (`when: saved`), so the file is what the editor shows; an ignored file fails with git's message |
| Unstage | `git restore --staged -- NAME`; before the first commit `git rm --cached -q -- NAME` | the file is kept; nothing staged for it prints `nothing to unstage` |

Both print the status of the file afterwards, as `git status --short` does:
`M  diagrams/light.graphml`.

## The commit

The commit takes the whole index: the diagram and every other staged file. A
session asks first, so the user sees what goes in and on which branch.

```
 editor                                          hsm_git commit --session
   | -- initialize ------------------------------> |
   | <-- {kind: supervised, controls: []} -------- |
   |                                               | git diff --cached --raw -z -M
   |                                               |   nothing staged: one line, exit 3
   | <-- log: the staged files, one per line ----- |
   | <-- ask: Commit 2 staged files to devel? ---- |   + the files, + a warning when
   |                                               |     the diagram has unsaved edits
   | -- accept {text: the message} --------------> |   empty: asked again
   |                                               |   the index changed: listed and
   |                                               |     asked again
   |                                               | git commit -F -  (the message on stdin)
   | <-- log: [devel 3f2a9c1] blink at night ----- |
   | <-- state {status: finished} ---------------- |   exit 0
   |                                               |
   | -- decline, cancel, shutdown ---------------> |   nothing committed, exit 1
```

* The message is one line: the answer line of the editor is one line.
* The document is locked while the question is open (`EDIT-PLUG-41`).
* The unsaved edits are not committed: `document.modified` of `request.json`
  adds the warning to the question.
* The hooks run without a terminal: a hook that needs one, or a signing key
  asking its passphrase on a terminal, fails the commit (exit 4, git's
  message in the output tab).
* An editor before the sessions shows the one-shot Commit... instead (the
  session action `replaces` it): a dialog with the message, the same list
  printed before git's output, no question.

## The diff

The diff compares the diagram as the editor shows it - `${input}`, the
unsaved edits included - with the file in a revision, `HEAD` by default.

```
 git rev-parse --verify -q REV^{commit}       ${input}: the editor's copy,
 git cat-file blob HASH:PATH                  CyberiadaML-GraphML 1.0
   -> revision.graphml, in any format                 |
            |                                         |
            v                                         v
 CyberiadaML.LocalDocument.open        CyberiadaML.LocalDocument.open
            |                                         |
            +------ old.diff(new, DiffOptions) -------+
                               |
                               v                the pairs of elements:
                    hsm_git.diff.text(...)      revision only, document only,
                               |                or both with what differs
                               v
                      the output tab: --- HEAD:diagrams/light.graphml
                                      +++ working
```

* `git cat-file blob` gives the stored file exactly: no text conversion, no
  filters, no pager.
* A file not in the revision is looked up as a staged rename
  (`git diff --cached -M --name-status HASH`); without one the diff is
  against an empty document, everything added.
* The library pairs the elements of the two documents and tells what differs
  in each pair; the plugin writes the pairs as text (`API.md`, The text of a
  diff). The geometry, the ids and the editor's own metainformation - the
  view state and the `regionGeometry` marker it writes at a save - are left
  out unless the Geometry option is on, as in the diff tab of the editor, so
  the two show the same pairs.
* The comparison needs `Document.diff` of the binding: without it the diff
  fails with one line naming the package; the other actions work without
  `CyberiadaML`.

## The compare

The compare shows the same changes on the canvas: the plugin finds the file of
the revision, the editor opens a diff tab with it as the base and the tab's
unsaved copy as the target, and pairs the elements itself (`MODES.md` of the
editor, The diff tab).

```
 editor: Compare with a                    hsm-git revision DOC
 Revision... (result: diff)                  --revision=REV --output F
   | -- ${document}, revision, ${output} --> |
   |                                         | git rev-parse --verify REV^{commit}
   |                                         | git cat-file blob HASH:PATH -> F
   |                                         |   a staged rename: the old path
   |                                         |   not in REV: F left empty
   | <-- exit 0; stdout: REV:PATH ---------- |
   v
 a diff tab "light.graphml ↔ HEAD": base = F, target = the ${input}
 snapshot, paired by Document::diff; Refresh runs the action again
```

* The revision file is the one of the text diff: `cat-file blob`, the rename
  lookup, an empty document for a file the revision lacks. The two share the
  code, so the tab and the text name the same revision.
* The run needs no `CyberiadaML`: the editor reads the file in any format the
  library reads, and its pairs are those `hsm-git diff` prints.
* The tab is labelled by the revision parameter (`HEAD`). Refresh runs the
  action again, so after a commit `HEAD` is the new revision.
* The geometry is the tab's own option (Document > Geometry), not a parameter.
* An editor before the diff tabs rejects a descriptor with a `diff` result
  (`PLUGIN-API.md`, Results): the Debian package `Breaks` the editors without
  them (the version is set at the release, `ChangeLog.md`), and the plugin
  keeps the text diff for every editor.

## The command line

    hsm-git stage DOCUMENT
    hsm-git unstage DOCUMENT
    hsm-git commit DOCUMENT --message-file FILE
    hsm-git commit DOCUMENT --session [--request FILE]
    hsm-git diff DOCUMENT [--current FILE] [--revision=REV] [--geometry]
    hsm-git revision DOCUMENT [--revision=REV] --output FILE
    hsm-git --install-editor-plugin [DIR]

`python3 -m hsm_git` is `hsm-git`. The exit codes and the formats are in
`API.md`.

## The plugin

`editor-plugin/plugin.json` is the plugin `git` (Plugins > Git).

| Action | Kind | When | Runs |
|---|---|---|---|
| Stage | one-shot, log | `saved`, `git` | `stage ${document}` |
| Unstage | one-shot, log | `git` | `unstage ${document}` |
| Commit... | session, supervised | `git` | `commit ${document} --session --request ${request}` |
| Commit... | one-shot, log; replaced by the session | `git` | `commit ${document} --message-file ${param-file:message}` |
| Changes Since a Revision... | one-shot, log | `git` | `diff ${document} --current ${input} --revision=${param:revision}` |
| Compare with a Revision... | one-shot, diff | `git` | `revision ${document} --revision=${param:revision} --output ${output}` |

* Every action lists `modes: ["hsm", "fa", "inspection"]`: an inspected
  diagram is staged and compared as an edited one; the text and the diff tabs
  get no git action.
* No action saves the document: Stage needs it saved, the diffs read
  `${input}`, the commit warns. `cwd: document` is not used because it saves.
* `--revision=` is joined to its value, so that a revision cannot become an
  option; a revision starting with `-` is refused.
* `hsm-git --install-editor-plugin [DIR]` copies the plugin into the user
  plugin folder of the editor bound to the Python that runs it (after
  `fad/plugin.py` of fa-dispatcher-py).

## Code layout

| Module | Holds |
|---|---|
| `hsm_git/__init__.py` | the version, the exit codes, the errors |
| `hsm_git/__main__.py` | `python3 -m hsm_git` |
| `hsm_git/cli.py` | the command line |
| `hsm_git/git.py` | running git: the environment, the bytes, the errors |
| `hsm_git/repo.py` | the repository of a document: the work tree, the path, the branch, the staged files, the revision, the blob |
| `hsm_git/actions.py` | stage, unstage, the one-shot commit |
| `hsm_git/session.py` | the commit session (JSON-RPC 2.0 over stdin and stdout) |
| `hsm_git/diff.py` | the revision file, the documents of a diff and its text |
| `hsm_git/plugin.py` | the installation of the editor plugin |

## Testing

* `test/run.py` - the actions and the diff on temporary repositories made by
  the test, with a git configuration of their own (no user or system
  configuration leaks in); the text of the diff of the example diagrams is
  compared with `test/good/`; `revision` writes the stored file, the old one
  of a staged rename, an empty one for a new file.
* `test/session_test.py` - the commit session driven over its pipes: accept,
  decline, an empty answer, a stop during the question, nothing staged.
* `test/plugin_test.py` - the plugin in the batch mode of CyberiadaPro:
  the list of the plugins, Stage, the diff, the commit session from a session
  script; skipped without an editor that starts, or with one before the `git`
  token. The compare: the `== diff` section of `--run-plugin git:compare
  --dump` against `test/good/`, its pairs those of the text diff; skipped with
  an editor before the diff tabs.
* A test without git, or a diff test without `Document.diff`, is skipped
  (exit 77).

## Stages

1. 0.1: Stage, Unstage, the commit with its question, the diff against a
   revision as text, Compare with a Revision... in a diff tab of the editor
   (an editor with the diff tabs, `EDIT-PLUG-58`).

## Open questions

* A message of several lines needs an answer box of several lines in the
  editor.
* `git diff` and `git log -p` on the command line could show the diagrams as
  the same text (a `textconv` driver), not in 0.1.
* The messages of the run are English; they could follow
  `CYBERIADA_PRO_LANGUAGE`.
