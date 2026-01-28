---
id: task-3.2
title: Implement GrpcClient transport
status: To Do
assignee: []
created_date: '2026-01-28 09:09'
labels:
  - phase-3
  - transport
  - grpc
dependencies:
  - task-3.1
  - task-1.5
parent_task_id: task-3
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the gRPC transport client using the generated proto stubs.

**Reference**: PRD Section 5.3.2 (gRPC Client Implementation)

**Location**: `tck/transport/grpc_client.py`

**Implementation details**:
- Use grpc.insecure_channel() for connection
- Use generated a2a_pb2_grpc.A2AServiceStub for RPC calls
- Convert dict to proto using google.protobuf.json_format.ParseDict
- Handle grpc.RpcError for error responses
- Support streaming responses (SendStreamingMessage, SubscribeToTask)

**Methods to implement**:
- All abstract methods from BaseTransportClient
- `_dict_to_proto(data: dict, proto_class: type)` helper

**Error handling**:
- Catch grpc.RpcError and convert to TransportResponse with error
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tck/transport/grpc_client.py exists
- [ ] #2 GrpcClient extends BaseTransportClient
- [ ] #3 Client uses generated a2a_pb2_grpc stubs
- [ ] #4 All A2A operations are implemented
- [ ] #5 Dict-to-proto conversion works correctly
- [ ] #6 gRPC errors are caught and returned in TransportResponse
- [ ] #7 Streaming operations return StreamingResponse with iterator
<!-- AC:END -->
