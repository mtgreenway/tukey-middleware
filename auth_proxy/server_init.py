import logging
import logging.handlers

def init_server(app, host='127.0.0.1', port=8080, 
	logger_name=__name__, log_file=None):

    import optparse
    parser = optparse.OptionParser(
        usage='%prog --port=PORT --host=HOST'
        )
    parser.add_option(
        '-p', '--port', default=port,
        dest='port', type='int',
        help='Port to serve on (default %s)' % port)

    parser.add_option(
        '-i', '--host', default=host,
        dest='host', type='str',
        help='Host (default %s)' % host)

    parser.add_option(
        '-l', '--logger-name', default=logger_name,
        dest='logger', type='str',
        help='logger name (default %s)' % logger_name)

    parser.add_option(
        '-f', '--log-file', default=log_file,
        dest='log_file', type='str',
        help='log file (default %s)' % log_file)

    options, args = parser.parse_args()


    #logging settings 
    logger = logging.getLogger(options.logger)

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s %(filename)s:%(lineno)d')

    if options.log_file is None:
	logFile = logging.StreamHandler()
    else:
        logFile = logging.handlers.WatchedFileHandler(options.log_file)

    logFile.setLevel(logging.DEBUG)
    logFile.setFormatter(formatter)

    logger.addHandler(logFile)

    from wsgiref.simple_server import make_server
    httpd = make_server(options.host, options.port, app)
    print 'Serving on http://%s:%s' % (options.host, options.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print '^C'

