class RuleError(ValueError):
    """A proposed action violates a game rule; input state is unchanged."""


def require(condition, message):
    if not condition:
        raise RuleError(message)
