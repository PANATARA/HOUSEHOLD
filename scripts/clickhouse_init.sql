CREATE TABLE IF NOT EXISTS rabbitmq_chore_completion
(
    payload String
)
ENGINE = RabbitMQ
SETTINGS
    rabbitmq_host_port = 'rabbitmq:5672',
    rabbitmq_exchange_name = 'clickhouse_exchange',
    rabbitmq_routing_key_list = 'completions',
    rabbitmq_exchange_type = 'direct',
    rabbitmq_format = 'JSONAsString',
    rabbitmq_username = 'myuser',
    rabbitmq_password = 'mypassword';

CREATE TABLE IF NOT EXISTS chore_completion_stats
(
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
    JSONExtract(payload, 'id','UUID') as id,
    JSONExtract(payload, 'family_id','UUID') as family_id,
    JSONExtract(payload, 'chore_id','UUID') as chore_id,
    JSONExtract(payload, 'completed_by_id','UUID') as completed_by_id,
    toDateTime(JSONExtract(payload, 'created_at','Int64') / 1000000) as created_at
FROM rabbitmq_chore_completion;
