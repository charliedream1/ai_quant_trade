# encoding=utf-8
import logging
import logging.config
import os
import sys
import time
import traceback
import datetime


def init_log(name='root'):
    path = os.path.dirname(__file__)

    config_file = path + os.sep + 'logger.conf'
    log_path = os.path.join(os.path.abspath(__file__ + ('/..' * 3)), 'zz_logs')
    if not os.path.exists(log_path):
        os.makedirs(log_path)

    log_path = os.path.join(log_path, str(datetime.datetime.now().date()) + '.log')

    if os.path.isfile(config_file) is False:
        raise Exception("Config file {} not found".format(config_file))

    datalines = list()
    with open(config_file, 'r') as f:
        for data in f.readlines():
            if '$path' in data:
                data = data.replace('$path', log_path)
            datalines.append(data)
    f = open(config_file + '_bak', 'w')
    f.writelines(datalines)
    f.close()

    del datalines

    logging.config.fileConfig(config_file + '_bak')

    # os.remove(config_file + '_bak')

    return logging.getLogger(name)


# decorator print log
def addlog(name=''):
    begin = time.time()

    def _addlog(func):
        def wapper(*args, **kwargs):
            data = None
            begin1 = time.time()
            try:
                s = traceback.extract_stack()
                file = s[-2][0]
                __project_name = os.path.abspath(__file__ + ('/..' * 3))
                file_name = file[file.find(__project_name) + len(__project_name) + 1:file.rfind(r'.')]
                func_descrip = (file_name + '.' + func.__name__) if name == '' else name

                log.info('Start Execute：%s ...' % func_descrip)
                data = func(*args, **kwargs)

                inner_secs = time.time() - begin1

                log.info('Complete：%s , Time Consume: %s, Total Time: %s ' % (func_descrip,
                                                         time_str(inner_secs), time_str(time.time() - begin)))

            except Exception as e:
                # traceback.print_exc()
                log.exception('Failure Calling Time Consume:%s, Total Time:%s, Err Message:%s', time_str(time.time() - begin1),
                              time_str(time.time() - begin), e)
                # traceback.print_exc(file=open(log_file, 'a'))
                sys.exit(0)

            return data

        return wapper

    return _addlog


def time_str(second):
    return ('%.2f sec' % second) if second < 60 else ('%.2f min' % (second / 60.0))


log = init_log()


# example
@addlog()
def log_test1():
    time.sleep(1)


@addlog(name='test2')
def log_test2():
    time.sleep(1)
    log_test1()
    time.sleep(2)
    raise ValueError('A very specific bad thing happened.')


if __name__ == "__main__":
    col = 'aaaa'
    missing_rate = 0.26587

    log.info('%s has missing rate as %f' % (col, missing_rate))
    # log_test2()
    #
    # __project_name = os.path.abspath(__file__ + ('/..' * 3))
    # print(__project_name)

    log.debug('debug')

    log.info('test  -   debug')

    log.warning('warining')
