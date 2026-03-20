# Storage Service

The `StorageService` provides object storage with pluggable backends. It supports local filesystem storage and AWS S3 (or any S3-compatible service).

## Installation

For S3 support, install the `storage` extra:

```bash
uv add "processpype[storage]"
```

Local storage works without any extra packages.

## Usage

```python
from processpype.services.storage.service import StorageService
from processpype.services.storage.models import StorageConfiguration, StorageBackend

service = app.register_service(StorageService)
service.configure(StorageConfiguration(
    backend=StorageBackend.LOCAL,
    base_path="/data/storage",
))
await app.start_service(service.name)

# Store an object
await service.put_object("reports/2024-01.csv", data=b"col1,col2\n1,2")

# Retrieve an object
obj = await service.get_object("reports/2024-01.csv")
print(obj.content)
```

## Configuration

### Local Storage

```python
from processpype.services.storage.models import StorageConfiguration, StorageBackend

config = StorageConfiguration(
    backend=StorageBackend.LOCAL,
    base_path="/data/storage",  # base directory for all objects
)
```

### S3 Storage

```python
config = StorageConfiguration(
    backend=StorageBackend.S3,
    s3_bucket="my-app-bucket",
    s3_region="us-east-1",
    s3_access_key="AKIA...",
    s3_secret_key="secret",
    # s3_endpoint="http://localhost:9000",  # for MinIO or other S3-compatible services
)
```

### YAML Configuration

```yaml
services:
  storage:
    enabled: true
    autostart: true
    backend: local
    base_path: /data/storage
```

S3:

```yaml
services:
  storage:
    enabled: true
    backend: s3
    s3_bucket: my-app-bucket
    s3_region: us-east-1
    s3_access_key: AKIA...
    s3_secret_key: secret
```

## Storage Operations

### Storing objects

```python
metadata = await service.put_object(
    "images/logo.png",
    data=image_bytes,
    metadata={"content-type": "image/png", "author": "admin"},
)
print(f"Stored {metadata.size} bytes at {metadata.path}")
```

### Retrieving objects

```python
obj = await service.get_object("images/logo.png")
print(obj.content)       # bytes
print(obj.size)          # int
print(obj.last_modified) # ISO 8601 string
print(obj.metadata)      # dict

# Get just the content
content = await service.get_object_content("images/logo.png")
```

### Checking existence

```python
exists = await service.object_exists("reports/2024-01.csv")
```

### Listing objects

```python
# List all objects
all_objects = await service.list_objects()

# List with prefix filter
reports = await service.list_objects(prefix="reports/")
for obj_meta in reports:
    print(f"{obj_meta.path}: {obj_meta.size} bytes")
```

### Deleting objects

```python
await service.delete_object("reports/2024-01.csv")
```

### Getting metadata only

```python
meta = await service.get_object_metadata("reports/2024-01.csv")
print(meta.size, meta.last_modified)
```

## Storage Models

| Model | Description |
|-------|-------------|
| `StorageObject` | Full object with `path`, `content`, `size`, `last_modified`, `metadata` |
| `StorageObjectMetadata` | Lightweight object info without content |

## Backends

### LocalStorageBackend

Stores objects as files under `base_path`. Metadata is stored alongside each object in a `.metadata.json` sidecar file. Path traversal attacks (using `..`) are blocked.

### S3StorageBackend

Uses `boto3` to interact with AWS S3. Automatically creates the bucket if it does not exist. Compatible with any S3-compatible API (MinIO, Ceph, Cloudflare R2) by setting `s3_endpoint`.

## REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/services/storage` | Service status |
| `POST` | `/services/storage/start` | Start the service |
| `POST` | `/services/storage/stop` | Stop the service |
| `POST` | `/services/storage/configure` | Configure the service |
| `POST` | `/services/storage/configure_and_start` | Configure and start |

## Configuration Reference

| Field | Default | Description |
|-------|---------|-------------|
| `backend` | `"local"` | Storage backend: `"local"` or `"s3"` |
| `base_path` | `"./data"` | Base path for local storage |
| `s3_bucket` | (none) | S3 bucket name (required for S3) |
| `s3_region` | (none) | AWS region |
| `s3_endpoint` | (none) | Custom endpoint URL (S3-compatible services) |
| `s3_access_key` | (none) | AWS access key ID |
| `s3_secret_key` | (none) | AWS secret access key |
