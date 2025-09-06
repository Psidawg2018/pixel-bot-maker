import unittest
from pixel_bot.utils.automation import _parse_key_string

class TestAutomation(unittest.TestCase):

    def test_simple_modifier(self):
        """Tests a simple combination of one modifier and one character."""
        modifiers, main_key = _parse_key_string('ctrl+c')
        self.assertEqual(len(modifiers), 1)
        self.assertEqual(modifiers[0], 'ctrl')
        self.assertEqual(main_key, 'c')

    def test_multiple_modifiers(self):
        """Tests a combination with multiple modifiers."""
        modifiers, main_key = _parse_key_string('ctrl+shift+a')
        self.assertEqual(len(modifiers), 2)
        self.assertIn('ctrl', modifiers)
        self.assertIn('shift', modifiers)
        self.assertEqual(main_key, 'a')

    def test_special_main_key(self):
        """Tests a combination with a special key like 'enter' or 'delete'."""
        modifiers, main_key = _parse_key_string('alt+delete')
        self.assertEqual(len(modifiers), 1)
        self.assertEqual(modifiers[0], 'alt')
        self.assertEqual(main_key, 'delete')

    def test_no_modifier(self):
        """Tests a single character key."""
        modifiers, main_key = _parse_key_string('x')
        self.assertEqual(len(modifiers), 0)
        self.assertEqual(main_key, 'x')

    def test_single_special_key(self):
        """Tests a single special key without modifiers."""
        modifiers, main_key = _parse_key_string('enter')
        self.assertEqual(len(modifiers), 0)
        self.assertEqual(main_key, 'enter')

    def test_invalid_key(self):
        """Tests that an invalid key name raises a ValueError."""
        with self.assertRaises(ValueError):
            _parse_key_string('ctrl+invalidkey')

    def test_multiple_main_keys(self):
        """Tests that two non-modifier keys raise a ValueError."""
        with self.assertRaises(ValueError):
            _parse_key_string('a+b')

    def test_multiple_special_main_keys(self):
        """Tests that two special non-modifier keys raise a ValueError."""
        with self.assertRaises(ValueError):
            _parse_key_string('enter+delete')

    def test_case_insensitivity(self):
        """Tests that the function is case-insensitive."""
        modifiers, main_key = _parse_key_string('CTRL+SHIFT+B')
        self.assertEqual(len(modifiers), 2)
        self.assertIn('ctrl', modifiers)
        self.assertIn('shift', modifiers)
        self.assertEqual(main_key, 'b')

    def test_whitespace_handling(self):
        """Tests that whitespace around the '+' is handled correctly."""
        modifiers, main_key = _parse_key_string(' ctrl + f5 ')
        self.assertEqual(len(modifiers), 1)
        self.assertEqual(modifiers[0], 'ctrl')
        self.assertEqual(main_key, 'f5')

if __name__ == '__main__':
    unittest.main()
