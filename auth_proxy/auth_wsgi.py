import auth_proxy
import local_settings
import os
import sys

from logging_settings import get_logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings


logger = get_logger()

application = auth_proxy.AuthProxy('127.0.0.1', 11211, local_settings.CONF_DIR,
    logger)

