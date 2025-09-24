# FINAL default.py - REMOVED the "future" library dependency as you suggested.

from __future__ import absolute_import
# << LINE REMOVED: from future import standard_library >>
# << LINE REMOVED: standard_library.install_aliases() >>

import os
import sys

# Append the script's library path to Python's system path
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

from kodiswift import Plugin
from lib.backgroundthread import BGThreader
from lib.player import PLAYER
from lib.windows.base import BaseWindow
from lib.util import T, get_setting, set_setting, get_global_setting, set_global_setting
import lib.util as util

plugin = Plugin(request=sys.argv[2], custom_log_prefix='script.plexmod.zidoo')

def run_addon(minimized=False):
    util.DEBUG_LOG('Addon start minimized=%s' % minimized)
    util.setGlobalProperty('script_running', 'True')
    monitor = util.Monitor()

    def main_loop(instance):
        from lib.windows.home import HomeWindow
        from lib.plex import get_all_client_info, get_server_info, connect_all
        from lib.windows.dialogs import Dialogs
        from lib.windows.login import LoginWindow

        connected, reason, account = connect_all()
        if not connected:
            if reason.lower() == 'login':
                w = LoginWindow.create()
                w.doModal()
                del w
                return main_loop(instance)

            Dialogs.ok(T(32000), reason)
            return

        BaseWindow.set_default_plex_object(get_server_info())
        util.setGlobalProperty('username', account.username)
        util.setGlobalProperty('friendly_name', plugin.addon.getAddonInfo('name'))
        util.setGlobalProperty('id', plugin.addon.getAddonInfo('id'))
        util.setGlobalProperty('version', plugin.addon.getAddonInfo('version'))

        # Main UI Loop
        window_stack = []
        clients = get_all_client_info()

        w = HomeWindow.create(data=(clients, window_stack), minimized=minimized)

        try:
            w.doModal()
        except Exception:
            util.ERROR()

        del w

    lockfile = os.path.join(util.xbmc.translatePath('special://temp/'), 'pm4k.lock')
    lock = util.SingleInstance(lockfile)
    if not lock:
        util.LOG('Main: script.plexmod.zidoo: Trying to reactivate minimized addon')
        util.xbmc.executebuiltin('NotifyAll(script.plexmod.zidoo, Other.RESTORE)')
        return

    try:
        main_loop(lock)
    finally:
        util.LOG('Main: script.plexmod.zidoo: Addon finished')
        util.setGlobalProperty('script_running', '')
        monitor.stop()
        BGThreader.stop()


@plugin.route('/')
def main_menu():
    util.set_home()
    if get_setting('service_run', 'False') == 'False':
        run_addon()


@plugin.route('/minimized')
def minimized_start():
    if get_setting('service_run', 'False') == 'False':
        set_global_setting('active_window', '')
        util.set_home()
        run_addon(minimized=True)


@plugin.route("/action/<action_string>")
def handle_action(action_string):
    """
    This is the main action handler for clicks from the home screen hubs.
    This fixes the 'Continue Watching' button.
    """
    util.LOG("PlexMod-Zidoo: default.py handle_action called with: %s" % action_string)

    list_item = util.get_list_item()
    if not list_item:
        util.LOG("PlexMod-Zidoo: Action handler called but no list item was focused.")
        return

    plex_object_str = list_item.get_property('plex_object')
    if not plex_object_str:
        util.LOG("PlexMod-Zidoo: Clicked item has no 'plex_object' property.")
        return

    from lib.plex import get_plex_object
    media_object = get_plex_object(plex_object_str)

    if not media_object:
        util.LOG("PlexMod-Zidoo: Could not deserialize the plex_object.")
        return

    if media_object.is_media:
        util.LOG("PlexMod-Zidoo: Identified playable media. Calling PLAYER.playVideo.")
        PLAYER.playVideo(media_object, resume=True)
    else:
        util.LOG("PlexMod-Zidoo: Item is not playable media, navigating...")
        util.navigate(media_object)


if __name__ == '__main__':
    try:
        plugin.run()
    except Exception as e:
        util.ERROR(e, notify=False)