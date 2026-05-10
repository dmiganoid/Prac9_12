class RedisTaskPublisher:
    def __init__(self, redis_url: str, stream_name: str):
        import redis

        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        self.stream_name = stream_name

    def publish_report_task(self, report_id: str) -> str:
        return self.client.xadd(self.stream_name, {"report_id": report_id})

    def healthcheck(self) -> None:
        self.client.ping()

