"""Nose tests for dropout class"""
from dropout import Dropout
import gapy
import nose


class TestDropout:

    def setUp(self):
        self.d = Dropout()
        self.raw = {}
        self.raw['results'] = {'completed': [[u'desktop', u'14452'],
                                             [u'mobile', u'4073'],
                                             [u'tablet', u'4287']],
                               'not_completed': [[u'desktop', u'30864'],
                                                 [u'mobile', u'11439'],
                                                 [u'tablet', u'9887']]}
        self.processed = {}
        self.processed['results'] = {'completed': {'desktop': 14452,
                                                   'mobile': 4073,
                                                   'tablet': 4287},
                                     'not_completed': {'desktop': 30864,
                                                       'mobile': 11439,
                                                       'tablet': 9887}}

    def test_convert_data_to_dict(self):
        input = [[u'Amazon Silk', u'193'],
                 [u'Android Browser', u'1361'],
                 [u'BlackBerry', u'116']]
        expected = {
            'Amazon Silk': 193,
            'Android Browser': 1361,
            'BlackBerry': 116
        }
        results = self.d.convert_data_to_dict(input)
        assert results == expected

    def test_get_unique_keys(self):
        '''
        Get the unique keys across both sets of results.
        '''
        del self.processed['results']['completed']['mobile']
        expected = [u'desktop', u'mobile', u'tablet']
        results = self.d.get_unique_keys(self.processed)
        assert results == expected

    def test_remove_missing_data(self):
        '''
        Remove data with missing or low values.
        '''
        self.processed['results']['completed']['mobile'] = 0
        self.processed['results']['not_completed']['wristwatch'] = 0
        expected = {'completed': {'tablet': 4287, 'desktop': 14452},
                    'not_completed': {'tablet': 9887, 'desktop': 30864}}
        results = self.d.remove_missing_data(self.processed)
        assert results == expected
