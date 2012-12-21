import local_settings
import logging
import logging.handlers
import tukeyServer

log_file_name = local_settings.LOG_DIR + 'tukey-api.log'

logger = logging.getLogger('tukey-api')

formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

logFile = logging.handlers.WatchedFileHandler('/var/log/tukey/tukey-api.log')
#logFile = logging.handlers.WatchedFileHandler('/dev/null')
logFile.setFormatter(formatter)

logger.addHandler(logFile)
logger.setLevel(logging.DEBUG)

application = tukeyServer.OpenStackApiProxy(8774, '127.0.0.1', 11211, logger)
