# Deployment

The core runtime has no mandatory third-party dependencies beyond Python. Optional extras add PDF, Office, scholarly-HTTP, JSON-schema, and API-server support. The FastAPI server exposes completed runs and a lightweight dashboard. It is intentionally read-mostly; model credentials and manuscript uploads should be handled by the host application's security boundary.

For production use, place run storage on encrypted persistent storage, restrict network egress, inject credentials through the host secret manager, and preserve the run manifest with the submitted review artifact.
