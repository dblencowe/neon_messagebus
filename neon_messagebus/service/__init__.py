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
from time import sleep

import tornado.options

from os.path import expanduser, isfile
from threading import Thread, Event
from tornado import web, ioloop
from neon_utils import LOG

from neon_messagebus.util.config import load_message_bus_config

from mycroft.messagebus.service.event_handler import MessageBusEventHandler


class NeonBusService(Thread):
    def __init__(self, config=None, debug=False, daemonic=False):
        self._started = Event()
        super().__init__()
        self.config = config or load_message_bus_config()
        self.debug = debug
        self.setDaemon(daemonic)
        self._stopping = Event()

        self._app = None
        self._loop = None

    @property
    def started(self) -> Event:
        return self._started

    def run(self):
        self._stopping.clear()

        LOG.info('Starting message bus service...')
        self._init_tornado()
        self._listen()
        LOG.info('Message bus service started!')
        ioloop.IOLoop.instance().start()
        # self._stopping.wait()
        # _loop.stop()
        # self._started.set()

    def _init_tornado(self):
        # Disable all tornado logging so mycroft loglevel isn't overridden
        tornado.options.parse_command_line(sys.argv + ['--logging=None'])
        # get event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    def _listen(self):
        routes = [(self.config.route, MessageBusEventHandler)]
        application = web.Application(routes, debug=self.debug)
        ssl_options = None
        LOG.info(f"Starting Messagebus server with config: {self.config}")
        if self.config.ssl:
            cert = expanduser(self.config.ssl_cert)
            key = expanduser(self.config.ssl_key)
            if not isfile(key) or not isfile(cert):
                LOG.error(
                    "ssl keys dont exist, falling back to unsecured socket")
            else:
                LOG.info("using ssl key at " + key)
                LOG.info("using ssl certificate at " + cert)
                ssl_options = {"certfile": cert, "keyfile": key}
        if ssl_options:
            LOG.info("wss listener started")
            self._app = application.listen(self.config.port, self.config.host,
                                           ssl_options=ssl_options)
        else:
            LOG.info("ws listener started")
            self._app = application.listen(self.config.port, self.config.host)

    def shutdown(self):
        LOG.info("Messagebus Server shutting down.")
        self._app.stop()
        loop = ioloop.IOLoop.instance()
        loop.add_callback(loop.stop)
        loop.close()
        self._loop.call_soon_threadsafe(self._loop.stop)
        while self._loop.is_running():
            LOG.debug("Waiting for loop to stop...")
            sleep(1)
        self._loop.close()
