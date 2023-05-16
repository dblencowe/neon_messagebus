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

from os.path import join, dirname, abspath
from time import time, sleep
from threading import Event, Thread

import mock
from ovos_bus_client import MessageBusClient, Message

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from neon_messagebus.service import NeonBusService


class TestMessageUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.service = NeonBusService(debug=True, daemonic=True)
        cls.service.start()
        cls.service.started.wait()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.service.shutdown()

    def test_get_messagebus(self):
        from neon_messagebus.util.message_utils import get_messagebus
        bus = get_messagebus()
        self.assertIsInstance(bus, MessageBusClient)
        self.assertTrue(bus.connected_event.is_set())
        self.assertTrue(bus.started_running)

        bus = get_messagebus(False)
        self.assertIsInstance(bus, MessageBusClient)
        self.assertFalse(bus.connected_event.is_set())
        self.assertFalse(bus.started_running)

    def test_send_message(self):
        from neon_messagebus.util.message_utils import get_messagebus, \
            send_message
        received: Message = None
        received_event = Event()
        received_event.clear()

        def message_handler(message):
            nonlocal received
            received = message
            received_event.set()

        client_bus = get_messagebus()
        client_bus.on("unit_test_message", message_handler)

        test_msg = Message("unit_test_message", {"time": time()},
                           {"test": "send Message Object"})
        send_message(test_msg)
        received_event.wait()
        self.assertEqual(test_msg.serialize(), received.serialize())
        received_event.clear()
        received = None

        send_message(test_msg.serialize())
        received_event.wait()
        self.assertEqual(test_msg.serialize(), received.serialize())
        received_event.clear()
        received = None

        send_message(test_msg.msg_type, test_msg.data, test_msg.context)
        received_event.wait()
        self.assertEqual(test_msg.serialize(), received.serialize())
        received_event.clear()
        client_bus.close()

    def test_send_binary_data_message(self):
        from neon_messagebus.util.message_utils import get_messagebus, \
            send_binary_data_message, decode_binary_message
        received: Message = None
        received_event = Event()
        received_event.clear()

        def message_handler(message):
            nonlocal received
            received = message
            received_event.set()

        client_bus = get_messagebus()
        client_bus.on("unit_test_message", message_handler)

        test_file = join(dirname(abspath(__file__)), "test_objects",
                         "test_image.png")
        with open(test_file, 'rb') as f:
            byte_data = f.read()

        context = {"test": "send Message Object"}
        send_binary_data_message(byte_data, "unit_test_message",
                                 msg_context=context)
        received_event.wait()
        self.assertEqual(received.context['test'], context['test'])
        self.assertEqual(received.data["binary"], byte_data.hex())
        self.assertEqual(decode_binary_message(received), byte_data)

    def test_send_binary_file_message(self):
        from neon_messagebus.util.message_utils import get_messagebus, \
            send_binary_file_message, decode_binary_message
        received: Message = None
        received_event = Event()
        received_event.clear()

        def message_handler(message):
            nonlocal received
            received = message
            received_event.set()

        client_bus = get_messagebus()
        client_bus.on("unit_test_message", message_handler)

        test_file = join(dirname(abspath(__file__)), "test_objects",
                         "test_image.png")
        with open(test_file, 'rb') as f:
            byte_data = f.read()

        context = {"test": "send Message Object"}
        send_binary_file_message(test_file, "unit_test_message",
                                 msg_context=context)
        received_event.wait()
        self.assertEqual(received.context['test'], context['test'])
        self.assertEqual(received.data["binary"], byte_data.hex())
        self.assertEqual(decode_binary_message(received), byte_data)

    def test_send_binary_file_method_invalid(self):
        from neon_messagebus.util.message_utils import send_binary_file_message
        test_file = join(dirname(abspath(__file__)), "test_objects")
        with self.assertRaises(FileNotFoundError):
            send_binary_file_message(test_file)
        with self.assertRaises(FileNotFoundError):
            send_binary_file_message('~')

    def test_decode_binary_message(self):
        from neon_messagebus.util.message_utils import decode_binary_message
        test_file = join(dirname(abspath(__file__)), "test_objects",
                         "test_image.png")
        with open(test_file, 'rb') as f:
            byte_data = f.read()
        hex_data = byte_data.hex()
        message = Message("tester", {"binary": hex_data},
                          {"context": "unit test"})
        serialized_message = message.serialize()

        self.assertEqual(decode_binary_message(hex_data), byte_data)
        self.assertEqual(decode_binary_message(message), byte_data)
        self.assertEqual(decode_binary_message(serialized_message), byte_data)


