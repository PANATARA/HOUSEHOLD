CREATE TABLE IF NOT EXISTS rabbitmq_planned_chores
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

CREATE TABLE IF NOT EXISTS planned_chore_stats
(
    id UUID,
    chore_id UUID,
    family_id UUID,
    completed_by_id UUID,
    assigned_to_id UUID,
    due_date Date,
    sign Int8
)
ENGINE = CollapsingMergeTree(sign)
ORDER BY (family_id, due_date);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_planned_chore
TO planned_chore_stats
AS
SELECT
    JSONExtract(payload, 'id', 'UUID') as id,
    JSONExtract(payload, 'family_id', 'UUID') as family_id,
    JSONExtract(payload, 'chore_id', 'UUID') as chore_id,
    JSONExtract(payload, 'completed_by_id', 'UUID') as completed_by_id,
    JSONExtract(payload, 'assigned_to_id', 'UUID') as assigned_to_id,
    toDate(JSONExtractString(payload, 'due_date')) as due_date,
    JSONExtract(payload, 'sign', 'Int8') as sign
FROM rabbitmq_planned_chores;
