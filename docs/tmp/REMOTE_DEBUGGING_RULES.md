# Remote Debugging Rules

## WSL-first remote operations

All remote debugging must use WSL first.

Use `wsl bash ...` or repository `.sh` scripts for:

- SSH commands
- SCP/rsync transfers
- remote script execution
- screen/tmux inspection
- GPU and training-process checks
- log polling and result pullback

Do not compose complex remote commands directly in PowerShell. PowerShell is allowed only when the user explicitly requests a PowerShell/`.ps1` workflow or when the task is specifically to test a Windows wrapper.

Any remote command that contains pipes, redirection, here-docs, `$()` command substitution, regular expressions, nested quotes, or multiline logic must be written as a bash script and invoked through WSL.

Reason: PowerShell can pre-parse remote shell syntax before SSH receives it, which has already caused quoting, pipe, and command-substitution failures during H800/3090 debugging.
