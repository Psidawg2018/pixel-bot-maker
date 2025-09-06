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
        value_to_compare = self.substitute(condition.get('value', ''))

        if not var_name or not operator:
            logging.error(f"Invalid condition: {condition}")
            return False

        actual_value = self.substitute(var_name)

        # For numeric comparisons, try to convert both to floats
        try:
            num_actual_value = float(actual_value)
            num_value_to_compare = float(value_to_compare)
            is_numeric = True
        except (ValueError, TypeError):
            is_numeric = False

        if operator == "equals":
            return actual_value == value_to_compare
        elif operator == "not equals":
            return actual_value != value_to_compare
        elif operator == "contains":
            return value_to_compare in actual_value
        elif operator == "not contains":
            return value_to_compare not in actual_value
        elif is_numeric:
            if operator == "is greater than":
                return num_actual_value > num_value_to_compare
            elif operator == "is less than":
                return num_actual_value < num_value_to_compare

        logging.warning(f"Unsupported operator '{operator}' for non-numeric comparison.")
        return False
