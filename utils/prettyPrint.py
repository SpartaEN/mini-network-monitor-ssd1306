import time


def currentDate():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def speed(speed):
    ''' speed in bps '''
    if speed == 'TBD':
        return speed
    if speed >= 10 ** 9:
        return '{} Gbps'.format(round(speed / 10 ** 9, 2))
    elif speed >= 10 ** 6:
        return '{} Mbps'.format(round(speed / 10 ** 6, 2))
    elif speed >= 10 ** 3:
        return '{} Kbps'.format(round(speed / 10 ** 3, 2))
    else:
        return '{} bps'.format(round(speed, 2))
