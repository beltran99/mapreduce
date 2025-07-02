#!/bin/bash

tests/clean_files.sh

echo "Running test 1..."

source venv/bin/activate

python src/driver.py 6 4 -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
python src/worker.py -v &
wait

deactivate

echo "Test 1 completed"
echo ""