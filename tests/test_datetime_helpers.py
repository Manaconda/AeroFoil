import datetime
import unittest

from app.db import utc_now


class DateTimeHelperTests(unittest.TestCase):
    def test_utc_now_returns_naive_utc_datetime(self):
        before = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        value = utc_now()
        after = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

        self.assertIsNone(value.tzinfo)
        self.assertGreaterEqual(value, before)
        self.assertLessEqual(value, after)


if __name__ == '__main__':
    unittest.main()
