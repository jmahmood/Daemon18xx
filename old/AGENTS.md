# Preserved original implementation

The owner explicitly requested that the original implementation be moved here
and retained, rather than deleted. These files are historical reference material,
including the mutable game model, configuration, minigames, tests, original
multiplayer server and frontend. README.md is preserved verbatim from master.

- Preserve the archived code, data, tests and required notices. Do not delete,
  reformat, modernize or replace them without an explicit request.
- Keep the active server and engines outside this directory. Do not add archive
  directories to the active application's import path.
- Original unit/scenario tests and multiplayer test scripts are preserved in
  old/tests/. The owner explicitly deprecated them: retain them as historical
  records, without running, maintaining or including them in current validation.
  Their original imports and assumptions are preserved, rather than adapted to
  the archive layout. Do not add old/__init__.py or otherwise make the archive
  part of the current application's imports or test discovery.
- Original deployment files are retained for reference, without updating their
  architecture or promising they work independently of the current project.
  Use the repository root's documented backend for current games.
- Local databases and other runtime files remain private, ignored data. Do not
  commit them when adding the archive to Git.
