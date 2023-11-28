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

import os
import sys
import unittest

from time import time, sleep
from unittest.mock import Mock, patch
from click.testing import CliRunner
from ovos_bus_client import MessageBusClient, Message
from ovos_utils.log import LOG

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from neon_messagebus.service import NeonBusService


_mock_langs = Mock(stt={"stt1", "stt2"}, tts={"tts1", "tts2", "tts3"},
                   skills={"skills1"})

class TestMessagebusService(unittest.TestCase):
    def test_bus_service(self):
        called_count = 0
        callback_message = Message("test_message", {"data": "test"})

        def _callback_method(message):
            nonlocal called_count
            called_count += 1
            self.assertEqual(message, callback_message)

        clients = list()
        alive = Mock()
        started = Mock()
        ready = Mock()
        stopping = Mock()

        service = NeonBusService(alive_hook=alive, started_hook=started,
                                 ready_hook=ready, stopping_hook=stopping,
                                 debug=True, daemonic=True)
        # Test init
        alive.assert_called_once()
        started.assert_not_called()
        ready.assert_not_called()
        stopping.assert_not_called()
        # Test service start
        service.start()
        LOG.info("Waiting for service start")
        self.assertTrue(service.started.wait(15))
        alive.assert_called_once()
        started.assert_called_once()
        ready.assert_called_once()
        stopping.assert_not_called()
        # Test client connections
        for i in range(32):
            client = MessageBusClient()
            client.run_in_thread()
            clients.append(client)
        for client in clients:
            self.assertTrue(client.started_running)
            self.assertTrue(client.connected_event.wait(10))
            client.on("test_message", _callback_method)
        sender = MessageBusClient()
        sender.run_in_thread()
        sender.emit(callback_message)

        timeout = time() + 10
        while called_count < len(clients) and time() < timeout:
            sleep(1)

        self.assertEqual(len(clients), called_count)
        # Test shutdown
        self.assertTrue(service.started.is_set())
        self.assertTrue(service.is_alive())
        service.shutdown()
        stopping.assert_called_once()
        service.join()
        self.assertFalse(service.is_alive())

    @patch("neon_utils.language_utils.get_supported_languages")
    def test_get_languages(self, get_langs):
        from ovos_utils.messagebus import FakeBus
        get_langs.return_value = _mock_langs
        bus = FakeBus()
        service = NeonBusService()
        service._bus = bus
        on_langs = Mock()
        bus.on("neon.languages.get.response", on_langs)
        service._handle_get_languages(Message("neon.languages.get"))
        on_langs.assert_called_once()
        resp = on_langs.call_args[0][0]
        self.assertEqual(resp.data, {"stt": list(_mock_langs.stt),
                                     "tts": list(_mock_langs.tts),
                                     "skills": list(_mock_langs.skills)})

    def test_service_shutdown(self):
        service = NeonBusService(daemonic=False)
        service.start()
        self.assertTrue(service.is_alive())
        service.join(1)
        self.assertTrue(service.is_alive())
        service.shutdown()
        self.assertFalse(service.is_alive())
        service.join()


class TestCLI(unittest.TestCase):
    runner = CliRunner()

    @patch("neon_messagebus.cli.init_config_dir")
    @patch("neon_messagebus.service.__main__.main")
    def test_run(self, main, init_config):
        from neon_messagebus.cli import run
        self.runner.invoke(run)
        init_config.assert_called_once()
        main.assert_called_once()


if __name__ == '__main__':
    unittest.main()
