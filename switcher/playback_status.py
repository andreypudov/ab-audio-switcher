import threading
from collections.abc import Callable

from .terminal_utils import clear_and_print


def format_elapsed_time(playback_position: int, samplerate: int) -> str:
    """Format playback position as H:MM:SS or MM:SS."""
    if samplerate <= 0:
        return "00:00"

    total_seconds = max(0, int(playback_position / samplerate))
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class PlaybackStatusDisplay:
    """Render and periodically refresh the playback status line."""

    def __init__(
        self,
        samplerate: int,
        get_playback_position: Callable[[], int],
        get_track_name: Callable[[], str],
        refresh_interval: float = 0.25,
    ):
        self._samplerate = samplerate
        self._get_playback_position = get_playback_position
        self._get_track_name = get_track_name
        self._refresh_interval = refresh_interval

        self._stop_event = threading.Event()
        self._render_lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def render(self) -> None:
        with self._render_lock:
            elapsed = format_elapsed_time(
                self._get_playback_position(),
                self._samplerate,
            )
            clear_and_print(
                f"Now playing: [{elapsed}] {self._get_track_name()}", newline=False
            )

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.wait(self._refresh_interval):
            self.render()
