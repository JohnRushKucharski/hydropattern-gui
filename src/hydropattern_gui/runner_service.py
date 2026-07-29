from __future__ import annotations

import contextlib
import io
import os
import subprocess
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, TextIO

import psutil

LogChannel = Literal["stdout", "stderr"]
LogCallback = Callable[[LogChannel, str], None]


@dataclass(frozen=True)
class RunOptions:
    output_directory: str | None = None
    plot: bool | None = None
    excel: bool | None = None
    overwrite: bool | None = None
    interp: bool | None = None
    show: bool | None = None
    threshold: float | None = None
    color_map: str | None = None
    color_map_ticks: list[float] | None = None
    fillin: bool | None = None
    run_toml_options: bool = False


@dataclass(frozen=True)
class RunResult:
    command: list[str]
    cwd: Path
    exit_code: int
    cancelled: bool
    stdout: str
    stderr: str


@dataclass
class RunningRun:
    command: list[str]
    cwd: Path
    process: subprocess.Popen[str]
    _on_output: LogCallback | None = None
    _stdout_chunks: list[str] = field(default_factory=list)
    _stderr_chunks: list[str] = field(default_factory=list)
    _cancelled: bool = False
    _threads: list[threading.Thread] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._threads = [
            threading.Thread(
                target=_pump_stream,
                args=(self.process.stdout, "stdout", self._stdout_chunks, self._on_output),
                daemon=True,
            ),
            threading.Thread(
                target=_pump_stream,
                args=(self.process.stderr, "stderr", self._stderr_chunks, self._on_output),
                daemon=True,
            ),
        ]
        for thread in self._threads:
            thread.start()

    def cancel(self) -> None:
        if self.process.poll() is not None:
            return
        self._cancelled = True
        _terminate_process_tree(self.process.pid)

    def wait(self) -> RunResult:
        exit_code = self.process.wait()
        for thread in self._threads:
            thread.join()
        return RunResult(
            command=self.command,
            cwd=self.cwd,
            exit_code=exit_code,
            cancelled=self._cancelled,
            stdout="".join(self._stdout_chunks),
            stderr="".join(self._stderr_chunks),
        )


class HydropatternRunner:
    def __init__(self, executable: str = "hydropattern") -> None:
        self._executable = executable

    def build_command(
        self, config_path: str | Path, options: RunOptions | None = None
    ) -> list[str]:
        opts = options or RunOptions()
        if opts.run_toml_options and _has_explicit_output_options(opts):
            raise ValueError(
                "run_toml_options=True conflicts with explicit output options."
            )
        command = [self._executable, "run", str(config_path)]
        if opts.output_directory is not None:
            command.extend(["--output-dir", opts.output_directory])
        if opts.plot is not None:
            command.append("--plot" if opts.plot else "--no-plot")
        if opts.excel is not None:
            command.append("--excel" if opts.excel else "--no-excel")
        if opts.overwrite is not None:
            command.append("--overwrite" if opts.overwrite else "--no-overwrite")
        if opts.interp is not None:
            command.append("--interp" if opts.interp else "--no-interp")
        if opts.show is not None:
            command.append("--show" if opts.show else "--no-show")
        if opts.threshold is not None:
            command.extend(["--threshold", str(opts.threshold)])
        if opts.color_map is not None:
            command.extend(["--color-map", opts.color_map])
        if opts.color_map_ticks is not None:
            for tick in opts.color_map_ticks:
                command.extend(["--color-map-ticks", str(tick)])
        if opts.fillin is not None:
            command.append("--fillin" if opts.fillin else "--no-fillin")
        if opts.run_toml_options:
            command.append("--run-toml-options")
        return command

    def start(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunningRun:
        command = self.build_command(config_path, options)
        run_cwd = Path(cwd).resolve() if cwd is not None else Path.cwd()
        process = subprocess.Popen(
            command,
            cwd=run_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        return RunningRun(command=command, cwd=run_cwd, process=process, _on_output=on_output)

    def run(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunResult:
        return self.start(config_path, options=options, on_output=on_output, cwd=cwd).wait()


class InProcessHydropatternRunner:
    def run(
        self,
        config_path: str | Path,
        options: RunOptions | None = None,
        on_output: LogCallback | None = None,
        cwd: str | Path | None = None,
    ) -> RunResult:
        from hydropattern.cli import run as hydropattern_cli_run

        opts = options or RunOptions()
        command = HydropatternRunner(executable="hydropattern").build_command(config_path, opts)
        run_cwd = Path(cwd).resolve() if cwd is not None else Path.cwd()
        stdout_stream = _CallbackTextWriter("stdout", on_output)
        stderr_stream = _CallbackTextWriter("stderr", on_output)
        original_cwd = Path.cwd()
        exit_code = 0
        try:
            os.chdir(run_cwd)
            with contextlib.redirect_stdout(stdout_stream), contextlib.redirect_stderr(
                stderr_stream
            ):
                hydropattern_cli_run(
                    path=str(config_path),
                    plot=opts.plot,
                    output_directory=opts.output_directory,
                    write_to_excel=opts.excel,
                    overwrite=opts.overwrite,
                    interp=opts.interp,
                    show=opts.show,
                    threshold=opts.threshold,
                    color_map=opts.color_map,
                    color_map_ticks=opts.color_map_ticks,
                    fillin=opts.fillin,
                    run_toml_options=opts.run_toml_options,
                )
        except SystemExit as exc:
            exit_code = int(exc.code) if isinstance(exc.code, int) else 1
        except Exception:  # noqa: BLE001
            traceback.print_exc(file=stderr_stream)
            exit_code = 1
        finally:
            os.chdir(original_cwd)
        return RunResult(
            command=command,
            cwd=run_cwd,
            exit_code=exit_code,
            cancelled=False,
            stdout=stdout_stream.getvalue(),
            stderr=stderr_stream.getvalue(),
        )


def _has_explicit_output_options(options: RunOptions) -> bool:
    return any(
        value is not None
        for value in (
            options.output_directory,
            options.plot,
            options.excel,
            options.overwrite,
            options.interp,
            options.show,
            options.threshold,
            options.color_map,
            options.color_map_ticks,
            options.fillin,
        )
    )


def _pump_stream(
    stream: TextIO | None,
    channel: LogChannel,
    sink: list[str],
    on_output: LogCallback | None,
) -> None:
    if stream is None:
        return
    for line in stream:
        sink.append(line)
        if on_output is not None:
            on_output(channel, line)
    stream.close()


def _terminate_process_tree(pid: int) -> None:
    process = psutil.Process(pid)
    children = process.children(recursive=True)
    for child in children:
        child.terminate()
    _, alive = psutil.wait_procs(children, timeout=2.0)
    for child in alive:
        child.kill()
    process.terminate()
    try:
        process.wait(timeout=2.0)
    except psutil.TimeoutExpired:
        process.kill()


class _CallbackTextWriter(io.StringIO):
    def __init__(self, channel: LogChannel, on_output: LogCallback | None) -> None:
        super().__init__()
        self._channel = channel
        self._on_output = on_output

    def write(self, s: str) -> int:
        written = super().write(s)
        if self._on_output is not None and s:
            self._on_output(self._channel, s)
        return written
