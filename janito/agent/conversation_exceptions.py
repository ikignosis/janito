class MaxRoundsExceededError(Exception):
    pass


class EmptyResponseError(Exception):
    pass


class ProviderError(Exception):
    def __init__(self, message, error_data):
        self.error_data = error_data
        super().__init__(message)
