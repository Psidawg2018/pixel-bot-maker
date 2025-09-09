import os

class ScriptPreviewEngine:
    def __init__(self, app):
        self.app = app
        self.preview_results = []

    def preview_sequence(self, sequence, target_window=None):
        """Generate detailed preview of what script will do"""
        results = []
        for i, step in enumerate(sequence):
            result = self.preview_step(step, i + 1)
            results.append(result)
        return results

    def preview_step(self, step, step_number):
        """Preview individual step with detailed info"""
        return {
            'step_number': step_number,
            'step_type': step.get('step_type', 'simple'),
            'description': self.generate_step_description(step),
            'estimated_duration': self.estimate_step_duration(step),
            'potential_issues': self.check_step_issues(step),
            'visual_info': self.get_visual_preview_info(step)
        }

    def generate_step_description(self, step):
        """Generate a human-readable description of the step."""
        # This logic is adapted from the format_step_for_display method in main_window.py
        step_type = step.get('step_type', 'simple')
        action_type = step.get('action_type')

        if step_type == 'simple':
            if action_type == 'Set Variable':
                params = step.get('action_params', {})
                return f"Set Var: '{params.get('variable_name', 'N/A')}' = '{params.get('variable_value', 'N/A')}'"
            elif action_type == 'Modify Variable':
                params = step.get('action_params', {})
                return f"Modify Var: '{params.get('modify_variable_name', 'N/A')}' {params.get('modify_variable_operation', '?')} {params.get('modify_variable_value', '?')}"
            elif action_type == 'OCR':
                params = step.get('action_params', {})
                return f"OCR to Var: '{params.get('output_variable_name', 'N/A')}'"
            else:
                mode = step.get('detection_mode', '?')
                action = step.get('action_type', '?')
                target = step.get('detection_target_name', 'Unknown')
                return f"Find {mode} '{target}', then {action}"
        elif step_type == 'conditional_loop':
            primary_target_name = step.get('primary_target', {}).get('detection_target_name', 'N/A')
            fallback_action = step.get('on_fail', {}).get('action_type', 'N/A')
            retries = step.get('max_retries', 'N/A')
            return f"CONDITIONAL ({retries}x): Find '{primary_target_name}', on fail: {fallback_action}"
        elif step_type == 'loop':
            loop_mode = step.get('loop_mode', 'repeat')
            if loop_mode == 'repeat':
                repeat_count = step.get('loop_repeat_count', 'N/A')
                return f"LOOP: Repeat {repeat_count} times"
            else:
                return f"LOOP: Until condition"
        elif step_type == 'time_based_condition':
            time_cond = step.get('time_condition', {})
            hour = time_cond.get('hour', '??')
            minute = time_cond.get('minute', '??')
            return f"TIME CONDITION: at {hour:02d}:{minute:02d}"
        elif step_type == 'wait':
            duration = step.get('duration', 0)
            return f"Wait for {duration:.2f} seconds"
        elif step_type == 'conditional_branch':
            condition = step.get('condition', {})
            var = condition.get('variable', '?').replace('{', '').replace('}', '')
            op = condition.get('operator', '?')
            val = condition.get('value', '?')
            return f"IF {var} {op} {val}"
        else:
            return "Unknown Step Type"

    def estimate_step_duration(self, step):
        """Estimate how long each step will take"""
        action_type = step.get('action_type')
        step_type = step.get('step_type', 'simple')

        # Base times for different actions
        base_times = {
            'Click': 0.5, 'Right-click': 0.5, 'Click with Offset': 0.5,
            'Type': 0.2,  # Base time, will add per-character time
            'Wait': 0.0, # The duration is the wait itself
            'OCR': 2.0,
            'Set Variable': 0.1,
            'Modify Variable': 0.1,
            'Key Combo': 0.3,
            'Scroll': 0.5,
            'Find Image': 1.5, # Assume some search time
            'Find Color': 1.0,
        }

        duration = 0.0

        # Handle container-like steps first
        if step_type in ['loop', 'conditional_branch', 'time_based_condition']:
            # These steps are containers. Their duration is the sum of their children plus a small overhead.
            # For a simple preview, we can give them a small base time, as we don't recurse here.
            duration += 0.1
            # The real duration would be calculated by summing children in the dialog
            return duration

        if step_type == 'wait':
            return float(step.get('duration', 1.0))

        if step_type == 'conditional_loop':
            # Estimate based on one successful check.
            duration += base_times.get('Find Image', 1.5) # The primary check

        if step_type == 'simple':
            action_type = step.get('action_type')
            duration += base_times.get(action_type, 1.0) # Default 1s for unknown simple actions
            if action_type == 'Type':
                text_to_type = step.get('action_params', {}).get('text', '')
                duration += len(text_to_type) * 0.05 # 50ms per character

        # Add post-action wait time, which is common to many steps
        wait_params = step.get('wait_params')
        if wait_params:
            wait_type = wait_params.get('type', 'Fixed')
            if wait_type == 'Fixed':
                duration += float(wait_params.get('fixed_time', 0.0))
            elif wait_type == 'Random':
                min_time = float(wait_params.get('min_time', 0.0))
                max_time = float(wait_params.get('max_time', 0.0))
                duration += (min_time + max_time) / 2 # Average random wait

        return duration

    def check_step_issues(self, step):
        """Identify potential issues with step execution"""
        issues = []

        # Check for missing images
        if step.get('detection_mode') == 'Image':
            targets = step.get('detection_target', [])
            if isinstance(targets, str):
                targets = [targets]
            for img_path in targets:
                if not os.path.exists(img_path):
                    issues.append(f"Image not found: {os.path.basename(img_path)}")

        # Check for missing images in 'conditional_loop' primary target
        if step.get('step_type') == 'conditional_loop':
            primary_target = step.get('primary_target', {})
            if primary_target.get('detection_mode') == 'Image':
                targets = primary_target.get('detection_target', [])
                if isinstance(targets, str):
                    targets = [targets]
                for img_path in targets:
                    if not os.path.exists(img_path):
                        issues.append(f"Primary image not found: {os.path.basename(img_path)}")
            # Check fallback action image
            on_fail = step.get('on_fail', {})
            if on_fail.get('detection_mode') == 'Image':
                targets = on_fail.get('detection_target', [])
                if isinstance(targets, str):
                    targets = [targets]
                for img_path in targets:
                     if not os.path.exists(img_path):
                        issues.append(f"Fallback image not found: {os.path.basename(img_path)}")

        # Check for very short wait times
        wait_params = step.get('wait_params', {})
        if wait_params: # Ensure wait_params exists
            wait_type = wait_params.get('type', 'Fixed')
            if wait_type == 'Fixed':
                wait_time = float(wait_params.get('fixed_time', 1.0))
                if wait_time < 0.5:
                    issues.append("Very short wait time (<0.5s) may cause timing issues.")

        return issues

    def get_visual_preview_info(self, step):
        """Get information needed for visual preview (e.g., image paths, regions)"""
        # This will be more useful for the live preview feature
        visual_info = {}
        if step.get('detection_mode') == 'Image':
            targets = step.get('detection_target', [])
            if isinstance(targets, str):
                targets = [targets]
            visual_info['images'] = [path for path in targets if os.path.exists(path)]

        if step.get('search_region'):
            visual_info['search_region'] = step['search_region']

        if step.get('action_type') == 'OCR':
             visual_info['ocr_region'] = step.get('action_params', {}).get('ocr_region')

        return visual_info
