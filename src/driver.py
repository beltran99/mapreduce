"""The Python implementation of the GRPC mapreduce.Driver server."""

from concurrent import futures
import logging
import threading
import time

import grpc
import mapreduce_pb2
import mapreduce_pb2_grpc

import argparse
import os
import sys
import queue
from typing import Literal, List

from pathlib import Path
abs_path = Path(__file__).resolve().parent

node_name = 'Driver ' + str(os.getpid())

TASK_TYPES = {0: 'map', 1: 'reduce'}

class Task:
    """ Task class for the Driver to organize them into queues """
    
    def __init__(self, task_type: Literal['m', 'r'], task_id: int) -> None:
        """ Create a new task

        Args:
            task_type (Literal['m', 'r']): Task type: It can be either 'm' (map) or 'r' (reduce).
            task_id (int): Task ID. 
        """
        
        self.task_type = task_type
        self.task_type_int = 0 if task_type == 'm' else 1
        self.task_id = task_id
        self.files = []
    
    def add_file(self, f: str) -> None:
        """ Adds a new file to the list of files targeted by the task.

        Args:
            f (str): Target file.
        """
        
        self.files.append(f)
        
    def __str__(self) -> None:
        task_type = "Map" if self.task_type == 'm' else "Reduce"
        return f"{task_type} task with id {self.task_id} that will have {[os.path.basename(path) for path in self.files]} as input" 


class Driver(mapreduce_pb2_grpc.DriverServicer):
    def __init__(self, N: int, M: int, input_dir: str) -> None:
        """ Creates a Driver object that will assign N map tasks and M reduce tasks.

        Args:
            N (int): number of map tasks
            M (int): number of reduce tasks
            input_dir (str): path where the input files for the word count are located
        """
        
        self.N = N
        self.M = M
        self.input_dir = input_dir
        
        # we create separate queues for map and reduce tasks because these
        # operations are performed sequentially in the map-reduce framework.
        # first, the map operations are executed and
        # when all of them have finished, the reduce ones are executed
        self.map_q = self.fill_map_queue()
        self.reduce_q = self.fill_reduce_queue()
        
        self.map_acks = 0
        self.reduce_acks = 0
        
    def fill_map_queue(self) -> None:
        """ Divides the input files into N map tasks and puts them into a task queue.

        Returns:
            q: queue filled with map tasks
        """
        
        q = queue.Queue()
        
        input_files = [x for x in os.listdir(abs_path / self.input_dir) if '.txt' in x]
        n_files = len(input_files)
        
        if self.N > n_files:
            logging.warning(f"You specified {self.N - n_files} more map tasks than input files there are to map, so those extra tasks will not be needed", extra={'node': node_name})
            self.N = n_files
        
        # create N tasks
        tasks = []
        for i in range(self.N):
            t = Task('m', i)
            tasks.append(t)            
            
        # round-robin distribution of files
        # assigns one file to a task at a time
        task_idx = 0
        for _file in input_files:
            tasks[task_idx].add_file(str(Path(self.input_dir) / _file))
            task_idx += 1
            if task_idx == self.N:
                task_idx = 0
        
        # queue created tasks     
        for task in tasks:
            logging.info(f"Created {task}", extra={'node': node_name})
            q.put(task)
            
        return q
            
    def fill_reduce_queue(self) -> None:
        """ Creates M reduce tasks and puts them into a task queue.

        Returns:
            q: queue filled with reduce tasks
        """
        
        q = queue.Queue()
        
        # fill task queue with M reduce tasks
        for j in range(self.M):
            t = Task('r', j)
            for i in range(self.N):
                _f = '../data/map/' + 'mr-' + str(i) + '-' + str(j)
                t.add_file(_f)
            logging.info(f"Created {t}", extra={'node': node_name})
            q.put(t)
            
        return q
    
    def check_available_tasks(self) -> None:
        """ Checks if there are still tasks to be completed. """
        
        while self.map_acks < self.N and self.reduce_acks < self.M:
            time.sleep(5)
        logging.info(f"Received all task completion notifications. Shutting down...", extra={'node': node_name})
    
    def AssignTask(self, request, context) -> mapreduce_pb2.TaskAssignment:
        """ Handles a task assignment request by either sending a map/reduce task assignment
            or telling the worker to wait.

        Returns:
            mapreduce_pb2.TaskAssignment: response to task assignment request
        """
        
        metadata = dict(context.invocation_metadata())
        sender_name = metadata.get('sender_name', 'Unknown')
        logging.info(f"Received task request from {sender_name}", extra={'node': node_name})
        
        if not self.map_q.empty():
            # send map task assignment
            task = self.map_q.get(block=False)
            logging.info(f"Assigned map task with id {task.task_id} to {sender_name}", extra={'node': node_name})
            return mapreduce_pb2.TaskAssignment(assignmentStatus=0, taskId=task.task_id, taskType=task.task_type_int, input_files=task.files, M=self.M)
        
        elif not self.reduce_q.empty():
            if self.map_acks == self.N:
                # send reduce task assignment
                task = self.reduce_q.get(block=False)
                logging.info(f"Assigned reduce task with id {task.task_id} to {sender_name}", extra={'node': node_name})
                return mapreduce_pb2.TaskAssignment(assignmentStatus=0, taskId=task.task_id, taskType=task.task_type_int, input_files=task.files)
            else:
                # cannot execute reduce operations yet, need to wait
                logging.info(f"Can't assign any task at the moment to {sender_name}", extra={'node': node_name})
                return mapreduce_pb2.TaskAssignment(assignmentStatus=1)
        else:
            # no more operations to execute
            logging.info("All tasks completed", extra={'node': node_name})
            return mapreduce_pb2.TaskAssignment(assignmentStatus=1)

    def PingPong(self, request, context) -> mapreduce_pb2.Pong:
        """ Handles a ping message by sending a pong back.

        Returns:
            mapreduce_pb2.Pong: pong
        """
        metadata = dict(context.invocation_metadata())
        sender_name = metadata.get('sender_name', 'Unknown')
        logging.info(f"Received PING from {sender_name}", extra={'node': node_name})

        return mapreduce_pb2.Pong(pong = request.ping + 1)
    
    def AcknowledgeTaskCompletion(self, request, context) -> mapreduce_pb2.TaskCompletionACK:
        """ Handles a task completion notification by updating the status of completed tasks
            and acknowledges the receipt of the message.

        Returns:
            mapreduce_pb2.TaskCompletionACK: notification ACK
        """
        
        metadata = dict(context.invocation_metadata())
        sender_name = metadata.get('sender_name', 'Unknown')
        logging.info(f"Received task completion notification: {TASK_TYPES[request.taskType]} task with id {request.taskId} from {sender_name}", extra={'node': node_name})
        
        if request.taskType == 0:
            self.map_acks += 1
        elif request.taskType == 1:
            self.reduce_acks += 1
            
        return mapreduce_pb2.TaskCompletionACK(taskId=request.taskId, taskType=request.taskType)

