# JSON Schema Quick Reference

## Quick Investigation Commands

```bash
# 1. List all defined types in the schema
jq '.definitions | keys' a2a_schema.json

# 2. Check if a specific type exists
jq '.definitions | has("TaskNotFoundError")' a2a_schema.json

# 3. Get complete definition of a type
jq '.definitions.Message' a2a_schema.json

# 4. Find all properties of a type
jq '.definitions.Message.properties | keys' a2a_schema.json

# 5. Check if a property is required
jq '.definitions.Message.required' a2a_schema.json

# 6. Find all types with a specific property
jq '.definitions | to_entries[] | select(.value.properties.taskId) | .key' a2a_schema.json

# 7. Get the type of a specific property
jq '.definitions.Message.properties.parts.items' a2a_schema.json

# 8. Find all enum values
jq '.. | .enum? // empty' a2a_schema.json | sort -u

# 9. Check discriminator fields (like "kind" or "type")
jq '.definitions.Part' a2a_schema.json

# 10. Find all error codes
jq '[.. | .properties?.code?.const? // empty] | unique' a2a_schema.json
```

## Common Investigation Templates

### "What fields does X have?"
```bash
TYPE="Message"  # Change this
jq --arg type "$TYPE" '.definitions[$type].properties | keys' a2a_schema.json
```

### "Is field Y required in X?"
```bash
TYPE="Message"  # Change this
FIELD="messageId"  # Change this
jq --arg type "$TYPE" --arg field "$FIELD" '
  .definitions[$type].required // [] | index($field) != null
' a2a_schema.json
```

### "What's the exact structure of a request?"
```bash
METHOD="SendMessageRequest"  # Change this
jq --arg method "$METHOD" '.definitions[$method]' a2a_schema.json | less
``` 