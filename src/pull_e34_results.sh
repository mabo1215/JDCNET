#!/usr/bin/env bash
# Pull best_metrics.json for all e34 multi-seed experiments
REMOTE="root@connect.westb.seetacloud.com"
RBASE="/root/autodl-tmp/JDCNET/src/runs/covid_matrix_e34"
LBASE="/mnt/c/source/JDCNET/src/runs/covid_matrix_e34"

for r in \
  student_xray_supervised_resnet18_paired_s43 \
  student_xray_supervised_resnet18_paired_s44 \
  student_xray_supervised_resnet18_paired_s45 \
  student_xray_supervised_biomedclip_paired_s43 \
  student_xray_supervised_biomedclip_paired_s44 \
  student_xray_supervised_biomedclip_paired_s45; do
  mkdir -p "${LBASE}/${r}"
  sshpass -p 'k5qShTLQWF5a' scp -o StrictHostKeyChecking=no -P 39830 \
    "${REMOTE}:${RBASE}/${r}/best_metrics.json" \
    "${LBASE}/${r}/best_metrics.json" && echo "OK $r" || echo "FAIL $r"
done
