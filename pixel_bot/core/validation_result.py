class ValidationResult:
    """
    A class to hold the results of a validation check.
    """
    def __init__(self):
        self.is_valid = True
        self.errors = []      # Blocking issues that prevent execution
        self.warnings = []    # Non-blocking concerns that the user should know about
        self.suggestions = [] # Recommendations for script improvement

    def add_error(self, message):
        """Adds a critical error to the result."""
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message):
        """Adds a warning to the result."""
        self.warnings.append(message)

    def add_suggestion(self, message):
        """Adds a suggestion to the result."""
        self.suggestions.append(message)

    def merge(self, other_result):
        """Merges another ValidationResult into this one."""
        if not other_result.is_valid:
            self.is_valid = False
        self.errors.extend(other_result.errors)
        self.warnings.extend(other_result.warnings)
        self.suggestions.extend(other_result.suggestions)
