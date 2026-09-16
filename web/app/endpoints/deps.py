from fastapi import Request

from app.services.backend_client import BackendClient


def get_client(request: Request) -> BackendClient:
    return request.app.state.backend