def serve(N: int, M: int, input_dir: str) -> None:
    """ Driver's loop. Handles workers' messages until all tasks are done.

    Args:
        N (int): number of map tasks
        M (int): number of reduce tasks
        input_dir (str): path where the input files for the word count are located
    """
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    driver = Driver(N, M, input_dir)
    mapreduce_pb2_grpc.add_DriverServicer_to_server(driver, server)
    
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    
    # loop that will go on until there are no tasks left
    server_loop = threading.Thread(target=driver.check_available_tasks)
    server_loop.start()
    
    server.start()
    logging.info("Server started, listening on " + port, extra={'node': node_name})

    server_loop.join()
    server.stop(grace=None)


if __name__ == "__main__":
    
    path = str(Path(abs_path / '../data/').resolve())
    if not os.path.exists(path):
        os.mkdir(path)
    path = str(Path(abs_path / '../data/input/').resolve())
    if not os.path.exists(path):
        os.mkdir(path)
    path = str(Path(abs_path / '../data/map/').resolve())
    if not os.path.exists(path):
        os.mkdir(path)
    path = str(Path(abs_path / '../data/reduce/').resolve())
    if not os.path.exists(path):
        os.mkdir(path)
    
    parser = argparse.ArgumentParser(description='Setup driver and configure number of N map tasks and M of reduce tasks to perform.')
    parser.add_argument('N', metavar='N', type=int, help='number of map tasks')
    parser.add_argument('M', metavar='M', type=int, help='number of reduce tasks')
    parser.add_argument('--input_dir', type=str, default=str(Path(abs_path / '../data/input/').resolve()), help='input files directory')
    parser.add_argument('--verbose', '-v', action="store_true", help='log system messages')
    args = parser.parse_args()
    
    if args.N < 1 or args.M < 1:
        print("You must specify at least 1 task of each type!")
        sys.exit()
    
    logging_level = logging.DEBUG
    if not args.verbose:
        logging_level = logging.CRITICAL
        
    logging.basicConfig(
        format='%(asctime)s - %(node)s - %(levelname)s - %(message)s',
        datefmt='%d/%m/%Y %I:%M:%S %p',
        level=logging_level,
    )
    
    serve(args.N, args.M, str(Path(args.input_dir).resolve()))