class TestSignalUtils(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from neon_messagebus.util.signal_utils import SignalManager
        cls.service = NeonBusService(debug=True, daemonic=True)
        cls.service.start()
        cls.service.started.wait()
        cls.signal_manager = SignalManager()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.service.shutdown()

    def test_00_init_signal_handlers(self):
        from neon_utils.signal_utils import init_signal_handlers
        init_signal_handlers()
        from neon_utils.signal_utils import _manager_create_signal, \
            _create_signal
        self.assertEqual(_manager_create_signal, _create_signal)
        from neon_utils.signal_utils import _manager_check_for_signal, \
            _check_for_signal
        self.assertEqual(_manager_check_for_signal, _check_for_signal)

    def test_create_signal(self):
        from neon_messagebus.util.signal_utils import Signal
        from neon_utils.signal_utils import create_signal
        self.assertTrue(create_signal("test_signal"))
        self.assertTrue(create_signal("test_signal"))
        self.assertIsInstance(self.signal_manager._signals["test_signal"],
                              Signal)
        self.assertTrue(self.signal_manager._signals["test_signal"].is_set)

    def test_check_for_signal(self):
        from neon_utils.signal_utils import check_for_signal, create_signal
        self.assertFalse(check_for_signal("test_signal"))
        create_signal("test_signal")
        self.assertTrue(check_for_signal("test_signal", -1))
        self.assertTrue(check_for_signal("test_signal", 60))
        self.assertTrue(check_for_signal("test_signal"))
        self.assertFalse(check_for_signal("test_signal"))
        create_signal("test_signal")
        self.assertTrue(check_for_signal("test_signal", 15))
        sleep(2)
        self.assertTrue(check_for_signal("test_signal", 15))
        self.assertFalse(check_for_signal("test_signal", 1))
        self.assertFalse(check_for_signal("test_signal"))

    def test_wait_for_signal_create(self):
        from neon_utils.signal_utils import check_for_signal, create_signal, \
            wait_for_signal_create

        def create_testing_signal():
            sleep(3)
            create_signal("test_signal")

        check_for_signal("test_signal")
        self.assertFalse(wait_for_signal_create("test_signal", 1))
        Thread(target=create_testing_signal).start()
        self.assertTrue(wait_for_signal_create("test_signal", 5))
        self.assertTrue(check_for_signal("test_signal"))

    def test_wait_for_signal_clear(self):
        from neon_utils.signal_utils import check_for_signal, create_signal, \
            wait_for_signal_clear

        def _clear_signal():
            sleep(3)
            self.assertTrue(check_for_signal("test_signal"))

        check_for_signal("test_signal")
        self.assertFalse(wait_for_signal_clear("test_signal", 1))
        self.assertTrue(create_signal("test_signal"))
        self.assertTrue(wait_for_signal_clear("test_signal", 1))
        Thread(target=_clear_signal).start()
        self.assertFalse(wait_for_signal_clear("test_signal", 10))
        self.assertFalse(check_for_signal("test_signal"))

    def test_threaded_signal_handling(self):
        from neon_utils.signal_utils import check_for_signal, create_signal
        create_results = []
        check_results = []

        def _create_signal(n):
            stat = create_signal(f"test_signal{n}")
            create_results.append(stat)

        def _check_signal(n):
            sleep(1)
            stat = check_for_signal(f"test_signal{n}", -1)
            check_results.append(stat)

        threads = []
        for i in range(8):
            t = Thread(target=_create_signal, args=(i,))
            threads.append(t)
            t.start()
            t = Thread(target=_check_signal, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        self.assertTrue(all(create_results))
        self.assertTrue(all(check_results))
        self.assertEqual(8, len(create_results), len(check_results))


class TestConfig(unittest.TestCase):
    def test_load_messagebus_config_default(self):
        from neon_messagebus.util.config import load_message_bus_config, \
            _DEFAULT_WS_CONFIG
        empty_config = {"host": None,
                        "port": None,
                        "route": None,
                        "ssl": None}
        self.assertEqual(load_message_bus_config(**empty_config),
                         load_message_bus_config(**_DEFAULT_WS_CONFIG))

    @mock.patch("ovos_config.config.Configuration.load_all_configs")
    def test_load_messagebus_config_configured(self, mock_load):
        mock_load.return_value = {
            "websocket": {
                "host": "test_hostname",
                "port": 80,
                "route": "/test",
                "ssl": True
            }
        }
        from neon_messagebus.util.config import load_message_bus_config, \
            MessageBusConfig
        test_config_dir = os.path.join(os.path.dirname(__file__),
                                       "test_config")
        os.environ["XDG_CONFIG_HOME"] = test_config_dir
        config = load_message_bus_config()
        self.assertEqual(config, MessageBusConfig(host="test_hostname",
                                                  port=80,
                                                  route="/test",
                                                  ssl=True))

        override_config = load_message_bus_config(port=8000, ssl=False)
        self.assertEqual(override_config,
                         MessageBusConfig(host="test_hostname",
                                          port=8000,
                                          route="/test",
                                          ssl=False))
        os.environ.pop("XDG_CONFIG_HOME")


if __name__ == '__main__':
    unittest.main()
