import unittest
from unittest.mock import Mock

from priority_hotkeys import PriorityHotkeys


class PriorityHotkeyTests(unittest.TestCase):
    def setUp(self):
        self.hook = PriorityHotkeys.__new__(PriorityHotkeys)
        self.hook.api = Mock()
        self.hook.hwnd = 123
        self.hook.bindings = {(0, 0x6D): 1, (0, 0x6B): 2}
        self.hook.consumed = set()

    def test_numpad_minus_consumed_once_until_release(self):
        self.assertTrue(self.hook.process_key(0x6D, True, 0))
        self.assertTrue(self.hook.process_key(0x6D, True, 0))
        self.hook.api.PostMessageW.assert_called_once_with(123, 0x312, 1, 0)
        self.assertTrue(self.hook.process_key(0x6D, False, 0))
        self.assertTrue(self.hook.process_key(0x6D, True, 0))
        self.assertEqual(self.hook.api.PostMessageW.call_count, 2)

    def test_regular_minus_and_unconfigured_keys_pass_through(self):
        for key in (0xBD, 0x41, 0x0D):
            self.assertFalse(self.hook.process_key(key, True, 0))
            self.assertFalse(self.hook.process_key(key, False, 0))
        self.hook.api.PostMessageW.assert_not_called()

    def test_modifiers_must_match(self):
        self.assertFalse(self.hook.process_key(0x6D, True, 2))
        self.hook.api.PostMessageW.assert_not_called()

    def test_release_still_consumed_after_modifier_change(self):
        self.hook.process_key(0x6D, True, 0)
        self.assertTrue(self.hook.process_key(0x6D, False, 2))

    def test_numpad_plus_uses_other_action(self):
        self.assertTrue(self.hook.process_key(0x6B, True, 0))
        self.hook.api.PostMessageW.assert_called_once_with(123, 0x312, 2, 0)


if __name__ == '__main__':
    unittest.main()
