import pytest
from practo.offline import offline_guard


@pytest.fixture(scope="session",autouse=True)
def no_external_network():
    with offline_guard() as attempts:
        yield attempts
    assert attempts == [], f"Unexpected outbound attempts: {attempts}"


@pytest.fixture(scope="session")
def rag(no_external_network):
    from practo.retrieval import RagCore
    return RagCore()


@pytest.fixture
def service(rag,tmp_path):
    from practo.service import ClinicService
    return ClinicService(rag,tmp_path / "requests.jsonl")
