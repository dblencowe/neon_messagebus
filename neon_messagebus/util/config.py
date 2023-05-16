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
from ovos_bus_client.conf import MessageBusConfig
from ovos_config.config import Configuration


_DEFAULT_WS_CONFIG = {"host": "0.0.0.0",
                      "port": 8181,
                      "route": "/core",
                      "ssl": False}


def load_message_bus_config(**kwargs) -> MessageBusConfig:
    """
    Mycroft-compatible method to read websocket configuration from disk
    :returns: MessageBusConfig object built from global configuration
    """
    LOG.info('Loading message bus configs')
    config = Configuration()

    websocket_config = config.get('websocket') or _DEFAULT_WS_CONFIG

    ws_config = MessageBusConfig(
        host=kwargs.get('host') or websocket_config.get('host'),
        port=kwargs.get('port') or websocket_config.get('port'),
        route=kwargs.get('route') or websocket_config.get('route'),
        ssl=kwargs.get('ssl') or False if 'ssl' in kwargs else
        websocket_config.get('ssl') or False
    )
    if not all([ws_config.host, ws_config.port, ws_config.route]):
        error_msg = 'Missing one or more websocket configs'
        raise ValueError(error_msg)

    return ws_config
