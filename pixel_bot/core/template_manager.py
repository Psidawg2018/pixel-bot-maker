import json
import logging
import os
from .script_validator import ScriptValidator

class ScriptTemplate:
    def __init__(self, name, category, description, difficulty, estimated_time, file):
        self.name = name
        self.category = category
        self.description = description
        self.difficulty = difficulty  # Beginner, Intermediate, Advanced
        self.estimated_time = estimated_time
        self.file = file
        self.steps = []
        self.variables = []
        self.requirements = []
        self.validation_result = None

    def load_steps(self, templates_base_path):
        """Loads the sequence of steps from the template's JSON file."""
        filepath = os.path.join(templates_base_path, self.category.lower(), self.file)
        try:
            with open(filepath, 'r') as f:
                self.steps = json.load(f)
            logging.info(f"Successfully loaded steps for template: {self.name}")
        except FileNotFoundError:
            logging.error(f"Template file not found: {filepath}")
            self.steps = []
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from template file: {filepath}")
            self.steps = []
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading template file {filepath}: {e}")
            self.steps = []


class TemplateManager:
    def __init__(self, templates_base_path="pixel_bot/templates"):
        self.templates_base_path = templates_base_path
        self.templates = []
        self.categories = ["Gaming", "Productivity", "Testing", "Maintenance"]
        self.validator = ScriptValidator()

    def load_templates(self):
        """Loads all templates from the manifest file and validates them."""
        manifest_path = os.path.join(self.templates_base_path, "template_manifest.json")
        if not os.path.exists(manifest_path):
            logging.warning("Template manifest file not found. No templates will be loaded.")
            return []

        try:
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
        except Exception as e:
            logging.error(f"Error reading template manifest: {e}")
            return []

        loaded_templates = []
        for template_data in manifest_data.get("templates", []):
            template = ScriptTemplate(
                name=template_data.get("name"),
                category=template_data.get("category"),
                description=template_data.get("description"),
                difficulty=template_data.get("difficulty"),
                estimated_time=template_data.get("estimated_time"),
                file=template_data.get("file")
            )
            template.load_steps(self.templates_base_path)
            # Validate the loaded steps
            template.validation_result = self.validator.validate_sequence(template.steps)
            if not template.validation_result.is_valid:
                logging.warning(f"Template '{template.name}' has validation errors.")

            loaded_templates.append(template)

        self.templates = loaded_templates
        logging.info(f"Loaded and validated {len(self.templates)} script templates.")
        return self.templates

    def get_templates_by_category(self, category):
        """Returns a list of templates for a given category."""
        return [t for t in self.templates if t.category == category]
