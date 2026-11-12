# The CyberiadaPro Git Plugin Architecture

Document version: 0.4 (2026-11-12)

The plugin brings the git repository of the open diagram into the CyberiadaPro
editor: it stages and unstages the diagram, commits the index after showing
what goes into the commit, and shows what changed in the diagram since a
revision or against the index - state by state and transition by transition,
not line by line of the GraphML file: as text linked to the elements, or on the
canvas of a diff tab of the editor. A text in a text tab of the editor is
staged, committed and compared line by line; `git diff` on the command line
shows the diagrams by their elements too.

The plugin runs git as a program and compares the diagrams with the document
diff of libcyberiadaml, reached through the `CyberiadaML` module of
libcyberiadamlpp-py: it finds the files and the revision and writes the text,
it never matches the elements of two diagrams itself; for a diff tab it only
hands the revision to the editor, which compares with the same library. It
depends on git, the `CyberiadaML` module (for the text diff of a diagram and
the textconv only) and the Python 3 standard library.

```
 CyberiadaPro                      hsm_git (python3 -m hsm_git)            git
+----------------------------+   +--------------------------------+   +------------+
| Plugins > Git: greyed out  |   | cli.py      the commands       |   | rev-parse  |
| by requires, when, modes   |   |                                |   | add        |
|                            |-->| repo.py     the work tree, the |-->| restore    |
| argv, ${document},         |   |             path, the revision,|   | commit     |
| ${input}, ${request},      |   |             the index, the log |<--| cat-file   |
| CYBERIADA_PRO_LANGUAGE     |   |                                |   | ls-files   |
|                            |<--| actions.py  stage, unstage,    |   | diff, log  |
| the output tab: stdout     |   |             the commit, history|   +------------+
|                            |   |                                |     -C <dir>,
| the session tab: the       |<=>| session.py  the commit         |     -z output
| question and the answer    |   |             question           |
|                            |   |                                |
| the diff tab: ${output},   |<--| diff.py     a diagram: the     |
| the revision as the base   |   |             base, the text,    |
|                            |   |             the findings,      |
| Diagnostics: ${diagnostics}|<--|             the listing        |
| a click: the element, the  |   |                                |
| line of a text tab         |<--| textdiff.py a text: the lines  |
|                            |   |                                |
|                            |   | i18n.py     the run messages   |
+----------------------------+   +--------------------------------+
                                       | old.diff(new)        ^
                                       v                      | hsm-git textconv FILE
                         +---------------------------+   +-----------------------+
                         | CyberiadaML: Document.diff|   | git diff, git log -p  |
                         | the pairs of elements and |   | (diff=cyberiada in    |
                         | what differs in each pair |   | .gitattributes)       |
                         +---------------------------+   +-----------------------+
```

## Usage requirements

| No | Requirement | Section |
|---|---|---|
| R1 | Be offered only where the actions can work: git installed, the document a file in a git work tree; Stage only for a saved document. | Conditions |
| R2 | Stage the saved document; unstage it, its file kept as it is. | Stage and unstage |
| R3 | Commit the whole index after showing the branch and the staged files; the message is the answer; a decline commits nothing. | The commit |
| R4 | Show the changes of the diagram since a revision (`HEAD` by default), the unsaved edits included, as text by the elements of the diagram. | The diff |
| R5 | Read the revision in every format the library reads: CyberiadaML-GraphML and the yEd dialects. | The diff |
| R6 | Run from the command line and as an editor plugin; ask nothing on stdin outside the session. | The command line, The plugin |
| R7 | Run on Python 3.8+ and git 2.23+, on Linux, Windows and macOS. | Testing |
| R8 | Show the same changes on the canvas: a diff tab of the editor, the revision against the diagram with its unsaved edits. | The compare |
| R9 | Link each change to the element of the edited diagram, or to the line of a text: a click in the Diagnostics of the editor goes there. | The findings |
| R10 | Compare with the index, as text and in a diff tab: what the commit takes against the edits. | The index |
| R11 | Stage, unstage, commit, the history and a line diff for the texts of the text tabs of the editor. | Text tabs |
| R12 | Show the commits of the file, a rename followed. | The history |
| R13 | Show the diagrams by their elements in `git diff` and `git log -p` on the command line. | The textconv |
| R14 | Write the messages of the run in the language of the editor: English, Russian. | The messages |

## Conditions

The editor greys an action out, with the reason in its tooltip, when a
condition the plugin declares fails (`PLUGIN-API.md`, Conditions). What only
git can tell stays in the run.

