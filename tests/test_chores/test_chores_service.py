from decimal import Decimal
import pytest

from chores.schemas import ChoreCreateSchema
from chores.services import ChoreCreatorService


def make_chore_data():
    return [
        ChoreCreateSchema(
            name="chore_name",
            description="chore_description",
            icon="chore_icon",
            valuation=Decimal(20),
        ),
        ChoreCreateSchema(
            name="chore_name_2",
            description="chore_description_2",
            icon="chore_icon_2",
            valuation=Decimal(10),
        ),
    ]


def assert_chore_equal(chore_obj, chore_data):
    assert chore_obj.name == chore_data.name
    assert chore_obj.description == chore_data.description
    assert chore_obj.icon == chore_data.icon
    assert chore_obj.valuation == chore_data.valuation


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chore_input",
    [
        pytest.param(make_chore_data()[0], id="single_chore"),
        pytest.param(make_chore_data(), id="chore_list"),
    ],
)
async def test_create_chore(admin_family, async_session_test, chore_input):
    _, family = admin_family

    service = ChoreCreatorService(
        family=family, db_session=async_session_test, data=chore_input
    )
    result = await service.run_process()

    if isinstance(chore_input, list):
        assert len(result) == len(chore_input)
        for res_chore, input_chore in zip(result, chore_input):
            assert_chore_equal(res_chore, input_chore)
    else:
        assert_chore_equal(result, chore_input)
