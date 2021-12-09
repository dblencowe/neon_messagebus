# Neon Messagebus
Messagebus Module for Neon Core. This module can be treated as a replacement for the
[mycroft-core](https://github.com/MycroftAI/mycroft-core) bus module. This module handles communication between other 
connected modules.

## Neon Enhancements
`neon-messagebus` extends `mycroft.messagebus` with the following added functionality:
* Utilities for sending files and other data over the bus
* A service for managing "signals" used for IPC

## Compatibility
This package can be treated as a drop-in replacement for `mycroft.messagebus`

## Running in Docker
The included `Dockerfile` may be used to build a docker container for the neon_messagebus module. The below command may be used
to start the container.

```shell
docker run -d \
--network=host \
--name=neon_messagebus \
-v ${NEON_DATA_DIR}:/home/neon/.local/share/neon:rw \
-v ${NEON_CONFIG_DIR}:/home/neon/.config/neon:rw \
neon_messagebus
```

>*Note:* The above example assumes Docker data locations are specified in the `NEON_DATA_DIR` and `NEON_CONFIG_DIR`
> environment variables.
