# Knowledge-base implementation safety and rollback

## Verified restore points (2026-11-04)
- Growth Lens repository: `jschop44/GrowthAI`, branch `restore/pre-knowledge-base-2026-11-04`, commit `37a3cb56199bdb75892acd4e57716f891b5a51fb`.
- LeadFlow repository: `jschop44/LeadFlow`, branch `restore/pre-knowledge-base-2026-11-04`, commit `88eb4d7d03eb69dcbd54e0217c76f3d7d3a23e01`.
- Neon project: `noisy-bread-73612102`. Production branch: `br-green-union-b8v06iyf`. Backup branch: `br-raspy-hat-b8rljjhy` (`backup-pre-knowledge-base-2026-11-04`), verified READY. This branch is a point-in-time snapshot, not a separately exported backup. Verify backup contents before any production database restore. Neon storage quotas and retention apply.
- Both applications default to `KNOWLEDGE_BASE_ENABLED=false`. The feature is not enabled merely by deploying code.

## Safety contract
1. Keep business-owned documents and prospect documents in separate collections, with explicit source ownership, citations, and scoped retrieval.
2. Implement all new storage in namespaced `kb_*` tables. Never modify or delete existing lead, audit, learning, OAuth, or feedback tables for knowledge-base setup.
3. Do not store uploaded originals on Render's ephemeral disk. Choose persistent storage within free limits; reject uploads until secure storage and authorization exist.
4. Feature-flag every new retrieval and document-management route. Default to OFF, including if the environment variable is absent.
5. Do not send emails automatically. Human confirmation remains mandatory.
6. Before schema migration, verify the backup with read-only queries and confirm adequate free-tier capacity.

## Disable without deleting
Set `KNOWLEDGE_BASE_ENABLED=false` in **both** Render services and redeploy. Verify their health endpoints report `knowledge_base.enabled=false` (Growth Lens) and `knowledgeBase.enabled=false` (LeadFlow). Existing audit and outreach features should continue working. This does not delete stored documents.

## Code rollback
Deploy the exact restore commit of each repository using a new rollback branch or a controlled revert. Do not force-push `main` or blindly restore production database data. Verify the app starts, authentication works, and existing leads/audits remain accessible. Record any post-restore changes to unrelated features before deciding whether to discard them.

## Complete knowledge-base removal (requires explicit approval)
1. Disable both feature flags and stop ingestion.
2. Export or preserve any documents the owner wants to keep.
3. Inventory only knowledge-base-specific tables, indexes, object-storage keys and API credentials. Confirm there are no references from existing app records.
4. With explicit owner approval, delete only the new knowledge-base storage objects and `kb_*` tables in a transaction/migration with a dry-run inventory. Never drop shared databases or existing business tables.
5. Remove knowledge-base routes/UI and revoke dedicated storage credentials.
6. Recheck health, lead discovery, email drafts, connected Gmail and Growth Lens audits. Record deletion results.

## Recovery limitations
Git branches preserve code, not live data. Neon branch snapshots preserve database state at creation time, not later writes. Rolling back the entire production database would discard newer unrelated data and must not be done automatically. Already sent email cannot be recalled. Browser-local templates are not part of the Neon backup. A separate export is recommended for long-term disaster recovery.
