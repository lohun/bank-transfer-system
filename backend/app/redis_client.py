import os

from dotenv import load_dotenv
from redis import Redis

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)
