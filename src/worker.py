"""The Python implementation of the GRPC mapreduce worker."""

from __future__ import print_function

import random
import argparse
import logging
import time
import re
import os
import sys
from collections import Counter
from typing import List

import grpc
import mapreduce_pb2
import mapreduce_pb2_grpc

from pathlib import Path
abs_path = Path(__file__).resolve().parent

node_name = 'Worker ' + str(os.getpid())

TASK_TYPES = {0: 'map', 1: 'reduce'}

class Worker:
    def __init__(self):
        self.channel = grpc.insecure_channel("localhost:50051")
        self.stub = mapreduce_pb2_grpc.DriverStub(self.channel)
        
        logging.info("Worker up", extra={'node': node_name})
        
        # Wait for the server to be ready (adjust the timeout as needed)
        grpc.channel_ready_future(self.channel).result(timeout=None)
        
    def notify_task_completion(self, taskId: int, taskType: int) -> None:
        """Sends a message to the Driver to notify the completion of a task
        so that the Driver can keep track of completed tasks.

        Args:
            taskId (int): completed task ID
            taskType (int): completed task type
        """
        
        try:
            logging.info("Notifying task completion...", extra={'node': node_name})
            ack = self.stub.AcknowledgeTaskCompletion(mapreduce_pb2.TaskCompletion(taskId=taskId, taskType=taskType), metadata = [('sender_name', node_name)])
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                # Handle timeout exception here
                logging.error("RPC Timeout: Deadline exceeded", extra={'node': node_name})
            else:
                # Handle other gRPC errors
                logging.error(f" gRPC Error: {e}", extra={'node': node_name})

        except Exception as ex:
            # Handle other non-gRPC exceptions
            logging.error(f"Unexpected error: {ex}", extra={'node': node_name})
        
    def map(self, taskId: int, input_files: List[str], M: int) -> None:
        """Executes map task with the given taskId on the given target files.

        Args:
            taskId (int): task ID
            input_files (List[str]): target files of the map operation
            M (int): number of reduce tasks specified by the user
        """
        
        logging.info(f"Executing map operation with id {taskId} on files {[os.path.basename(path) for path in input_files]}", extra={'node': node_name})
        
        for input_file in input_files:
            f = open(Path(abs_path / input_file).resolve(), 'r')
            text = f.read()
            # words = text.split()
            words = re.findall(r'\b[a-zA-Z0-9]+\b', text)
            
            for word in words:
                bucket_id = ord(word[0]) % M
                bucket_name = "mr-" + str(taskId) + "-" + str(bucket_id)
                bucket_path = (abs_path / ("../data/map/" + bucket_name)).resolve()
                mode = 'w' if not os.path.exists(bucket_path) else 'a'
                with open(bucket_path, mode) as bucket_file:
                    bucket_file.write(word + '\n')
                    
        self.notify_task_completion(taskId=taskId, taskType=0)
        
    def reduce(self, taskId: int, input_files: List[str]) -> None:
        """Executes reduce task with the given taskId on the given target files.
        The target files could be inferred by looking for those with bucketId == taskId but
        they can be inferred beforehand by the driver aswell since they are predefined by the taskId.

        Args:
            taskId (int): task ID
            input_files (List[str]): target files of the reduce operation
        """
        
        logging.info(f"Executing reduce operation with id {taskId} on files {[os.path.basename(path) for path in input_files]}", extra={'node': node_name})
        
        words = []
        for input_file in input_files:
            f = open(Path(abs_path / input_file).resolve(), 'r')
            words_partial = f.read().splitlines()
            words.extend(words_partial)
            
        c = Counter(words)
        
        out_path = (abs_path / ("../data/reduce/mr-" + str(taskId))).resolve()
        mode = 'w' if not os.path.exists(out_path) else 'a'
        with open(out_path, mode) as out_file:
            for word, count in c.most_common():
                out_file.write('{} {}\n'.format(word, count))
                    
        self.notify_task_completion(taskId=taskId, taskType=1)
        
    def run(self) -> None:
        """
            Worker's loop.
            Basic workflow:
                1. Ping the server to check that it is up
                2. Request a new task assignment
                3. Complete task assignment
                4. Notify about task completion
        """
        while True:
            try:
                # first ping the server to see if it is up
                pong = self.stub.PingPong(mapreduce_pb2.Ping(ping=random.randint(0, 10000)), wait_for_ready=True, timeout=10, metadata = [('sender_name', node_name)])
            
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                    # Handle timeout exception here
                    logging.info("PING Timeout: Driver is not up anymore. Shutting down...", extra={'node': node_name})
                    break
                elif e.code() == grpc.StatusCode.CANCELLED or e.code() == grpc.StatusCode.UNAVAILABLE:
                    # Handle cancelled connection
                    logging.info("Cannot reach Driver. Checking if it is still up...", extra={'node': node_name})
                    continue
                else:
                    logging.error(f"gRPC Error: {e}", extra={'node': node_name})
                    break
            
            except Exception as ex:
                # Handle other non-gRPC exceptions
                logging.error(f"Unexpected error: {ex}", extra={'node': node_name})
                break
            
            try:
                # server is up so we request a new task
                logging.info("Server is up. Requesting new task...", extra={'node': node_name})
                taskAssignment = self.stub.AssignTask(mapreduce_pb2.TaskRequest(request=0), metadata = [('sender_name', node_name)])
                
                # handle driver assignment
                if taskAssignment.assignmentStatus == 0: # new task
                    logging.info(f"Received {TASK_TYPES[taskAssignment.taskType]} task assignment", extra={'node': node_name})
                    
                    if taskAssignment.taskType == 0: # map task
                        self.map(taskAssignment.taskId, taskAssignment.input_files, taskAssignment.M)
                    elif taskAssignment.taskType == 1: # reduce task
                        self.reduce(taskAssignment.taskId, taskAssignment.input_files)
                    else:
                        logging.warning(f"Received task assignment of unknown type", extra={'node': node_name})
                    
                elif taskAssignment.assignmentStatus == 1: # no tasks available at the moment
                    logging.info(f"No tasks to complete right now...", extra={'node': node_name})
                    time.sleep(5)
                
                else:
                    logging.warning(f"Received task assignment with unknown status", extra={'node': node_name})
                
            except grpc.RpcError as e:
                logging.error(f"gRPC Error: {e}", extra={'node': node_name})
                break

            except Exception as ex:
                # Handle other non-gRPC exceptions
                logging.error(f"Unexpected error: {ex}", extra={'node': node_name})
                break
            
            
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Invoke worker')
    parser.add_argument('--verbose', '-v', action="store_true", help='log system messages')
    args = parser.parse_args()
    
    logging_level = logging.DEBUG
    if not args.verbose:
        logging_level = logging.CRITICAL
    
    logging.basicConfig(
        format='%(asctime)s - %(node)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%Y %I:%M:%S %p',
        level=logging_level
    )
    
    worker = Worker()
    worker.run()