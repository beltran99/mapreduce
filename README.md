# mapreduce
Word Count implementation using MapReduce framework, gRPC and Python 3.8.10.

## Problem Statement
This repository contains a distributed map-reduce solution for the word count problem on a local machine. The server-client communication uses [gRPC](https://grpc.io/). The problem input is a set of text files, and the output consists on the count of how many times each word appears in the whole dataset.

## Implementation
### Worker
- [worker.py](src/worker.py) implements the worker functionality.
- The workers will wait for the Driver to start.
- A worker will firstly send a ping message to check if the Driver is up.
  - If the Driver does not answer after a timeout is consumed, the workers will assume all tasks are completed and shut down themselves.
- If the Driver is still up, then the workers will make task assignment requests.
- If there are still tasks to complete but cannot be assigned in that moment (i.e. other workers are still finishing map tasks so reduce tasks cannot start yet), the unoccupied workers will wait a bit and subsequently make a new request.
- When the workers receive a task assignment, they will complete it and finally notify the Driver about its completion.

### Driver

- [driver.py](src/driver.py) implements the driver functionality.
- The Driver will initially split the total work among the map and reduce tasks in a [round-robin](https://en.wikipedia.org/wiki/Round-robin_scheduling) fashion and queue them.
- Then it will start listening to workers' requests.
- Firstly, it will start assigning map tasks.
- As soon as the Driver has acknowledged the completion of all map tasks, it will start assigning the reduce ones.
- Finally, when all reduce tasks have been completed too, the server will shut down itself.

### Protocol
- [mapreduce.proto](protos/mapreduce.proto) defines the protocol used between workers and drivers.

| Message | Field | Type | Description |
| ------------- | ------------- | ------------- | ------------- |
| Ping | ping | int | Random number |
| Pong | pong | int | Received number incremented by 1 |
| TaskRequest | request | int | Irrelevant field |
| TaskAssignment | assignmentStatus | int | Status of the task assignment |
| TaskAssignment | taskId | int | Task ID |
| TaskAssignment | taskType | int | Task type |
| TaskAssignment | input_files | List[str] | Target files for the task |
| TaskAssignment | M | int | Number of reduce tasks configured by the user |
| TaskCompletion | taskId | int | Task ID |
| TaskCompletion | taskType | int | Task type |
| TaskCompletionACK | taskId | int | Task ID |
| TaskCompletionACK | taskType | int | Task type |

## Tutorial
### Installation
Clone the repository into your working directory
```bash
git clone https://github.com/beltran99/mapreduce.git
```

Navigate to the repository folder
```bash
cd mapreduce
```

Install virtualenv if you don't have it installed already
```bash
pip install virtualenv
```

Create a new virtual environment called venv
```bash
virtualenv venv
```

Activate the venv environment
```bash
source venv/bin/activate
```

Installed the required packages in the virtual environment
```bash
pip install -r requirements.txt
```

### Example usage
A Driver can be invoked with the following parameters:
  - N, the number of map tasks to execute. It has to be larger than 1 and, if its value is larger than the actual number of input files, those extra tasks will be rejected since each task needs to target at least 1 file.
  - M, the number of reduce tasks to execute. It has to be larger than 1.
  - -v or --verbosity (optional), verbosity option.
  - --input_dir (optional), an option to specify a different set of input files.
```bash
python src/driver.py 6 4 -v
```

A worker has the option to be invoked with a -v verbosity option.
```bash
python src/worker.py -v
```

## Testing
There are 6 different test included in this repository.
| Test | Description | Objective |
| ------------- | ------------- | ------------- |
| test1.sh | Invocation of a Driver configured with 6 map tasks and 4 reduce tasks and 4 workers. | Evaluate the implementation in general. | 
| test2.sh | Invocation of two workers first, a 10 second sleep and then the invocation of the Driver. | Check that the workers and drivers can be invoked in any order. |
| test3.sh | Invocation of a Driver, a worker, a 2 second sleep and then the invocation of another worker. | Check how the Driver handles the situation since it cannot assume how many workers will show up. |
| test4.sh | Invocation of a Driver configured with 0 map tasks and 0 reduce tasks. | Check the correct parsing of N and M parameters via command-line. |
| test5.sh | Invocation of a Driver configured with 1 map task and 10 reduce tasks and 4 workers. | Check the implementation performance with a small M value and a large N value. |
| test6.sh | Invocation of a Driver configured with 10 map task and 1 reduce tasks and 4 workers. | Check the implementation performance with a large M value and a small N value. Also check what happens when the user specifies more map tasks than actual number of input files. |

You can perform an individual test by running the following command on your terminal:
```bash
./tests/test3.sh
```
Or run them all by running this command:
```bash
./tests/run_tests.sh
```
If you have any trouble running the test scripts, you may have to give execution permissions to the bash scripts like this:
```bash
chmod +x tests/*
```