| Condition | Declared | Checked by |
|---|---|---|
| git is installed | `requires.programs: ["git"]` | the editor, at the scan (`EDIT-PLUG-50`) |
| the document is a file in a git work tree | `when: ["git"]` | the editor: a `.git` directory in the file's directory or above it, no process (`EDIT-PLUG-55`) |
| Stage: the document is saved | `when: ["saved", "git"]` | the editor (`EDIT-PLUG-52`) |
| the tab holds a diagram, edited or inspected, or a text | `modes` (see The plugin) | the editor (`EDIT-PLUG-56`) |
| the work tree of the file, the revision, a staged change, an unmerged index | - | the run: one line on stderr, the exit code |

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
| Stage | `git add -- NAME` | the document is saved (`when: saved`), so the file is what the editor shows; an ignored file fails with git's message |
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
   |                                               |     the document has unsaved edits
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
unsaved edits included - with the file in a revision, `HEAD` by default, or
in the index.

```
 git rev-parse --verify -q REV^{commit}       ${input}: the editor's copy,
 git cat-file blob HASH:PATH                  CyberiadaML-GraphML 1.0
 (--index: the blob of ls-files --stage)              |
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
                      ${diagnostics}: a finding per changed element
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
* The compared file decides the kind: a `.graphml` file is a diagram, any
  other a text (see Text tabs). The editor writes `${input}` as
  `input.graphml` for a diagram and `input.<ext>` for a text.

## The findings

The diff also writes its changes as the findings of the editor
(`PLUGIN-API.md`, The diagnostics file), so the Diagnostics dock lists them
and a click selects the changed element on the canvas, or goes to the
changed line of a text tab.

```
 hsm-git diff ... --diagnostics ${diagnostics}
   Writer.node / transition / link / machine / meta -- one finding per element
     {severity: info, rule: added | changed | removed,
      element: the id in the edited diagram, message: "state Red changed: entry"}
   textdiff: one finding per changed block of lines, {line: its first line}
```

* An added or changed element links to its id in the edited diagram; a
  removed one is not there, so its finding has no link.
* The messages use the words of the text of a diff: they stay English, as the
  text does.
* The output tab keeps the text: the findings add the links, they do not
  replace it.

## The index

The index is a base as a revision is: what the commit takes, compared with the
edits of the tab.

```
 git ls-files --stage -z -- PATH
   no entry           -> an empty base: "PATH is not in the index"
   stage 0 entry      -> git cat-file blob HASH -> the base file
   stage 1..3 entries -> the file is unmerged: one line, exit 4
```

* `hsm-git diff --index` and `hsm-git revision --index` take the index
  instead of a revision; the header names it `index:PATH`.
* Compare with the Index (result `diff`) opens a diff tab with the index as
  the base. The action has no string parameter, so the editor labels the base
  by the action: `light.graphml ↔ Compare with the Index` (`EDIT-PLUG-58`).
* The index exists before the first commit: a staged new diagram is compared.

## Text tabs

The editor runs the plugins in its text tabs too (`EDIT-PLUG-56/57`): a text
is staged, unstaged and committed as a diagram is, and its diff is a line
diff.

```
 text tab (text, markdown, c, cpp, csharp, python)
   ${input} = input.<ext>, the text with its unsaved edits, UTF-8
      |
      v
 hsm-git diff DOC --current input.md --revision=REV     not .graphml: textdiff.run
   the base: the same revision file (or the index)
   difflib.unified_diff(base lines, current lines, 3 lines of context)
   ${diagnostics}: a finding per block, line = its first line in the text
```

* The lines are compared without their line ends; the base is read as UTF-8,
  an undecodable byte replaced.
* A text diff needs no `CyberiadaML`.
* The compares stay diagram-only: the editor accepts a `diff` result only in
  the diagram modes (`EDIT-PLUG-58`).
* The modes of the languages a plugin brings are not listed: `modes` has no
  wildcard, and their ids are not known in advance.

## The history

```
 git log --follow -n COUNT -z --date=short --format=%h%x1f%ad%x1f%an%x1f%s -- PATH
   PATH: the file in HEAD; a staged rename: its old path (as the diff)
   -> 3f2a9c1  2026-11-11  Alexey Fedoseev  blink at night
```

* `COUNT` is 30 unless `--count` says otherwise.
* No commit yet, or a file HEAD lacks: `PATH has no commits`.
* The hashes are those Compare with a Revision... and Changes Since a
  Revision... take as the revision.

## The textconv

git compares the texts its textconv driver prints for the two sides
(`gitattributes(5)`, Performing text diffs of binary files). `hsm-git textconv`
prints a diagram as its listing: the text of a diff against an empty document,
without the marks and the summary - every element, one line each, in the order
of the text of a diff.

```
 .gitattributes:  *.graphml diff=cyberiada
 git config diff.cyberiada.textconv "hsm-git textconv"
 git diff / git log -p  ->  hsm-git textconv <side>  ->  the listing of each side
                        ->  git's line diff of the two listings
