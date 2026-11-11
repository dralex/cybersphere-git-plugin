# cybersphere-git-plugin project changelog

## Version 0.1.0 (unreleased)

Added:
- the specification: the architecture (`docs/ARCHITECTURE.md`) and the
  interface (`docs/API.md`) of the plugin - stage, unstage, the commit of the
  index after a question, the diff of a diagram against a revision as text;
- the package `hsm_git` and the command `hsm-git` (`python3 -m hsm_git`):
  stage, unstage, the one-shot commit of the index, the diff of a diagram
  against a revision as text over `Document.diff` of libcyberiadamlpp-py 1.2;
- `hsm-git revision`: the diagram of a revision written into a file, the base
  of a diff tab of the editor - the old path of a staged rename, an empty file
  for a diagram the revision lacks; the base of the text diff too;
- the commit session of the editor: the branch and the staged files asked
  about, the answer the message, a changed index asked again;
- the editor plugin `git`: Stage, Unstage, Commit... and Changes Since a
  Revision..., greyed out without git or outside a git work tree (the editor
  conditions `requires` and `git`), the Russian texts;
- `hsm-git --install-editor-plugin [DIR]` and the Debian package
  `python3-cybersphere-git`.
