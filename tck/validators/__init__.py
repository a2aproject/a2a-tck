"""Validators for A2A protocol responses.

Schema ref constants define the vocabulary shared by all validators
(JSONSchemaValidator, ProtoSchemaValidator, JsonRpcResponseValidator).
Tests pass these constants to ``validator.validate(data, SCHEMA_REF)``
and each validator resolves them to its transport-specific representation.
"""

AGENT_CARD = "Agent Card"
AGENT_INTERFACE = "Agent Interface"
MESSAGE = "Message"
SEND_MESSAGE_RESPONSE = "Send Message Response"
STREAM_RESPONSE = "Stream Response"
TASK = "Task"