```

* The listing leaves out the geometry, the ids and the view state, so a moved
  state is no change on the command line.
* An empty file is an empty listing. A file the library cannot read, or a
  Python without `CyberiadaML`, prints the file as it is with one warning line
  on stderr, so `git diff` still works.
* The driver is the user's git configuration: the plugin does not write it.

## The messages

The run writes its own messages in the language of the editor,
`CYBERIADA_PRO_LANGUAGE` (`PLUGIN-API.md`, The command line), English
without it.

* `i18n.tr(text)` looks the English text up in the catalog of the language;
  a text without a translation stays English.
* Translated: the failures, the status lines, the history, the questions, the
  logs and the states of the commit session.
* Not translated: the text of a diff and its findings (a format, as the
  output of `git diff`), git's own output (git translates it), the
  installation of the editor plugin (it runs outside the editor).

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
    hsm-git diff DOCUMENT [--current FILE] [--revision=REV | --index] [--geometry]
                 [--diagnostics FILE]
    hsm-git revision DOCUMENT [--revision=REV | --index] --output FILE
    hsm-git history DOCUMENT [--count N]
    hsm-git textconv FILE
    hsm-git --install-editor-plugin [DIR]

`python3 -m hsm_git` is `hsm-git`. The exit codes and the formats are in
`API.md`.

## The plugin

`editor-plugin/plugin.json` is the plugin `git` (Plugins > Git).

| Action | Kind | When | Modes | Runs |
|---|---|---|---|---|
| Stage | one-shot, log | `saved`, `git` | all | `stage ${document}` |
| Unstage | one-shot, log | `git` | all | `unstage ${document}` |
| Commit... | session, supervised | `git` | all | `commit ${document} --session --request ${request}` |
| Commit... | one-shot, log; replaced by the session | `git` | all | `commit ${document} --message-file ${param-file:message}` |
| Changes Since a Revision... | one-shot, log | `git` | all | `diff ${document} --current ${input} --revision=${param:revision} --diagnostics ${diagnostics}` |
| Compare with a Revision... | one-shot, diff | `git` | diagram | `revision ${document} --revision=${param:revision} --output ${output}` |
| Compare with the Index | one-shot, diff | `git` | diagram | `revision ${document} --index --output ${output}` |
| History | one-shot, log | `git` | all | `history ${document}` |

* The diagram modes are `hsm`, `fa` and `inspection`: an inspected diagram is
  staged and compared as an edited one. All the modes add the text modes
  `text`, `markdown`, `c`, `cpp`, `csharp` and `python`. The diff tabs get no
  git action.
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
| `hsm_git/repo.py` | the repository of a document: the work tree, the path, the branch, the staged files, the revision, the blob, the index, the log |
| `hsm_git/actions.py` | stage, unstage, the one-shot commit, the history |
| `hsm_git/session.py` | the commit session (JSON-RPC 2.0 over stdin and stdout) |
| `hsm_git/diff.py` | the base file, the documents of a diff, its text and findings, the listing |
| `hsm_git/textdiff.py` | the line diff of a text and its findings |
| `hsm_git/i18n.py` | the language of the run and the catalogs of the messages |
| `hsm_git/plugin.py` | the installation of the editor plugin |

## Testing

* `test/run.py` - the actions and the diffs on temporary repositories made by
  the test, with a git configuration of their own (no user or system
  configuration leaks in); the text of the diff of the example diagrams is
  compared with `test/good/`; `revision` writes the stored file, the old one
  of a staged rename, an empty one for a new file; the index as a base, an
  unmerged file refused; the findings of a diagram and of a text; the line
  diff of a text; the history after a rename; the listing, and `git diff`
  through the textconv driver configured in the test repository; the Russian
  messages, every translated text used and every used text translated.
* `test/session_test.py` - the commit session driven over its pipes: accept,
  decline, an empty answer, a stop during the question, nothing staged, a
  Russian question.
* `test/plugin_test.py` - the plugin in the batch mode of CyberiadaPro:
  the list of the plugins, Stage, the diff and its findings, the commit
  session from a session script, the history; a Markdown file in a text tab
  staged and compared; skipped without an editor that starts, or with one
  before the `git` token. The compares: the `== diff` section of
  `--run-plugin git:compare --dump` and `git:compare-index` against
  `test/good/`, their pairs those of the text diff; skipped with an editor
  before the diff tabs.
* A test without git, or a diff test without `Document.diff`, is skipped
  (exit 77).

## Stages

1. 0.1: Stage, Unstage, the commit with its question, the diff against a
   revision as text, Compare with a Revision... in a diff tab of the editor
   (an editor with the diff tabs, `EDIT-PLUG-58`); the findings of the diff,
   Compare with the Index, the text tabs, the history, the textconv driver,
   the Russian messages (an editor with the plugin modes, `EDIT-PLUG-56/57`).

## Open questions

* A message of several lines needs an answer box of several lines in the
  editor.
* The text modes of the plugin languages need a mode group in `modes` to get
  the git actions.
