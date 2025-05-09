
## You need to configure your .env file inroot directory
```env
PG_DATABASE=postgres
PG_USER=postgres
PG_PASSWORD=postgres
redis_url=redis://redis:6379
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres_db:5432/postgres
SECRET_KEY=mySecretKey
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=20160
S3_ACCESS_KEY=myS3AccessKey
S3_SECRET_KEY=myS3SecretKey
S3_ENDPOINT_URL=https://mys3.endpoint.url
S3_BUCKET_NAME=household-storage
METRICS_BACKEND_URL=http://household-metrics.com
```