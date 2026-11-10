"""Read decrypted history only from stdin; emit counts, never report content."""
import json,sys
from backend.audit_restore import restore_snapshot
try:
    raw=sys.stdin.buffer.read(20000001)
    if len(raw)>20000000:raise ValueError('Input exceeds restore limit')
    result=restore_snapshot(json.loads(raw))
    print(json.dumps(result))
except Exception:
    print('Audit restore failed. Check snapshot integrity, target configuration and conflicting identifiers. No existing report was overwritten.',file=sys.stderr)
    raise SystemExit(1)
