#!/bin/bash

tests/clean_files.sh

echo "Running test 3..."

source venv/bin/activate

python src/driver.py 8 6 -v &
python src/worker.py -v &
sleep 2
python src/worker.py -v &
wait

deactivate

echo "Test 3 completed"
echo ""