from http import HTTPStatus

from flow_tracer_api.services import ServiceError, TraceNotFoundError


def test_service_error_keeps_message_and_status_code() -> None:
    error = TraceNotFoundError(message="Trace x not found", status_code=HTTPStatus.NOT_FOUND)

    assert isinstance(error, ServiceError)
    assert error.message == "Trace x not found"
    assert error.status_code == HTTPStatus.NOT_FOUND
    assert str(error) == "Trace x not found"
