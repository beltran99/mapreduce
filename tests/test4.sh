#!/bin/bash

tests/clean_files.sh

echo "Running test 4..."

source venv/bin/activate

python src/driver.py 0 0 -v

deactivate

echo "Test 4 completed"
echo ""