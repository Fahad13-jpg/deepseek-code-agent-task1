"""Desktop entrypoint, plus isolated package self-test and unittest child modes."""
import sys
from pathlib import Path

# Also supports `python -I main.py` for the restricted-environment test child.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    if "--run-python-tests" in sys.argv:
        from codeagent.runner import child_main
        root = sys.argv[sys.argv.index("--run-python-tests") + 1]
        # Windowed PyInstaller executables have no stdout/stderr. Write directly
        # to the log also opened by the parent process.
        if sys.stdout is None or sys.stderr is None:
            sys.stdout = sys.stderr = open(Path(root) / ".agent" / "child-tests.log", "w", encoding="utf-8", buffering=1)
        return child_main(root)
    if "--self-test" in sys.argv:
        from codeagent.selftest import run_self_test
        output = Path(sys.argv[sys.argv.index("--output") + 1]) if "--output" in sys.argv else Path.home() / "Documents" / "DeepSeek Agent Self Test"
        return run_self_test(output)
    from codeagent.ui import main as ui_main
    return ui_main()


if __name__ == "__main__":
    raise SystemExit(main())
