from contextlib import contextmanager


@contextmanager
def temporary_file(content):
    # type: (str) -> str
    """Context manager that creates a temporary file with specified content
    and yields its name. Once the context is exited the file is deleted.
    """
    import tempfile
    file = tempfile.NamedTemporaryFile()
    file.write(content)
    file.flush()
    yield file.name
