from io import BytesIO


class MinioStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool):
        from minio import Minio

        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_pdf(self, file_key: str, content: bytes) -> None:
        self.ensure_bucket()
        self.client.put_object(
            self.bucket,
            file_key,
            BytesIO(content),
            length=len(content),
            content_type="application/pdf",
        )

    def healthcheck(self) -> None:
        self.ensure_bucket()

