class RedisStreamConsumer:
    def __init__(self, redis_url: str, stream_name: str, group_name: str, consumer_name: str, block_ms: int = 5000):
        import redis

        self.client = redis.Redis.from_url(redis_url)
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.block_ms = block_ms

    def ensure_group(self) -> None:
        from redis.exceptions import ResponseError

        try:
            self.client.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def read_messages(self, count: int = 1) -> list[tuple[str, str]]:
        messages = self.client.xreadgroup(
            self.group_name,
            self.consumer_name,
            streams={self.stream_name: ">"},
            count=count,
            block=self.block_ms,
        )
        tasks: list[tuple[str, str]] = []
        for _, stream_messages in messages:
            for message_id, fields in stream_messages:
                decoded_id = message_id.decode() if isinstance(message_id, bytes) else str(message_id)
                report_id = self._decode_fields(fields).get("report_id")
                if report_id:
                    tasks.append((decoded_id, report_id))
        return tasks

    def ack(self, message_id: str) -> None:
        self.client.xack(self.stream_name, self.group_name, message_id)

    def healthcheck(self) -> None:
        self.client.ping()

    @staticmethod
    def _decode_fields(fields: dict) -> dict[str, str]:
        decoded: dict[str, str] = {}
        for key, value in fields.items():
            key_text = key.decode() if isinstance(key, bytes) else str(key)
            value_text = value.decode() if isinstance(value, bytes) else str(value)
            decoded[key_text] = value_text
        return decoded

