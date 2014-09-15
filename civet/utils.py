import os


def file_exists_in_env_path(file):
    def is_executable(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    path, name = os.path.split(file)
    if path and is_executable(file):
        return True

    path_str = os.getenv('PATH') or os.defpath
    paths = path_str.split(os.pathsep)

    for path in paths:
        full_path = os.path.join(path, file)
        if is_executable(full_path):
            return True
    return False
