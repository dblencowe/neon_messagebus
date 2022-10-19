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

from ovos_utils.log import LOG
from neon_utils.configuration_utils import init_config_dir
from neon_utils.log_utils import init_log
from mycroft_bus_client.client import MessageBusClient

from neon_messagebus.service import NeonBusService
from neon_messagebus.util.signal_utils import SignalManager
from neon_messagebus.util.mq_connector import start_mq_connector
from neon_messagebus.util.config import load_message_bus_config


from mycroft.lock import Lock  # creates/supports PID locking file
from mycroft.util import wait_for_exit_signal, reset_sigint_handler


def main(**kwargs):
    init_config_dir()
    init_log(log_name="bus")
    reset_sigint_handler()
    # Create PID file, prevent multiple instances of this service
    lock = Lock("bus")
    # TODO debug should be False by default
    service = NeonBusService(debug=True, daemonic=True, **kwargs)
    service.start()
    messagebus_config = load_message_bus_config()
    config_dict = messagebus_config._asdict()
    config_dict['host'] = "0.0.0.0"
    client = MessageBusClient(**config_dict)
    if not service.started.wait(10):
        LOG.warning("Timeout waiting for service start")
    SignalManager(client)
    LOG.debug("Signal Manager Initialized")

    connector = None
    try:
        connector = start_mq_connector(config_dict)
        if connector:
            LOG.debug("MQ Connection Established")
        else:
            LOG.debug("No MQ Credentials provided")
    except ImportError:
        LOG.debug("MQ Connector module not available")
    except Exception as e:
        LOG.error("Connector not started")
        LOG.exception(e)

    service._ready_hook()
    wait_for_exit_signal()
    service.shutdown()

    if connector:
        from pika.exceptions import StreamLostError
        try:
            connector.stop()
        except StreamLostError:
            pass
    lock.delete()
    LOG.info("Messagebus service stopped")


if __name__ == "__main__":
    main()
