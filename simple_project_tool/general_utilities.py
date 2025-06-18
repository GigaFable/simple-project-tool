INDENT_SPACES = 4


def is_leaf(stage):
    return not ("parallel_stages" in stage or "stages" in stage)


class AlphaLabelGenerator:
    def __init__(self):
        self.n = 1

    def next(self):
        label = self._number_to_label(self.n)
        self.n += 1
        return label

    @staticmethod
    def _number_to_label(n):
        result = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result = chr(rem + ord("A")) + result
        return result


class NodeRefGenerator:
    def __init__(self, prefix):
        self.n = 1
        self.prefix = prefix

    def next(self):
        label = f"{self.prefix}{self.n}"
        self.n += 1
        return label
