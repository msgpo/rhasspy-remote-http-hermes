"""Hermes MQTT service for remote Rhasspy server"""
import argparse
import asyncio
import logging
import shlex
import typing
from collections import defaultdict

import paho.mqtt.client as mqtt
import rhasspyhermes.cli as hermes_cli

from . import RemoteHermesMqtt

_LOGGER = logging.getLogger(__name__)


def main():
    """Main method."""
    parser = argparse.ArgumentParser(prog="rhasspy-remote-http-hermes")
    parser.add_argument(
        "--asr-url",
        help="URL of remote speech to text server (e.g., http://localhost:12101/api/speech-to-text)",
    )
    parser.add_argument(
        "--asr-command", help="Command to execute for ASR (WAV to text)"
    )
    parser.add_argument(
        "--asr-train-url",
        help="URL for training speech to text server (POST with JSON)",
    )
    parser.add_argument(
        "--asr-train-command", help="Command to train ASR system (JSON to stdin)"
    )
    parser.add_argument(
        "--nlu-url",
        help="URL of remote intent recognition server (e.g., http://localhost:12101/api/text-to-intent)",
    )
    parser.add_argument(
        "--nlu-command", help="Command to execute for NLU (text to intent)"
    )
    parser.add_argument(
        "--nlu-train-url",
        help="URL for training intent recognition server (POST with JSON)",
    )
    parser.add_argument(
        "--nlu-train-command", help="Command to train NLU system (JSON to stdin)"
    )
    parser.add_argument(
        "--tts-url",
        help="URL of remote text to speech server (e.g., http://localhost:12101/api/text-to-speech)",
    )
    parser.add_argument(
        "--tts-command", help="Command to execute for TTS (text to WAV)"
    )
    parser.add_argument(
        "--wake-command",
        help="Command to execute for wake word detection (raw audio to wakewordId)",
    )
    parser.add_argument(
        "--wake-sample-rate",
        default=16000,
        help="Sample rate in hertz required by wake command (default: 16000)",
    )
    parser.add_argument(
        "--wake-sample-width",
        default=2,
        help="Sample width in bytes required by wake command (default: 2)",
    )
    parser.add_argument(
        "--wake-channels",
        default=1,
        help="Number of channels required by wake command (default: 1)",
    )
    parser.add_argument("--handle-url", help="URL of remote intent handling server")
    parser.add_argument(
        "--handle-command",
        help="Command to execute for intent handling (JSON on stdin)",
    )
    parser.add_argument(
        "--casing",
        choices=["upper", "lower", "ignore"],
        default="ignore",
        help="Case transformation for words (default: ignore)",
    )
    parser.add_argument("--certfile", help="SSL certificate file")
    parser.add_argument("--keyfile", help="SSL private key file (optional)")
    parser.add_argument(
        "--webhook", nargs=2, action="append", help="Topic/URL pairs for webhook(s)"
    )

    hermes_cli.add_hermes_args(parser)
    args = parser.parse_args()

    hermes_cli.setup_logging(args)
    _LOGGER.debug(args)

    # Split commands
    if args.asr_command:
        args.asr_command = shlex.split(args.asr_command)

    if args.asr_train_command:
        args.asr_train_command = shlex.split(args.asr_train_command)

    if args.nlu_command:
        args.nlu_command = shlex.split(args.nlu_command)

    if args.nlu_train_command:
        args.nlu_train_command = shlex.split(args.nlu_train_command)

    if args.tts_command:
        args.tts_command = shlex.split(args.tts_command)

    if args.wake_command:
        args.wake_command = shlex.split(args.wake_command)

    if args.webhook:
        webhooks = defaultdict(list)
        for topic, url in args.webhook:
            webhooks[topic].append(url)
    else:
        webhooks = None

    # Listen for messages
    client = mqtt.Client()
    hermes = RemoteHermesMqtt(
        client,
        asr_url=args.asr_url,
        asr_train_url=args.asr_train_url,
        asr_command=args.asr_command,
        asr_train_command=args.asr_train_command,
        nlu_url=args.nlu_url,
        nlu_train_url=args.nlu_train_url,
        nlu_command=args.nlu_command,
        nlu_train_command=args.nlu_train_command,
        tts_url=args.tts_url,
        tts_command=args.tts_command,
        wake_command=args.wake_command,
        wake_sample_rate=args.wake_sample_rate,
        wake_sample_width=args.wake_sample_width,
        wake_channels=args.wake_channels,
        handle_url=args.handle_url,
        handle_command=args.handle_command,
        word_transform=get_word_transform(args.casing),
        certfile=args.certfile,
        keyfile=args.keyfile,
        webhooks=webhooks,
        siteIds=args.siteId,
    )

    _LOGGER.debug("Connecting to %s:%s", args.host, args.port)
    hermes_cli.connect(client, args)
    client.loop_start()

    try:
        # Run event loop
        asyncio.run(hermes.handle_messages_async())
    except KeyboardInterrupt:
        pass
    finally:
        _LOGGER.debug("Shutting down")

        # Needed if using wake "command" system
        hermes.stop_wake_command()

        client.loop_stop()


# -----------------------------------------------------------------------------


def get_word_transform(name: str) -> typing.Optional[typing.Callable[[str], str]]:
    """Gets a word transformation function by name."""
    if name == "upper":
        return str.upper

    if name == "lower":
        return str.lower

    return None


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
