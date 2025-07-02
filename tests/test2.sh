#!/bin/bash

tests/clean_files.sh

echo "Running test 2..."

source venv/bin/activate

python src/worker.py -v &
python src/worker.py -v &
sleep 10
python src/driver.py 4 2 -v &
wait

deactivate

echo "Test 2 completed"
echo ""