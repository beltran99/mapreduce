#!/bin/bash

tests/clean_files.sh

echo "Running test 5..."

source venv/bin/activate

python src/driver.py 1 10 -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
wait

deactivate

echo "Test 5 completed"
echo ""