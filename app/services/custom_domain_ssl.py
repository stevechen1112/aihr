import os
import shlex
import subprocess
from dataclasses import dataclass

from app.config import settings


@dataclass
class ProvisionCommandResult:
    success: bool
    detail: str


def ssl_automation_enabled() -> bool:
    return bool((settings.CUSTOM_DOMAIN_SSL_COMMAND_TEMPLATE or "").strip())


def _split_command(command: str) -> list[str]:
    return shlex.split(command, posix=os.name != "nt")


def _normalize_output(*parts: str) -> str:
    output = "\n".join(part.strip() for part in parts if part and part.strip())
    if not output:
        return "Command completed"
    return output[:500]


def run_ssl_provisioning(domain: str) -> ProvisionCommandResult:
    template = (settings.CUSTOM_DOMAIN_SSL_COMMAND_TEMPLATE or "").strip()
    if not template:
        return ProvisionCommandResult(False, "SSL automation command is not configured")

    command = _split_command(template.replace("{domain}", domain))
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=settings.CUSTOM_DOMAIN_SSL_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        return ProvisionCommandResult(
            False,
            _normalize_output(completed.stderr, completed.stdout),
        )

    reload_command = (settings.CUSTOM_DOMAIN_SSL_RELOAD_COMMAND or "").strip()
    if reload_command:
        reload_result = subprocess.run(
            _split_command(reload_command.replace("{domain}", domain)),
            capture_output=True,
            text=True,
            timeout=settings.CUSTOM_DOMAIN_SSL_TIMEOUT_SECONDS,
            check=False,
        )
        if reload_result.returncode != 0:
            return ProvisionCommandResult(
                False,
                _normalize_output(reload_result.stderr, reload_result.stdout),
            )

    return ProvisionCommandResult(
        True,
        _normalize_output(completed.stdout, completed.stderr),
    )
