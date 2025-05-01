CONSTANT = 42
"""A global constant."""

global_var = "hello"
"""A global variable."""


def outer_function():
    """This is the outer function.
    It has a multi-line docstring.
    Useful for testing extraction.
    """

    def inner_function():
        """Inner function docstring."""
        pass

    return inner_function


class OuterClass:
    """OuterClass docstring."""

    CLASS_CONST = 3.14

    def method_one(self):
        """Method one docstring."""

        def nested_method_func():
            """Nested method function docstring."""
            pass

        return nested_method_func

    def method_two(self):
        """Method two docstring."""
        pass


class InnerClass(OuterClass):
    """InnerClass docstring."""

    def inner_method(self):
        """Inner method docstring."""
        pass


def another_function():
    """Another function docstring."""
    pass


if __name__ == "__main__":
    """Main block docstring."""
    print("Running as main!")
