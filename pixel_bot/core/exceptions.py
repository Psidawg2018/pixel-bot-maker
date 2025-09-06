class BotExecutionError(Exception):
    """Custom exception for bot execution errors"""
    def __init__(self, message, step_index=None, retry_count=0):
        super().__init__(message)
        self.step_index = step_index
        self.retry_count = retry_count
