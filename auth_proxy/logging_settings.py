import logging
import logging.handlers
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../local')
import local_settings

def get_logger():

    logger = logging.getLogger('tukey-auth')

    logger.setLevel(local_settings.LOG_LEVEL)
    
    formatter = logging.Formatter(local_settings.LOG_FORMAT)
    
    log_file_name = local_settings.LOG_DIR + 'tukey-auth.log'
    
    logFile = logging.handlers.WatchedFileHandler(log_file_name)
    logFile.setFormatter(formatter)
    
    logger.addHandler(logFile)

    return logger

