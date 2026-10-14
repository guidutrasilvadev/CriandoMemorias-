"""Erros da API num formato único: {"error": {"code", "message", "fields"?, "details"?}}.
`code` é estável (use no front para decidir o que mostrar); `message` já vem em português."""
from typing import Dict, Optional


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: Optional[Dict[str, str]] = None,
                 headers: Optional[Dict[str, str]] = None, details: Optional[dict] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields
        self.headers = headers or {}
        self.details = details

    def body(self) -> dict:
        err = {"code": self.code, "message": self.message}
        if self.fields:
            err["fields"] = self.fields
        if self.details:
            err["details"] = self.details  # dados para a tela decidir o que mostrar (ex.: o novo total)
        return {"error": err}


def unauthorized(message: str = "Entre na sua conta para continuar.", code: str = "unauthorized") -> ApiError:
    return ApiError(401, code, message, headers={"WWW-Authenticate": "Bearer"})


def not_found(message: str = "Não encontrado.", code: str = "not_found") -> ApiError:
    return ApiError(404, code, message)


def bad_request(message: str, code: str = "bad_request", fields: Optional[Dict[str, str]] = None) -> ApiError:
    return ApiError(400, code, message, fields)


def conflict(message: str, code: str = "conflict") -> ApiError:
    return ApiError(409, code, message)
