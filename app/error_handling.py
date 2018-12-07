import logging
from typing import List, Tuple


def err(validate: bool, error_msg: str, *format_error_msg_params):
    if not validate:
        return error_msg.format(*format_error_msg_params)


class ErrorListValidator(object):
    error_list: List[str] = []

    def validate(self,
                 possible_errors: List[str]):
        logging.warning("DEPRECIATED: replace validate with validator.")
        self.error_list = self.error_list + [error for error in possible_errors if error is not None]
        return len(self.error_list) == 0

    def validator(self,
                  *possible_errors: Tuple):
        errors = (err(p[0], p[1], *p[2:]) for p in possible_errors)
        self.error_list = self.error_list + [e for e in errors if e is not None]
        return len(self.error_list) == 0
