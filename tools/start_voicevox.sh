#!/usr/bin/env bash
# VOICEVOX エンジンを起動する（Docker版）。すでに起動していれば何もしない。
set -e
if curl -s -m 2 localhost:50021/version >/dev/null; then echo "VOICEVOX は起動済み"; exit 0; fi
docker ps >/dev/null 2>&1 || (dockerd >/tmp/dockerd.log 2>&1 &) ; sleep 3
docker start voicevox 2>/dev/null || docker run -d --name voicevox -p 50021:50021 voicevox/voicevox_engine:cpu-latest
for i in $(seq 1 60); do curl -s -m 2 localhost:50021/version >/dev/null && { echo "VOICEVOX 起動OK"; exit 0; }; sleep 2; done
echo "VOICEVOX の起動に失敗しました"; exit 1
