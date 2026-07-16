import sounddevice as sd


def get_default_hostapi_name() -> str | None:
    """Return the host API name for the default output device, if available."""
    try:
        default_device = sd.default.device
        output_device = (
            default_device[1]
            if isinstance(default_device, (tuple, list))
            else default_device
        )
        if output_device is None or int(output_device) < 0:
            return None

        device_info = sd.query_devices(int(output_device))
        hostapi_index = device_info.get("hostapi")
        if hostapi_index is None:
            return None

        hostapi_info = sd.query_hostapis(int(hostapi_index))
        hostapi_name = hostapi_info.get("name")
        return str(hostapi_name) if hostapi_name else None
    except Exception:
        return None


def build_output_stream_kwargs(
    samplerate: int,
    channels: int,
) -> tuple[dict, str | None]:
    """Build output stream kwargs tuned for low latency and transparent playback."""
    kwargs: dict = {
        "samplerate": samplerate,
        "channels": channels,
        "dtype": "float32",
        "latency": "low",
        "blocksize": 0,
        "clip_off": True,
        "dither_off": True,
    }

    hostapi_name = get_default_hostapi_name()
    message = None

    if (
        hostapi_name
        and "WASAPI" in hostapi_name.upper()
        and hasattr(sd, "WasapiSettings")
    ):
        try:
            kwargs["extra_settings"] = sd.WasapiSettings(exclusive=True)
            message = "Output mode: WASAPI exclusive + low latency"
        except Exception:
            message = "Output mode: low latency (WASAPI exclusive unavailable)"
    elif hostapi_name:
        message = f"Output mode: {hostapi_name} low latency"
    else:
        message = "Output mode: low latency"

    return kwargs, message
