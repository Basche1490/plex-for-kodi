# coding=utf-8
from __future__ import absolute_import
import logging
import tempfile

from lib.logging import log
# noinspection PyUnresolvedReferences
from lib.kodi_util import translatePath, xbmc, setGlobalProperty, getGlobalProperty
from tendo_singleton import SingleInstance, SingleInstanceException


# tempfile's standard temp dirs won't work on specific OS's (android)
tempfile.tempdir = translatePath("special://temp/")


class KodiLogProxyHandler(logging.Handler):
    def emit(self, record):
        try:
            log(self.format(record))
        except:
            self.handleError(record)


# add custom logger for tendo.singleton, so we can capture its messages
logger = logging.getLogger("tendo.singleton")
logger.addHandler(KodiLogProxyHandler())
logger.setLevel(logging.DEBUG)


started = False
try:
    if getGlobalProperty('running') and not getGlobalProperty('is_active'):
        try:
            xbmc.executebuiltin('NotifyAll({0},{1},{2})'.format('script.plexmod', 'RESTORE', '{}'))
        except:
            log('Main: script.plex: Already running, couldn\'t reactivate other instance, exiting.')
    else:
        if not getGlobalProperty('started'):
            with SingleInstance("pm4k"):
                setGlobalProperty('started', '1')
                started = True
                from lib import main
                main.main()
        else:
            log('Main: script.plex: Already running, exiting')

except SingleInstanceException:
    pass

except SystemExit as e:
    if e.code not in (-1, 0):
        raise

finally:
    if started:
        setGlobalProperty('started', '')
