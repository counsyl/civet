import os
import signal
import sys


def collect_src_dst_dir_mappings(src_dst_tuples):
    """Create a src_dir->dst_dir dict from a list of (src, dst) tuples.

    Args:
        src_dst_tuples: A list of (src, dst) tuples. For example, passing
            [('/some/source/test.coffee', '/some/output/test.js')] results
            in the dict {'/some/source': '/some/output'}.
    """
    return {os.path.dirname(src): os.path.dirname(dst)
            for src, dst in src_dst_tuples}


def get_shortest_topmost_directories(dirs):
    """Return the shortest topmost directories from the dirs list.

    Args:
        dirs: A list of directories

    Returns:
        The shortest list of parent directories s, such that every directory
        d in dirs can be reached from one (and only one) directory in s.

        For example, given the directories /a, /a/b, /a/b/c, /d/e, /f
        since /a/b and /a/b/c can all be reached from /a, only /a is needed.
        /d/e can only be reached from /d/e and /f from /f, so the resulting
        list is /a, /d/e, and /f.
    """

    if not dirs:
        return []

    # Sort the dirs and use path prefix to eliminate covered children
    sorted_dirs = sorted(dirs)

    current = sorted_dirs.pop(0)
    results = [current]

    # To avoid the case where /foobar is treated as a child of /foo, we add
    # the / terminal to each directory before comparison
    current = current + '/'

    while sorted_dirs:
        next = sorted_dirs.pop(0)
        terminated_next = next + '/'
        if not terminated_next.startswith(current):
            current = terminated_next
            results.append(next)
    return results


def raise_error_or_kill(kill_on_error):
    """Either raise an error or terminate runserver.
    """
    if kill_on_error:
        # Tell autoreload's loader thread that we're done
        os.kill(os.getpid(), signal.SIGINT)

        # Terminate the spawned server process
        sys.exit(1)
    else:
        raise AssertionError('Asset precompilation failed.')
