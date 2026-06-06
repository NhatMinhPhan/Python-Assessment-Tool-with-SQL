"""
Equivalent to __init__.py in plain_pyscripts.

Activates and runs judge.py files.
"""

import subprocess
import os
import sys

has_logged_in = True

def run_judge(subfolder_name: str) -> bool:
    """
    Run judge.py in the subfolder in the current directory whose name is passed to this function.

    Returns:
        the boolean value returned by run() in judge.py.
    """
    print(f'Running judge.py in \'{subfolder_name}\'...')

    # Run judge.py in the passed subfolder
    path_to_subfolder = f"{os.getcwd()}\\{subfolder_name}"
    command = [sys.executable, "judge.py"]
    subprocess.run(
        command,
        cwd = path_to_subfolder,
        capture_output=False,
        env=os.environ.copy()
    )

    print('judge_driver.py terminating...')
    pass

if __name__ == '__main__':
    run_judge('plain_pyscripts\\examination_collections')