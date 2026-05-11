# H800 Manual Stop Summary

Timestamp: 2026-05-11T07:25:52Z archive / 2026-05-11 15:26 +08 remote stop.

Action taken:
- Stopped the local path-C monitor to avoid remote task restarts.
- Stopped H800 Path C training scheduler and auto-shutdown watchdog.
- Stopped the active supervised_s44 training process before completion because the H800 run had low paper value and high cost sensitivity.
- Archived partial H800 results and logs.

Pulled local files:
- docs/tmp/h800_pathc/h800_partial_before_shutdown_20260511T072552Z.tgz
- docs/tmp/h800_pathc/h800_partial_before_shutdown_20260511T072552Z.txt

Partial completion:
- 6 best_metrics.json files were present at stop time:
  - teacher_ct_s42/s43/s44
  - xray_supervised_s42/s43/s44
- KD runs had not started, so there is no H800 KD-vs-supervised conclusion.

Poweroff status:
- OS-level poweroff/shutdown failed because this AutoDL/SeetaCloud runtime is a container with PID 1 = bash, not systemd, and forced reboot/poweroff is not permitted from inside the container.
- The training workload is stopped, but the machine may remain billable until stopped from the provider web UI or via the provider API with a valid developer token.
