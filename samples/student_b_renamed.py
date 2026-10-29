# totally my own work
def sort_list(data):
    size = len(data)
    for x in range(size):
        for y in range(0, size - x - 1):
            if data[y] > data[y + 1]:
                data[y], data[y + 1] = data[y + 1], data[y]
    return data


def check_prime(value):
    if value < 2:
        return False
    for k in range(2, int(value ** 0.5) + 1):
        if value % k == 0:
            return False
    return True


def fib_series(count):
    first, second = 0, 1
    out = []
    for _ in range(count):
        out.append(first)
        first, second = second, first + second
    return out
