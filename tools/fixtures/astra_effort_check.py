"""Read-only fixture for real OpenCode reasoning/tool compatibility checks."""


def binary_search(values, target):
    low, high = 0, len(values) - 1
    while low <= high:
        middle = (low + high) // 2
        if values[middle] == target:
            return middle
        if values[middle] < target:
            low = middle  # Intentional termination bug for the test client to identify.
        else:
            high = middle - 1
    return -1
