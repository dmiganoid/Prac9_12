class MinioStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool):
        from minio import Minio

        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def get_pdf(self, file_key: str) -> bytes | None:
        from minio.error import S3Error

        self.ensure_bucket()
        try:
            response = self.client.get_object(self.bucket, file_key)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                return None
            raise
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def healthcheck(self) -> None:
        self.ensure_bucket()

