# Copyright 2019 Streamlit Inc. All rights reserved.
# -*- coding: utf-8 -*-

"""Server related utility functions"""

from streamlit import config
from streamlit import util

# Largest message that can be sent via the WebSocket connection.
# (Limit was picked arbitrarily)
# TODO: Break message in several chunks if too large.
MESSAGE_SIZE_LIMIT = 5 * 10e7  # 50MB


def serialize_forward_msg(msg):
    """Serialize a ForwardMsg to send to a client.

    If the message is too large, it will be converted to an exception message
    instead.

    Parameters
    ----------
    msg : ForwardMsg
        The message to serialize

    Returns
    -------
    str
        The serialized byte string to send

    """
    msg_str = msg.SerializeToString()

    if len(msg_str) > MESSAGE_SIZE_LIMIT:
        _convert_msg_to_exception_msg(msg, RuntimeError('Data too large'))
        msg_str = msg.SerializeToString()

    return msg_str


def _convert_msg_to_exception_msg(msg, e):
    import streamlit.elements.exception_proto as exception_proto

    delta_id = msg.delta.id
    msg.Clear()
    msg.delta.id = delta_id

    exception_proto.marshall(msg.delta.new_element.exception, e)


def is_url_from_allowed_origins(url):
    """Return True if URL is from allowed origins (for CORS purpose).

    Allowed origins:
    1. localhost
    2. The internal and external IP addresses of the machine where this
       function was called from.
    3. The cloud storage domain configured in `s3.bucket`.

    If `server.enableCORS` is False, this allows all origins.

    Parameters
    ----------
    url : str
        The URL to check

    Returns
    -------
    bool
        True if URL is accepted. False otherwise.

    """
    if not config.get_option('server.enableCORS'):
        # Allow everything when CORS is disabled.
        return True

    hostname = util.get_hostname(url)

    allowed_domains = [
        # Check localhost first.
        'localhost',
        '0.0.0.0',
        '127.0.0.1',
        # Try to avoid making unecessary HTTP requests by checking if the user
        # manually specified a server address.
        _get_server_address_if_manually_set,
        _get_s3_url_host_if_manually_set,
        # Then try the options that depend on HTTP requests or opening sockets.
        util.get_internal_ip,
        util.get_external_ip,
        lambda: config.get_option('s3.bucket'),
    ]

    for allowed_domain in allowed_domains:
        if util.is_function(allowed_domain):
            allowed_domain = allowed_domain()

        if allowed_domain is None:
            continue

        if hostname == allowed_domain:
            return True

    return False


def _get_server_address_if_manually_set():
    if config.is_manually_set('browser.serverAddress'):
        return util.get_hostname(config.get_option('browser.serverAddress'))


def _get_s3_url_host_if_manually_set():
    if config.is_manually_set('s3.url'):
        return util.get_hostname(config.get_option('s3.url'))