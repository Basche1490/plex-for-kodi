# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import datetime
import json
# noinspection PyUnresolvedReferences
from lib.kodi_util import (xbmc, xbmcgui, xbmcaddon, IPCTimeoutException, waitForGPEmpty,
                           setGlobalProperty, getGlobalProperty, KODI_VERSION_MAJOR, FROM_KODI_REPOSITORY)


ADDON = xbmcaddon.Addon()


def log(msg, level=xbmc.LOGINFO, realm="Updater"):
    xbmc.log('script.plexmod/{}: {}'.format(realm, msg), level)


def main():
    if getGlobalProperty('service.started'):
        # Prevent add-on updates from starting a new version of the addon
        return

    log('Started', realm="Service")
    setGlobalProperty('service.started', '1', wait=True)

    if ADDON.getSetting('kiosk.mode') == 'true':
        xbmc.log('script.plexmod: Starting from service (Kiosk Mode)', xbmc.LOGINFO)
        delay = ADDON.getSetting('kiosk.delay') or "0"
        xbmc.executebuiltin('RunScript(script.plexmod,1{})'.format(",{}".format(delay) if delay != "0" else ""))


    # update checker and auto update logic
    if not FROM_KODI_REPOSITORY:
        from lib.updater import get_updater, ServiceMonitor, UpdateException, UpdaterSkipException

        # fixme: store last update check mode and react accordingly (mode change)
        last_check_mode = mode = "beta"  # get
        updater = get_updater(mode)(branch='develop_kodi21' if KODI_VERSION_MAJOR > 18 else 'addon_kodi18')

        def should_check():
            return not any([
                xbmc.Player().isPlaying(),
                getGlobalProperty('running') != '1',
                getGlobalProperty('started') != '1',
                getGlobalProperty('is_active') != '1',
                getGlobalProperty('waiting_for_start')
            ])

        def disable_enable_addon():
            log("Toggling")
            try:
                xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
                                         'params': {'addonid': 'script.plexmod', 'enabled': False}}))
                xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.SetAddonEnabled',
                                         'params': {'addonid': 'script.plexmod', 'enabled': True}}))
            except:
                raise

        monitor = ServiceMonitor()
        last_update_check = datetime.datetime.now()  # get
        check_interval = datetime.timedelta(hours=4)  # 4h, get
        check_immediate = True  # get

        while not getGlobalProperty('running') and not monitor.abortRequested():
            if monitor.waitForAbort(1):
                return

        while not monitor.abortRequested():
            now = datetime.datetime.now()

            if (last_update_check + check_interval <= now or check_immediate) and not monitor.sleeping:
                if should_check():
                    try:
                        if check_immediate:
                            check_immediate = False

                        log('Checking for updates')
                        update_version = updater.check('0.8.0-alpha3')#ADDON.getAddonInfo('version'))

                        last_update_check = datetime.datetime.now()

                        if update_version:
                            # notify user in main app and wait for response
                            setGlobalProperty('update_available', update_version, wait=True)

                            try:
                                resp = getGlobalProperty('update_response', consume=True, wait=True)
                                log("RESP: %s" % resp)
                            except IPCTimeoutException:
                                # timed out
                                raise UpdateException('No user response')

                            log("User response: {}".format(resp))

                            if resp == "commence":
                                # wait for UI to close
                                try:
                                    waitForGPEmpty('running', timeout=200)
                                except IPCTimeoutException:
                                    raise UpdateException('Timeout waiting for UI to close')
                            else:
                                raise UpdaterSkipException()

                            pd = xbmcgui.DialogProgressBG()
                            pd.create("Update", message="Downloading")
                            had_already = os.path.exists(updater.archive_path)
                            if not had_already:
                                log("Update found: {}, downloading".format(update_version))
                                zip_loc = updater.download()

                                if zip_loc:
                                    log("Update zip downloaded to: {}".format(zip_loc))
                            else:
                                log("Update {} previously downloaded, using previous zip".format(update_version))

                            pd.update(25, message="Unpacking")

                            dir_loc = updater.unpack()

                            has_major_changes = updater.get_major_changes()

                            pd.update(50, message="Installing")

                            if dir_loc and updater.install():
                                pd.update(75, message="Cleaning up")
                                updater.cleanup()
                                pd.update(100, message="Preparing to start")
                                xbmc.sleep(1000)

                                do_start = True
                                if has_major_changes:
                                    kw = {}
                                    if KODI_VERSION_MAJOR >= 20:
                                        kw = {'defaultbutton': xbmcgui.DLG_YESNO_YES_BTN}
                                    do_start = xbmcgui.Dialog().yesno(
                                        "Major changes",
                                        "Start anyway?",
                                        nolabel="No",
                                        yeslabel="Yes",
                                        **kw
                                    )

                                xbmc.executebuiltin('UpdateLocalAddons', True)
                                xbmc.executebuiltin('ActivateWindow(Home)', True)
                                pd.close()
                                del pd
                                #disable_enable_addon()

                                if do_start:
                                    xbmc.executebuiltin('RunScript(script.plexmod)')

                    except UpdateException as e:
                        log(e, xbmc.LOGWARNING)

                    except UpdaterSkipException:
                        log("Update skipped")

                    finally:
                        setGlobalProperty('update_available', '')
                        setGlobalProperty('update_response', '')

                else:
                    xbmc.log('script.plexmod: Delaying update check', xbmc.LOGINFO)

            if monitor.waitForAbort(10):
                break

if __name__ == '__main__':
    main()
    log("Exited", realm="Service")
