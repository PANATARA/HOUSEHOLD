CREATE TABLE IF NOT EXISTS kafka_chore_completion (
    payload String,
    "schema" String
)
ENGINE = Kafka()
SETTINGS
    kafka_broker_list = 'kafka:9092',
    kafka_topic_list = 'dbserver1.public.chore_completion',
    kafka_group_name = 'clickhouse_chore_completion_consumer',
    kafka_format = 'JSONEachRow',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS chore_completion_stats (
    id UUID,
    chore_id UUID,
    family_id UUID,
    completed_by_id UUID,
    created_at DateTime

)
ENGINE = MergeTree()
ORDER BY (family_id, created_at);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_chore_completion
TO chore_completion_stats
AS
SELECT
    JSONExtract(payload,'after','id','UUID') as id,
    JSONExtract(payload,'after','family_id','UUID') as family_id,
    JSONExtract(payload,'after','chore_id','UUID') as chore_id,
    JSONExtract(payload,'after','completed_by_id','UUID') as completed_by_id,
    toDateTime(JSONExtract(payload,'after','created_at','Int64') / 1000000) as created_at
FROM kafka_chore_completion
WHERE JSONExtract(payload,'after','status','String') = 'approved';