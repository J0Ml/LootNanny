from typing import List, Any


class BaseModule(object):

    def __init__(self):
        pass

    def tick(self, lines: List[Any]):
        """
        A function that performs a tick operation.

        Args:
            lines (List[Any]): The list of lines.

        Returns:
            None
        """
        pass
