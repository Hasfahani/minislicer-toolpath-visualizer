REM Purpose: Root-level Windows shortcut for setting up MiniSlicer.
REM Reason: Provides an easy entry point while delegating the real setup work to scripts/setup.cmd.
@echo off
setlocal
call scripts\setup.cmd
