import logging
import re


class VariableManager:
    def __init__(self, variables_dict, logger_func):
        self.variables = variables_dict
        self.log = logger_func # This is passed from App, which is now logging.info

    def _replace_match(self, match):
        """Helper function for re.sub to look up the variable."""
        var_name = match.group(1).strip()
        # Return the value if found, otherwise return the original placeholder
        return self.variables.get(var_name, match.group(0))

    def substitute(self, text):
        """
        Substitutes placeholders like {{var_name}} in a string with their
        values from the self.variables dictionary.
        """
        if not isinstance(text, str):
            return text
        # This regex finds all occurrences of {{...}}
        return re.sub(r'\{\{(.*?)\}\}', self._replace_match, text)

    def evaluate_condition(self, condition):
        """
        Evaluates a condition dictionary.
        Example: {'variable': '{{count}}', 'operator': 'is greater than', 'value': '5'}
        """
        var_name = condition.get('variable', '').strip()
        operator = condition.get('operator')
        value_to_compare_str = self.substitute(condition.get('value', ''))

        if not var_name or not operator:
            logging.error(f"Invalid condition: {condition}")
            return False

        actual_value_str = self.substitute(var_name)

        # First, attempt numeric comparison if applicable
        try:
            num_actual = float(actual_value_str)
            num_compare = float(value_to_compare_str)

            if operator == "equals":
                return num_actual == num_compare
            if operator == "not equals":
                return num_actual != num_compare
            if operator == "is greater than":
                return num_actual > num_compare
            if operator == "is less than":
                return num_actual < num_compare
            # If operator is not a numeric one (e.g., 'contains'),
            # fall through to string-based comparison.
        except (ValueError, TypeError):
            # One or both values are not numeric, so we must use string comparison.
            pass

        # String-based comparison
        if operator == "equals":
            return actual_value_str == value_to_compare_str
        if operator == "not equals":
            return actual_value_str != value_to_compare_str
        if operator == "contains":
            return value_to_compare_str in actual_value_str
        if operator == "not contains":
            return value_to_compare_str not in actual_value_str

        logging.warning(f"Unsupported operator '{operator}' for the given value types (string).")
        return False
