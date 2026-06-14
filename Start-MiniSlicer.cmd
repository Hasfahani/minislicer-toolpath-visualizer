REM Purpose: Root-level Windows shortcut for launching MiniSlicer.
REM Reason: Provides an easy entry point while delegating the real app launch to scripts/run.cmd.
@echo off
setlocal
call scripts\run.cmd
