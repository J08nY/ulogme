#!/bin/bash

if [ "$(uname)" == "Darwin" ]; then
  # This is a Mac
  ./osx/run_ulogme_osx.sh
else
  # Assume Linux
  sudo ./keyfreq.sh &
  kf=$!
  echo $kf
  trap "sudo kill -9 $kf" INT
  ./logactivewin.sh
fi
