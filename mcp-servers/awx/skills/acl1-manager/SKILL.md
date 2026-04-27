---
name: acl1-manager
description: Manage the ACL1 IP prefix list via AWX.
---
## When to use

Trigger this skill when the user says any of the following:
- "add [IP/prefix] to acl1"
- "remove [IP/prefix] from acl1"
- "add [IP/prefix] to the acl1 list"
- Any variation involving adding or removing IPs/prefixes to/from ACL1

## Variables

| Variable | Values | When to use |
|---|---|---|
| `operation` | `add` | User says "add" |
| `operation` | `remove` | User says "remove" |
| `network_prefixes` | Comma-separated IPs/CIDRs from the user's message | Always |
| `file_path` | `/home/tcarr/ACL1/ip_list.txt` | Always (fixed) |
| `acl1_playbook` | `/home/tcarr/ACL1/test.yml` | Always (fixed) |

## Steps

1. Parse `network_prefixes` from the user's message — comma-join if multiple IPs/prefixes were given.
2. Set `operation` to `add` or `remove` based on the user's intent.
3. If `mcp__awx-webhook__launch_awx_job` schema is not loaded, call `ToolSearch` with `select:mcp__awx-webhook__launch_awx_job` first, then wait for the user to confirm the tool is loaded before proceeding.
4. Call `mcp__awx-webhook__launch_awx_job` with:

```json
{
  "extra_vars": {
    "operation": "<add|remove>",
    "network_prefixes": "<comma-separated IPs/CIDRs>",
    "file_path": "/home/tcarr/ACL1/ip_list.txt",
    "acl1_playbook": "/home/tcarr/ACL1/test.yml"
  }
}
```

5. Report the job ID and status back to the user.

## Examples

User: "add 1.1.1.1 to acl1"
→ `operation: add`, `network_prefixes: 1.1.1.1`

User: "remove 8.8.8.8 from acl1"
→ `operation: remove`, `network_prefixes: 8.8.8.8`

User: "add 10.0.0.0/24 and 192.168.1.1 to acl1"
→ `operation: add`, `network_prefixes: 10.0.0.0/24,192.168.1.1`
