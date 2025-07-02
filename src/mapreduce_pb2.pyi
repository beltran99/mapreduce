from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class Ping(_message.Message):
    __slots__ = ["ping"]
    PING_FIELD_NUMBER: _ClassVar[int]
    ping: int
    def __init__(self, ping: _Optional[int] = ...) -> None: ...

class Pong(_message.Message):
    __slots__ = ["pong"]
    PONG_FIELD_NUMBER: _ClassVar[int]
    pong: int
    def __init__(self, pong: _Optional[int] = ...) -> None: ...

class TaskRequest(_message.Message):
    __slots__ = ["request"]
    REQUEST_FIELD_NUMBER: _ClassVar[int]
    request: int
    def __init__(self, request: _Optional[int] = ...) -> None: ...

class TaskAssignment(_message.Message):
    __slots__ = ["assignmentStatus", "taskId", "taskType", "input_files", "M"]
    ASSIGNMENTSTATUS_FIELD_NUMBER: _ClassVar[int]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TASKTYPE_FIELD_NUMBER: _ClassVar[int]
    INPUT_FILES_FIELD_NUMBER: _ClassVar[int]
    M_FIELD_NUMBER: _ClassVar[int]
    assignmentStatus: int
    taskId: int
    taskType: int
    input_files: _containers.RepeatedScalarFieldContainer[str]
    M: int
    def __init__(self, assignmentStatus: _Optional[int] = ..., taskId: _Optional[int] = ..., taskType: _Optional[int] = ..., input_files: _Optional[_Iterable[str]] = ..., M: _Optional[int] = ...) -> None: ...

class TaskCompletion(_message.Message):
    __slots__ = ["taskId", "taskType"]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TASKTYPE_FIELD_NUMBER: _ClassVar[int]
    taskId: int
    taskType: int
    def __init__(self, taskId: _Optional[int] = ..., taskType: _Optional[int] = ...) -> None: ...

class TaskCompletionACK(_message.Message):
    __slots__ = ["taskId", "taskType"]
    TASKID_FIELD_NUMBER: _ClassVar[int]
    TASKTYPE_FIELD_NUMBER: _ClassVar[int]
    taskId: int
    taskType: int
    def __init__(self, taskId: _Optional[int] = ..., taskType: _Optional[int] = ...) -> None: ...
