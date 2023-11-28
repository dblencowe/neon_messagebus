# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import asyncio
import sys
import tornado.options

from time import sleep
from os.path import expanduser, isfile
from threading import Thread, Event

from ovos_bus_client import MessageBusClient, Message
from ovos_utils.process_utils import StatusCallbackMap, ProcessStatus
from tornado import web, ioloop
from ovos_utils.log import LOG
from ovos_config.config import Configuration
from ovos_messagebus.event_handler import MessageBusEventHandler
from ovos_messagebus.load_config import load_message_bus_config

from neon_messagebus.util.mq_connector import start_mq_connector
from neon_messagebus.util.signal_utils import SignalManager


def on_ready():
    LOG.info('Messagebus is ready.')


def on_stopping():
    LOG.info('Messagebus service is shutting down...')


def on_error(e='Unknown'):
    LOG.error('Messagebus service failed to launch ({}).'.format(repr(e)))


def on_alive():
    LOG.debug("Messagebus client alive")


def on_started():
    LOG.debug("Messagebus client started")


class NeonBusService(Thread):
    def __init__(self, ready_hook=on_ready, error_hook=on_error,
                 stopping_hook=on_stopping, alive_hook=on_alive,
                 started_hook=on_started,
                 config=None, debug=False, daemonic=False):
        super().__init__()
        callbacks = StatusCallbackMap(on_ready=ready_hook,
                                      on_error=error_hook,
                                      on_stopping=stopping_hook,
                                      on_alive=alive_hook,
                                      on_started=started_hook)
        self.service_id = "bus"
        self.status = ProcessStatus(self.service_id, callback_map=callbacks)
        self.status.set_alive()

        self.config = config or Configuration()
        self.debug = debug
        self.daemon = daemonic
        self._stopping = Event()
        self._running = Event()

        self._bus = None
        self._app = None
        self._loop = None
        self._loop_thread = None
        self._signal_manager = None
        self._mq_connector = None

    @property
    def started(self) -> Event:
        return self._running

    def run(self):
        self.status.set_started()
        self._stopping.clear()

        LOG.info('Starting message bus service...')
        self._init_tornado()
        self._listen()
        self._loop_thread = Thread(target=ioloop.IOLoop.instance().start)
        self._loop_thread.start()

        self._bus = self._init_bus_client()
        self._init_signal_manager()
        self._init_mq_connector()

        self.status.set_ready()
        self._running.set()
        LOG.info('Message bus service started!')
        self._stopping.wait()

    def _init_bus_client(self) -> MessageBusClient:
        config_dict = {k: v for k, v in self.config.get("websocket", {}).items()
                       if k in ("host", "port", "route", "ssl")}
        config_dict['host'] = "0.0.0.0"
        bus = MessageBusClient(**config_dict)
        bus.run_in_thread()
        bus.on('neon.languages.get', self._handle_get_languages)

        return bus

    def _handle_get_languages(self, message: Message):
        """
        Handle a request to get languages supported by Neon Core.
        @param message: neon.languages.get Message
        """
        from neon_utils.language_utils import get_supported_languages
        supported_langs = get_supported_languages()
        self._bus.emit(message.response({"stt": list(supported_langs.stt),
                                         "tts": list(supported_langs.tts),
                                         "skills": list(supported_langs.skills)
                                         }))

    def _init_signal_manager(self):
        self._signal_manager = SignalManager(self._bus)
        LOG.info("Signal Manager started")

    def _init_mq_connector(self):
        if not self.config.get("MQ"):
            LOG.info("No MQ Configuration")
            return
        try:
            self._mq_connector = start_mq_connector(self.config)
            if self._mq_connector:
                LOG.info(f"MQ Connection Established to "
                         f"{self._mq_connector.config.get('server')}:"
                         f"{self._mq_connector.config.get('port')}")
            else:
                LOG.info("No MQ Credentials provided")
        except ImportError as e:
            LOG.warning(f"MQ Connector module not available: {e}")
        except Exception as e:
            LOG.error("Connector not started")
            LOG.exception(e)

    def _init_tornado(self):
        # Disable all tornado logging so mycroft loglevel isn't overridden
        tornado.options.parse_command_line(sys.argv + ['--logging=None'])
        # get event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def _listen(self):
        config = load_message_bus_config(**self.config.get('websocket', {}))
        routes = [(config.route, MessageBusEventHandler)]
        application = web.Application(routes, debug=self.debug)
        ssl_options = None
        LOG.info(f"Starting Messagebus server with config: {config}")
        if config.ssl:
            cert = expanduser(config.ssl_cert)
            key = expanduser(config.ssl_key)
            if not isfile(key) or not isfile(cert):
                LOG.error(
                    "ssl keys dont exist, falling back to unsecured socket")
            else:
                LOG.info("using ssl key at " + key)
                LOG.info("using ssl certificate at " + cert)
                ssl_options = {"certfile": cert, "keyfile": key}
        if ssl_options:
            LOG.info("wss listener started")
            self._app = application.listen(config.port, config.host,
                                           ssl_options=ssl_options)
        else:
            LOG.info("ws listener started")
            self._app = application.listen(config.port, config.host)

    def shutdown(self):
        LOG.info("Messagebus Server shutting down.")
        self.status.set_stopping()
        self._app.stop()
        loop = ioloop.IOLoop.instance()
        loop.add_callback(loop.stop)
        sleep(1)
        loop.close()
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except RuntimeError as e:
            LOG.debug(e)
        while self._loop.is_running():
            LOG.debug("Waiting for loop to stop...")
            sleep(1)
        self._loop.close()
        self._loop_thread.join()

        if self._mq_connector:
            from pika.exceptions import StreamLostError
            try:
                self._mq_connector.stop()
            except StreamLostError:
                pass

        self._stopping.set()
        LOG.info("Messagebus service stopped")
