class Common:
    @staticmethod
    def get_create_values(**kwargs):
        model = kwargs.pop("model")  # noqa: F841
        result = []
        max_length = max(len(value) if isinstance(value, list) else 1 for value in kwargs.values())
        for i in range(max_length):
            combination = {}
            for key, value in kwargs.items():
                combination[key] = value[i % len(value)] if isinstance(value, list) else value
            result.append(combination)
        return result

    @staticmethod
    def get_write_values(**kwargs):
        model = kwargs.pop("model")  # noqa: F841
        return kwargs
