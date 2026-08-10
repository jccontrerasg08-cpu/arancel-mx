import subprocess
import sys


def test_release_package_imports_in_fresh_process_without_pipeline_cycle():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from arancel_mx.release.package import "
                "PUBLIC_RELEASE_ASSETS, verify_publication_bundle; "
                "assert len(PUBLIC_RELEASE_ASSETS) == 6; "
                "assert callable(verify_publication_bundle)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
