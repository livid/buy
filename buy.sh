source .venv/bin/activate
ITERATIONS=30
SIZE=0.01
SLIPPAGE=25
SLEEP=300   # seconds
for i in $(seq 1 $ITERATIONS); do
  echo "[$i] buy $SIZE"
  python buy.py $SIZE --slippage-bps $SLIPPAGE --yes
  if [ $i -lt $ITERATIONS ]; then
    sleep $SLEEP
  fi
done