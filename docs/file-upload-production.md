# File Upload Production Safety

This template stores private uploads in S3-compatible object storage and keeps
metadata in PostgreSQL. Production hardening focuses on bounded memory usage,
object verification after presigned uploads, and explicit malware scanner
boundaries.

## Upload Paths

Direct multipart upload:

1. validate filename and declared content type
2. read the request body in bounded chunks up to `UPLOAD_MAX_SIZE_BYTES`
3. sniff magic bytes and run malware scanning
4. write the object privately and persist metadata

Presigned upload:

1. validate metadata and issue a short-lived PUT URL
2. client uploads directly to object storage
3. `POST /api/v1/files/presigned-upload/complete` verifies the stored object
   before metadata is persisted

## Object Verification After Presigned Upload

Completion verifies the stored object rather than trusting client metadata:

- object exists in storage
- `HEAD` metadata size matches declared `size_bytes`
- stored content type matches declared `content_type`
- downloaded bytes match declared size
- magic-byte sniffing matches declared content type
- malware scanner runs against downloaded bytes

If verification fails, metadata is not persisted and the client must upload again
or delete the orphan object through operational cleanup.

## Malware Scanner Integration

Scanner selection is controlled by:

- `UPLOAD_MALWARE_SCAN_ENABLED`
- `UPLOAD_MALWARE_SCANNER_URL`
- `UPLOAD_MALWARE_SCANNER_TIMEOUT_SECONDS`

Behavior:

- disabled: uploads skip scanning
- enabled without URL: built-in filename sentinel scanner for local/testing
- enabled with URL: HTTP scanner integration boundary

HTTP scanner contract:

```http
POST /scan
Content-Type: application/octet-stream
X-Upload-Filename: invoice.pdf

<raw file bytes>
```

Expected JSON response:

```json
{"clean": true}
```

See `docs/malware-scanning.md` for the HTTP scanner contract and production
boundaries.

## Metadata Validation

Upload metadata is validated before storage writes:

- filenames must be non-empty, bounded length, and must not contain path
  traversal markers or separators
- content types must use a valid MIME type format and appear in
  `UPLOAD_ALLOWED_CONTENT_TYPES`

## Recommended Production Checklist

- keep presigned URL expiry short
- run malware scanning in production through `UPLOAD_MALWARE_SCANNER_URL`
- monitor orphan objects created by failed presigned completions
- delete failed or rejected uploads from object storage during operational
  cleanup
- tune `UPLOAD_STREAM_CHUNK_SIZE_BYTES` for your reverse proxy and worker memory
  limits
