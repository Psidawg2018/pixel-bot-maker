from . import validation_rules

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


class ScriptValidator:
    """
    A class to validate action sequences and individual steps.
    """
    def __init__(self):
        # A list of validation functions to be applied to each step.
        self.step_rules = [
            validation_rules.validate_required_fields,
            validation_rules.validate_image_paths,
            validation_rules.validate_variable_syntax,
            validation_rules.validate_wait_times,
            validation_rules.validate_unreachable_code,
        ]
        # A list of validation functions for the whole sequence (for context-aware checks).
        self.sequence_rules = [
            validation_rules.validate_variable_definition,
        ]

    def validate_sequence(self, sequence):
        """
        Performs a comprehensive validation of the entire script sequence.
        """
        full_result = ValidationResult()
        if not isinstance(sequence, list):
            full_result.add_error("Sequence is not a valid list.")
            return full_result

        for i, step in enumerate(sequence):
            # Add context for rules that might need it
            context = {'index': i, 'sequence': sequence}
            step_result = self.validate_step(step, context)

            # Prepend step number to messages for clarity
            for error in step_result.errors:
                full_result.add_error(f"Step {i+1}: {error}")
            for warning in step_result.warnings:
                full_result.add_warning(f"Step {i+1}: {warning}")
            for suggestion in step_result.suggestions:
                full_result.add_suggestion(f"Step {i+1}: {suggestion}")

        # Run sequence-level validation rules
        for rule in self.sequence_rules:
            full_result.merge(rule(sequence))

        return full_result

    def validate_step(self, step, context=None):
        """
        Performs validation on a single step, with optional context
        from its position in a sequence.
        """
        step_result = ValidationResult()
        if not isinstance(step, dict):
            step_result.add_error("Step is not a valid dictionary.")
            return step_result

        for rule in self.step_rules:
            # Pass context to rules that might need it
            result = rule(step)
            step_result.merge(result)
        return step_result

    def validate_dependencies(self, sequence):
        """
        Checks for external dependencies required by the script.
        Currently, this is handled by the main validation methods.
        """
        # This method can be expanded to check for things like Tesseract installation, etc.
        # For now, file path checks are handled in `validate_image_paths`.
        return self.validate_sequence(sequence)
