import json

from numpy import identity
from pandas import DataFrame
from pandas.testing import assert_frame_equal
import pytest
import responses

from cellengine.resources.compensation import Compensation
from cellengine.resources.fcs_file import FcsFile
from cellengine.utils import converter


EXP_ID = "5d38a6f79fae87499999a74b"


@pytest.fixture(scope="function")
def fcs_file(fcs_files):
    file = fcs_files[0]
    file.update({"experimentId": EXP_ID})
    return FcsFile.from_dict(file)


@pytest.fixture(scope="function")
def compensation(compensations):
    comp = compensations[0]
    comp.update({"experimentId": EXP_ID})
    return converter.structure(comp, Compensation)


def properties_tester(comp):
    assert type(comp) is Compensation
    assert hasattr(comp, "_id")
    assert hasattr(comp, "name")
    assert hasattr(comp, "experiment_id")
    assert hasattr(comp, "channels")
    assert hasattr(comp, "N")
    assert comp.N == len(comp.dataframe)
    assert hasattr(comp, "dataframe")
    assert type(comp.dataframe) is DataFrame
    assert all(comp.dataframe.index == comp.channels)
    assert hasattr(comp, "apply")
    assert hasattr(comp, "dataframe_as_html")


def test_compensation_properties(compensation):
    properties_tester(compensation)


@responses.activate
def test_should_post_compensation(client, ENDPOINT_BASE, compensations):
    responses.add(
        responses.POST,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations",
        json=compensations[0],
    )
    comp = Compensation(None, EXP_ID, "test_comp", ["a", "b"], [1, 0, 0, 1])
    comp = client.create(comp)
    properties_tester(comp)


@responses.activate
def test_creates_compensation(client, ENDPOINT_BASE, compensations):
    responses.add(
        responses.POST,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations",
        json=compensations[0],
    )
    comp = Compensation.create(EXP_ID, "test-comp", ["a", "b"], [1, 0, 0, 1])
    properties_tester(comp)


@responses.activate
def test_creates_compensation_with_dataframe(client, ENDPOINT_BASE, compensations):
    responses.add(
        responses.POST,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations",
        json=compensations[0],
    )
    df = DataFrame([[1, 0], [0, 1]], columns=["a", "b"], index=["a", "b"])
    comp = Compensation.create(EXP_ID, "test-comp", dataframe=df)
    properties_tester(comp)


@responses.activate
def test_raises_TypeError_when_wrong_arg_combo_is_passed(
    client, ENDPOINT_BASE, compensations
):
    responses.add(
        responses.POST,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations",
        json=compensations[0],
    )
    with pytest.raises(TypeError) as err:
        Compensation.create(EXP_ID, "test-comp", spill_matrix=[0, 1])
    assert err.value.args[0] == "Both 'channels' and 'spill_matrix' are required."

    with pytest.raises(TypeError) as err:
        Compensation.create(EXP_ID, "test-comp", channels=["a", "b"])
    assert err.value.args[0] == "Both 'channels' and 'spill_matrix' are required."

    with pytest.raises(TypeError) as err:
        Compensation.create(
            EXP_ID, "test-comp", channels=["a", "b"], dataframe=DataFrame()
        )
    assert err.value.args[0] == (
        "Only one of 'dataframe' or {'channels', 'spill_matrix'} may be assigned."
    )


@responses.activate
def test_should_delete_compensation(ENDPOINT_BASE, compensation):
    responses.add(
        responses.DELETE,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations/{compensation._id}",
    )
    deleted = compensation.delete()
    assert deleted is None


@responses.activate
def test_should_update_compensation(ENDPOINT_BASE, compensation):
    """Test that the .update() method makes the correct call. Does not test
    that the correct response is made; this should be done with an integration
    test.
    """
    # patch the mocked response with the correct values
    response = converter.unstructure(compensation)
    response.update({"name": "newname"})
    responses.add(
        responses.PATCH,
        ENDPOINT_BASE + f"/experiments/{EXP_ID}/compensations/{compensation._id}",
        json=response,
    )
    compensation.name = "newname"
    compensation.update()
    properties_tester(compensation)
    assert json.loads(responses.calls[0].request.body) == response


def test_create_from_spill_string(spillstring):
    comp = Compensation.from_spill_string(spillstring)
    spillstring.replace
    assert type(comp) is Compensation

    assert comp.channels == [
        "Ax488-A",
        "PE-A",
        "PE-TR-A",
        "PerCP-Cy55-A",
        "PE-Cy7-A",
        "Ax647-A",
        "Ax700-A",
        "Ax750-A",
        "PacBlu-A",
        "Qdot525-A",
        "PacOrange-A",
        "Qdot605-A",
        "Qdot655-A",
        "Qdot705-A",
    ]


@responses.activate
def test_apply_comp_errors_for_nonmatching_channels(compensation, acea_fcs_file):
    with pytest.raises(IndexError):
        compensation.apply(acea_fcs_file)


@responses.activate
def test_apply_compensation_to_fcs_file_with_matching_kwargs(
    ENDPOINT_BASE, compensation, fcs_file
):
    # Given: a Compensation with channels as a subset of the FcsFile events
    responses.add(
        responses.GET,
        f"{ENDPOINT_BASE}/experiments/{EXP_ID}/fcsfiles/{fcs_file._id}.fcs",
        body=open("tests/data/Acea - Novocyte.fcs", "rb"),
    )
    events = fcs_file.get_events(inplace=True, testKwarg="foo")
    assert fcs_file._events_kwargs == {"testKwarg": "foo"}

    ix = list(events.columns)
    compensation.dataframe = DataFrame(identity(24), index=ix, columns=ix)
    compensation.channels = ix

    # When: a Compensation is applied
    results = compensation.apply(fcs_file, testKwarg="foo")

    # Then: events should be compensated
    assert all(results == events)
    assert (
        responses.assert_call_count(
            f"{ENDPOINT_BASE}/experiments/{EXP_ID}/fcsfiles/{fcs_file._id}.fcs?testKwarg=foo",
            1,
        )
        is True
    )


@responses.activate
def test_apply_comp_compensates_values(
    acea_events_compensated, acea_fcs_file, acea_compensation
):
    """This test compares results from file-internal compensation calculated
    by the Python toolkit to one calculated by CellEngine. See
    tests/fixtures/compensated_events.py for details on the fixtures used
    here."""
    # Given:
    # - a file-internal compensation (see tests/fixtures/compensated_events.py)
    # - an FcsFile with uncompensated events

    # When: the Compensation is applied to a file
    results = acea_compensation.apply(acea_fcs_file, inplace=False)

    # Then: events should be compensated correctly
    assert_frame_equal(results.head(5), acea_events_compensated.head(5))
