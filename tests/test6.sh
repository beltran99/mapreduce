#!/bin/bash

tests/clean_files.sh

echo "Running test 6..."

source venv/bin/activate

python src/driver.py 10 1 -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
wait

deactivate

echo "Test 6 completed"
echo ""