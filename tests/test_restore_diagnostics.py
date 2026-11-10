from backend.audit_restore import restore_failure_code


def test_provider_failures_are_actionable_without_disclosing_credentials():
    cases={
        'password authentication failed for user secret-user':'authentication_failed',
        'could not translate host name private-db.example':'dns_failed',
        'connection timeout expired at postgresql://user:secret@host/db':'connection_timeout',
        'Your compute time quota is exceeded':'quota_exceeded',
        'SSL error: certificate verify failed':'tls_failed',
        'endpoint has been disabled':'database_suspended',
        'database "secret-database" does not exist':'database_missing',
        'permission denied for schema growthlens_audit':'permission_denied',
        'A target identifier already contains different data; no rows were overwritten':'report_id_conflict',
        'unexpected private report contents':'unclassified_restore_failure',
    }
    for message,expected in cases.items():
        assert restore_failure_code(RuntimeError(message))==expected
