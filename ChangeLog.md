# cybersphere-git-plugin project changelog

## Version 0.1.0 (unreleased)

Added:
- the specification: the architecture (`docs/ARCHITECTURE.md`) and the
  interface (`docs/API.md`) of the plugin - stage, unstage, the commit of the
  index after a question, the diff of a diagram against a revision as text;
- the package `hsm_git` and the command `hsm-git` (`python3 -m hsm_git`):
  stage, unstage, the one-shot commit of the index, the diff of a diagram
  against a revision as text over `Document.diff` of libcyberiadamlpp-py 1.2;
- the commit session of the editor: the branch and the staged files asked
  about, the answer the message, a changed index asked again;
- the editor plugin `git`: Stage, Unstage, Commit... and Changes Since a
  Revision..., greyed out without git or outside a git work tree (the editor
  conditions `requires` and `git`), the Russian texts;
- `hsm-git --install-editor-plugin [DIR]` and the Debian package
  `python3-cybersphere-git`;
- Compare with a Revision...: `hsm-git revision` writes the diagram as a
  revision stores it (the old path of a staged rename, an empty file for a
  new one) for a diff tab of the editor (`result: diff`), the text diff and
  the tab sharing the revision file and the pairs;
- the actions work in the HSM, FA and inspection tabs of the editor
  (`modes`); the editor's `regionGeometry` marker is shown with the Geometry
  option only, as the view state;
- the findings of Changes Since a Revision...: the changed elements in the
  Diagnostics of the editor, a click selects one (`hsm-git diff
  --diagnostics`);
- Compare with the Index: the staged diagram as the base of a diff tab
  (`hsm-git revision --index`), the text diff against the index (`hsm-git
  diff --index`), an unmerged file refused;
- the text tabs of the editor: Stage, Unstage, Commit... and Changes Since a
  Revision... for a plain text, Markdown, C, C++, C# or Python file, the
  changes line by line with their lines in Diagnostics;
- History: the last commits of the file, a rename followed (`hsm-git
  history`);
- `hsm-git textconv`: the textconv driver of git, `git diff` and `git log -p`
  show a diagram by its elements;
- a diagram the library cannot read fails the diff with one line, with any
  binding: before 1.2.0 its exceptions do not derive from
  `CyberiadaML.Exception`;
- the messages of the run in Russian when the editor speaks Russian
  (`CYBERIADA_PRO_LANGUAGE`); the text of a diff stays English.

Open for the release:
- the Debian package `Breaks: cyberiada-pro (<< X)`, X the first editor
  version with the diff tabs: the editors v1.0-pre3 and v1.0-pre4 reject the
  plugin for its `diff` result, and they share the package version 1.0.0
  with the current editor.
