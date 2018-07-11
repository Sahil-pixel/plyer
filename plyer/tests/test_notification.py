'''
TestNotification
================

Tested platforms:

* Windows
* Linux - notify-send, dbus
'''

import unittest
import sys
from mock import Mock, patch

from time import sleep
from os.path import dirname, abspath, join

from plyer.utils import platform
from plyer.tests.common import PlatformTest, platform_import


class MockedNotifySend(object):
    @staticmethod
    def whereis_exe(binary):
        return binary == 'notify-send'

    @staticmethod
    def call(args):
        assert len(args) >= 3
        assert TestNotification.data['title'] in args
        assert TestNotification.data['message'] in args

    @staticmethod
    def warn(msg):
        assert 'dbus package is not installed' in msg


class TestNotification(unittest.TestCase):
    data = {
        'title': 'title',
        'message': 'My Message\nis multiline',
        'app_name': 'Plyer Test',
        'app_icon': join(
            dirname(abspath(__file__)),
            'images', 'kivy32.ico'
        ),
        'timeout': 0.1
    }

    def show_notification(self, instance):
        instance.notify(**self.data)

    @PlatformTest('win')
    def test_notification_windows(self):
        import ctypes
        from ctypes import (
            WINFUNCTYPE, POINTER,
            create_unicode_buffer,
            c_bool, c_int
        )
        notif = platform_import(
            platform='win',
            module_name='notification'
        ).instance()
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetClassNameW = ctypes.windll.user32.GetClassNameW

        # loop over windows and get refs to
        # the opened plyer notifications
        clsnames = []

        def fetch_class(hwnd, lParam):
            buff = create_unicode_buffer(50)
            GetClassNameW(hwnd, buff, 50)

            if 'Plyer' in buff.value:
                clsnames.append(buff.value)

        # ensure it's not an empty facade
        self.assertIn('WindowsNotification', str(notif))

        # create enum function for EnumWindows
        EnumWindowsProc = WINFUNCTYPE(
            # returns
            c_bool,

            # input params: hwnd, lParam
            POINTER(c_int), POINTER(c_int)
        )

        for i in range(3):
            self.show_notification(notif)

            # the balloon needs some time to became visible in WinAPI
            sleep(0.01)

            # fetch window class names
            EnumWindows(
                # enum & params
                EnumWindowsProc(fetch_class), None
            )

            # 3 active balloons at the same time,
            # class_name is incremented - see WindowsBalloonTip
            self.assertEqual(len(clsnames), i + 1)
            self.assertIn('PlyerTaskbar' + str(i), clsnames)
            clsnames = []

    @PlatformTest('linux')
    def test_notification_dbus(self):
        notif = platform_import(
            platform='linux',
            module_name='notification'
        )
        self.assertIn('NotifyDbus', dir(notif))

        # (3) mocked Interface called from dbus
        interface = Mock()
        interface.side_effect = (interface, )

        # (2) mocked SessionBus called from dbus
        session_bus = Mock()
        session_bus.side_effect = (session_bus, )

        # (1) mocked dbus for import
        dbus = Mock(SessionBus=session_bus, Interface=interface)

        # inject the mocked module
        self.assertNotIn('dbus', sys.modules)
        sys.modules['dbus'] = dbus

        try:
            notif = notif.instance()
            self.assertIn('NotifyDbus', str(notif))

            # call notify()
            self.show_notification(notif)

            # check whether Mocks were called
            dbus.SessionBus.assert_called_once()

            session_bus.get_object.assert_called_once_with(
                'org.freedesktop.Notifications',
                '/org/freedesktop/Notifications'
            )

            interface.Notify.assert_called_once_with(
                TestNotification.data['app_name'],
                0,
                TestNotification.data['app_icon'],
                TestNotification.data['title'],
                TestNotification.data['message'],
                [], [],
                TestNotification.data['timeout'] * 1000
            )
        finally:
            del sys.modules['dbus']
        self.assertNotIn('dbus', sys.modules)

    @PlatformTest('linux')
    def test_notification_notifysend(self):
        notif = platform_import(
            platform='linux',
            module_name='notification',
            whereis_exe=MockedNotifySend.whereis_exe
        )
        self.assertIn('NotifySendNotification', dir(notif))
        with patch(target='warnings.warn', new=MockedNotifySend.warn):
            notif = notif.instance()
        self.assertIn('NotifySendNotification', str(notif))

        with patch(target='subprocess.call', new=MockedNotifySend.call):
            self.assertIsNone(self.show_notification(notif))


if __name__ == '__main__':
    unittest.main()
