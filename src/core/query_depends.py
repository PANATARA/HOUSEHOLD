from fastapi import Query


def get_pagination_params(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, le=50),
):
    return offset, limit
