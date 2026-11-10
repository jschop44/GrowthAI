"""Read decrypted history only from stdin; emit counts, never report content."""
import json,sys
from backend.audit_restore import restore_snapshot,restore_failure_code
try:
    raw=sys.stdin.buffer.read(20000001)
    if len(raw)>20000000:raise ValueError('Input exceeds restore limit')
    result=restore_snapshot(json.loads(raw))
    print(json.dumps(result))
except Exception as exc:
    # Emit only fixed identifiers, never exception messages containing DSNs or reports.
    code=getattr(exc,'sqlstate',None)
    print(json.dumps({'status':'restore_failed','error_type':type(exc).__name__,
                      'reason_code':restore_failure_code(exc),
                      'sqlstate':code if isinstance(code,str) and len(code)==5 and code.isalnum() else None}),file=sys.stderr)
    print('Audit restore failed. Check snapshot integrity, target configuration and conflicting identifiers. No existing report was overwritten.',file=sys.stderr)
    raise SystemExit(1)
