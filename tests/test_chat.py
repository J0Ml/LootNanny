import unittest

from chat import LogLine, parse_log_line


class TestChatParsing(unittest.TestCase):

    def _internal(self, line, expected):
        """
        Internal function used for performing an assertion test.

        Parameters:
            line (str): The log line to be parsed.
            expected (str): The expected parsed log line.

        Returns:
            None
        """
        log_line = parse_log_line(line)
        self.assertEqual(log_line, expected)

    def test_parse_system_message(self):
        """
        Test the `parse_system_message` function.

        This function tests the functionality of the `parse_system_message` method in the
        class. It verifies that the method correctly parses a system message string and
        creates a `LogLine` object with the expected attributes.

        Parameters:
            self (TestClass): An instance of the TestClass.
        
        Returns:
            None
        """
        msg = "2021-09-21 09:42:35 [System] [] Critical hit - Additional damage! You inflicted 519.1 points of damage"
        expected = LogLine(
            "2021-09-21 09:42:35",
            "System",
            "",
            "Critical hit - Additional damage! You inflicted 519.1 points of damage"
        )
        self._internal(msg, expected)

    def test_parse_global_message(self):
        """
        Test the parsing of a global message.

        This function tests the parsing of a global message by providing a sample message and an expected output. The function creates a `LogLine` object with the expected values and calls the `_internal` method to compare the output with the expected result.

        Parameters:
            self (TestClass): The instance of the test class.
        
        Returns:
            None
        """
        msg = "2021-09-21 09:46:31 [Globals] [] Nanashana Nana Itsanai killed a creature " \
              "(Desert Crawler Provider) with a value of 416 PED!"
        expected = LogLine(
            "2021-09-21 09:46:31",
            "Globals",
            "",
            "Nanashana Nana Itsanai killed a creature (Desert Crawler Provider) with a value of 416 PED!"
        )
        self._internal(msg, expected)

    def test_parse_global_message_brood(self):
        """
        Parses a global message log line and asserts that it correctly generates the expected LogLine object.

        Args:
            self: The TestClass instance.
        
        Returns:
            None
        """
        msg = "2021-09-21 09:46:31 [Globals] [] Nanashana Nana Itsanai killed a creature " \
              "(Disecter, Brood of Bram) with a value of 91 PED!"
        expected = LogLine(
            "2021-09-21 09:46:31",
            "Globals",
            "",
            "Nanashana Nana Itsanai killed a creature (Disecter, Brood of Bram) with a value of 91 PED!"
        )
        self._internal(msg, expected)

    def test_parse_global_message_with_apostrophe_name(self):
        """
        Test the function parse_global_message_with_apostrophe_name.

        This test case checks the behavior of the parse_global_message_with_apostrophe_name
        function when provided with a message that contains an apostrophe in the name.
        The function should correctly parse the message and return a LogLine object with
        the expected values.

        Parameters:
            self (TestClassName): An instance of the test class.

        Returns:
            None
        """
        msg = "2021-09-21 09:46:31 [Globals] [] Na'na'sha'na Na'na It'san'ai killed a creature " \
              "(Desert Crawler Provider) with a value of 416 PED!"
        expected = LogLine(
            "2021-09-21 09:46:31",
            "Globals",
            "",
            "Na'na'sha'na Na'na It'san'ai killed a creature (Desert Crawler Provider) with a value of 416 PED!"
        )
        self._internal(msg, expected)


if __name__ == '__main__':
    unittest.main()
