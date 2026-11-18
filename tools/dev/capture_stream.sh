#!/bin/sh
# One capture stream: keeps taking device screenshots until /data/local/tmp/stop appears.
# The frame name carries the millisecond it was requested plus a per-stream sequence number,
# so several streams can be merged back into one timeline by sorting on the timestamp.
S=$1
OUT=/data/local/tmp/frames
i=0
while [ ! -f /data/local/tmp/stop ]; do
  i=$((i+1))
  snapshot_display -f $OUT/s${S}_$(date +%s%3N)_${i}.jpeg >/dev/null 2>&1
done
