"""Stable transport codes accompanying existing HTTP statuses and detail values."""

from fastapi import HTTPException

ERROR_CODES = {
    "AUTH_REQUIRED": "Supply a Bearer token for this room.",
    "INVALID_CREDENTIAL": "The token is invalid for this room.",
    "ROLE_FORBIDDEN": "This role cannot perform the operation.",
    "PLAYER_MISMATCH": "The action attempts to use a different player's identity.",
    "ROOM_NOT_FOUND": "Check the room code and variant.",
    "GAME_NOT_STARTED": "Wait for the creator to start the game.",
    "SAVED_STATE_INVALID": "The saved game needs server-side investigation.",
    "INVALID_PLAYER_NAMES": "Provide one name per registered seat.",
    "RULE_VIOLATION": "The engine rejected the move; detail explains why.",
    "STALE_REVISION": "Fetch current state and reconsider the action.",
    "STATE_CONFLICT": "State initialization/write conflicted or a writer is busy; refresh before retrying.",
    "ROOM_ALLOCATION_UNAVAILABLE": "Room allocation is unavailable; back off before retrying.",
    "REQUEST_VALIDATION_FAILED": "Correct the request using the detail array.",
    "DATABASE_UNAVAILABLE": "The service is not ready to read its database.",
    "NOT_FOUND": "The endpoint does not exist.",
    "METHOD_NOT_ALLOWED": "Use a supported HTTP method.",
    "HTTP_ERROR": "Other HTTP failure; inspect status and detail.",
}

ERROR_RESPONSES = {
    status: {
        "description": "Transport or rules error",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["code", "detail"],
                    "properties": {
                        "code": {"type": "string", "enum": list(ERROR_CODES)},
                        "detail": {},
                    },
                }
            }
        },
    }
    for status in (401, 403, 404, 405, 409, 422, 503)
}


class APIError(HTTPException):
    def __init__(self, status_code, code, detail):
        super().__init__(status_code, detail)
        self.code = code
