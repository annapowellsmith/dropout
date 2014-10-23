# Student finance,76885282,15,TRUE,
import argparse
import copy
import csv
import sys
import gapy.client
from datetime import datetime, timedelta
from operator import itemgetter
from pprint import pprint
from pandas import DataFrame
from scipy import stats


class Dropout:
    '''
    Fetches data on converted and non-converted segments from the Google
    Analytics API. Compares the characteristics of those segments for
    several pre-set dimensions: browser, operating system, etc.
    Runs a chi-squared test to find significant dimensions.
    '''

    def fetch_data(self, dimension):
        '''
        Given a particular dimension (e.g. device type) fetches data for each
        segment split out by that dimension from the Analytics API.
        Then transforms GA's array-based data into a dictionary format.
        Returned data looks like this:
        {'not_completed': {u'mobile': 1077, u'tablet': 2637, u'desktop': 6403},
         'completed':     {u'mobile': 1391, u'tablet': 5314, u'desktop': 9112}}

        '''
        print '--------------- Fetching data for:', \
              dimension['description'], '---------------'

        results = {}

        segments = [
            {'id': 'completed',
             'segment': self.YES_SEGMENT},
            {'id': 'not_completed',
             'segment': self.NO_SEGMENT}
        ]

        # Collects data for the last 60 days of data by default.
        end_date = (datetime.today() - timedelta(days=1)).date()
        start_date = end_date - timedelta(days=60)

        # Get data from the API, using a dimension if required.
        for segment in segments:
            # NB: Could add samplingLevel=HIGHER_PRECISION if desired
            data = self.client.query.get(self.GA_ID,
                                         start_date,
                                         end_date,
                                         metrics=['ga:users'],
                                         dimensions=dimension['id'],
                                         segment=segment['segment'])

            # Warn about sampled data.
            if data.containsSampledData:
                print 'Based on %s samples from a population of %s' % \
                      (data.sampleSize, data.sampleSpace)

            if data.rows:
                results[segment['id']] = self.convert_data_to_dict(data.rows)
            else:
                results[segment['id']] = {}

        return results

    def convert_data_to_dict(self, data):
        '''
        Convert the raw data returned by GA into a dictionary.
        The results are usually an array of length 2: convert
        these into key and values.
        In cases where we've queried multiple dimensions, the result
        will be an array longer than 2. In this case, turn the
        all but the last element in the array into the key name.
        '''
        results_dict = {}
        for d in data:
            key_name = d[0]
            if len(d) > 2:
                for i in range(1, len(d)-1):
                    key_name += '_' + d[i]
            results_dict[key_name] = int(d[-1])
        return results_dict

    def get_unique_keys(self, dimension):
        '''
        Get the unique keys across both segments,
        and sort them alphabetically.
        '''
        keys = []
        for id in dimension['results']:
            temp_keys = [val for val in dimension['results'][id]]
            for t in temp_keys:
                keys.append(t)
        return sorted(list(set(keys)))

    def remove_missing_data(self, dimension):
        '''
        Delete any columns where the value in either segment is under 5.
        This is a requirement for the Pearson's chi-squared test.
        If the value of completed is under 5, print a warning - this is
        so we pick up on these categories even though they're not in the
        chi-squared results.
        NB: pandas can remove low values: df = df.ix[:, (df > 5).any(axis=0)]
        but it's more useful for us to do it manually.
        '''
        r = dimension['results']
        unique_keys = self.get_unique_keys(dimension)
        low_numbers = []

        for k in unique_keys:
            good_data_in_both_segments = True

            # Print a warning for cells with low completed values.
            if (k in r['not_completed']) and (r['not_completed'][k] > 10):
                if (k not in r['completed']) or (r['completed'][k] < 5):
                    vals = [k, r['not_completed'][k]]
                    if k in r['completed']:
                        vals.append(r['completed'][k])
                    else:
                        vals.append(0)
                    low_numbers.append(vals)

            for goal in r:
                if not(k in r[goal]) or r[goal][k] < 5:
                    good_data_in_both_segments = False
                    break

            if not good_data_in_both_segments:
                for goal in r:
                    if k in r[goal]:
                        del r[goal][k]

        low_numbers = sorted(low_numbers, key=itemgetter(1), reverse=True)
        for ln in low_numbers:
            warning = 'LOW COMPLETION RATE for %s: ' % ln[0]
            warning += '%s not completed, %s completed' % (ln[1], ln[2])
            print warning

        return r

    def get_chi_squared(self, results):
        '''
        Convert input data to a pandas data frame, run a chi-squared test
        and return the results.
        '''
        df = DataFrame(results).T.fillna(0)
        # print df
        chi2_values = stats.chi2_contingency(df)
        return chi2_values

    def print_dimension(self, dimension):
        '''
        Print results for a particular dimension in a useful fashion.
        Indexes results by dimension so we can print the results more
        meaningfully. Also calculates completion rates.
        In other words we change results from being indexed by segment:
        results = {'completed': {'desktop': 14452,
                                 'mobile': 4073 },
                   'not_completed': {'desktop': 30864,
                                     'mobile': 11439 }}
        To being indexed by dimension, and including completion rates:
        'pretty_results' = [ { 'id': 'desktop',
                                'values':  { 'completed': 44,
                                             'not_completed': 22,
                                             'completed_percent': 66.7,
                                             'not_completed_percent': 33.3 }},
                             { 'id': 'mobile', ... etc
        '''

        pretty_results = []

        # Pivot results by key, and calculate conversion rates.
        for k in self.get_unique_keys(dimension):
            vals = {}
            # Get raw values.
            for r in ['completed', 'not_completed']:
                results = dimension['results'][r]
                for res in results:
                    if res == k:
                        vals[r] = float(results[k])

            # Calculate percentages.
            # pprint(vals)
            vals['total'] = vals['completed'] + vals['not_completed']
            vals['percent_completed'] = (vals['completed']/vals['total']) * 100
            vals['percent_not_completed'] = (vals['not_completed'] /
                                             vals['total']) * 100
            pretty_result = {'id': k, 'values': vals}
            pretty_results.append(pretty_result)

        # Sort list by completion rate, then print.
        pretty_sorted = sorted(pretty_results,
                               key=lambda result:
                               (result['values']['percent_completed']),
                               reverse=True)
        for result in pretty_sorted:
            id = result['id']
            vals = result['values']
            if 'completed' in vals and 'not_completed' in vals:
                # TODO: Use this properly.
                significance_indicator = ''  # '** ' if vals['total'] else ''
                print '%susers in category "%s": %s of %s (%.1f%%) completed' % \
                    (significance_indicator, id, int(vals['completed']),
                     int(vals['total']),
                     vals['percent_completed'])
            else:
                print 'users in category "%s":' + \
                    ' No data for at least one category' % id
        print

    def print_significant_dimensions(self, dimensions):
        '''
        Filter for significant dimensions, sort by order of significance,
        and print nicely.
        '''
        # Filter for significant dimensions.
        filtered_dimensions = []
        non_significant_dimensions = []
        for dimension in dimensions:
            # pprint(dimension)
            if dimension['p'] < 0.05 and dimension['p'] is not None:
                filtered_dimensions.append(dimension)
            else:
                non_significant_dimensions.append(dimension)
        sorted_dimensions = sorted(filtered_dimensions, key=itemgetter('p'))

        # Print significant dimensions.
        print '--------------- RESULTS ---------------'
        print '%s significant dimensions found for completion in past 60 days.' % len(filtered_dimensions)
        print
        if len(filtered_dimensions) > 1:
            print 'In order of significance:'
            print
        for i, dimension in enumerate(sorted_dimensions):
            print '%s. %s (p-value %s)' % (i+1,
                                           dimension['description'],
                                           dimension['p'])
            d.print_dimension(dimension)
            print
        if non_significant_dimensions:
            print 'Non-significant dimensions:'
            print [nd['id'] for nd in non_significant_dimensions]

    def get_all_dimensions(self, GA_ID, GOAL_ID, SERVICE_NAME, HAS_FUNNEL,
                           SECRETS_PATH, dimensions):
        '''
        For a given service and goal, gets results for the given dimensions.
        Set up the segment expressions, and initialise the gapy client.
        Then for each dimension, fetch data, clean it and run a chi-squared
        test for significance. Print the results to the terminal.
        '''
        self.GA_ID = GA_ID
        self.GOAL_ID = GOAL_ID
        self.SECRETS_PATH = SECRETS_PATH
        self.YES_SEGMENT = 'users::condition::ga:goal%sCompletions>0' % GOAL_ID
        if HAS_FUNNEL:
            self.NO_SEGMENT = 'users::condition::ga:goal%sStarts>0;ga:goal%sCompletions==0' \
                % (GOAL_ID, GOAL_ID)
        else:
            self.NO_SEGMENT = 'users::condition::ga:goal%sCompletions==0' \
                % GOAL_ID

        self.client = gapy.client.from_secrets_file(
            '%s/client_secrets.json' % self.SECRETS_PATH,
            storage_path='%s/storage.db' % self.SECRETS_PATH)

        dimensions_copy = copy.deepcopy(dimensions)
        for dimension in dimensions_copy:
            if isinstance(dimension['id'], basestring):
                dimension['nice_id'] = dimension['id'].replace('ga:', '')
            else:
                dimension['nice_id'] = '_'.join(dimension['id'])
                dimension['nice_id'] = dimension['nice_id'].replace('ga:', '')
            # Fetch and clean data.
            dimension['results'] = d.fetch_data(dimension)
            dimension['results'] = d.remove_missing_data(dimension)
            # Run a chi-squared test.
            chi2, p, dof, expected = d.get_chi_squared(dimension['results'])
            dimension['chi2'] = chi2
            dimension['p'] = p

        return dimensions_copy


if __name__ == "__main__":

    # Configure arguments.
    overall_description = 'Find the characteristics of users who '
    overall_description += 'do not complete a Google Analytics goal'
    parser = argparse.ArgumentParser(description=overall_description)
    secrets = 'Path to your Google Analytics secrets file'
    services = 'Path to your services file'
    parser.add_argument('-s', '--secrets_path', help=secrets, required=True)
    parser.add_argument('-f', '--services_file', help=services, required=True)
    args = vars(parser.parse_args())
    SECRETS_PATH = args['secrets_path']
    SERVICES_FILE = args['services_file']
    dimensions = [
        {'id': 'ga:fullReferrer', 'description': 'Referrer'},
        {'id': 'ga:deviceCategory', 'description': 'Device category'},
        {'id': 'ga:browser', 'description': 'Browser'},
        {'id': 'ga:visitorType', 'description': 'Visitor type'},
        {'id': 'ga:socialNetwork', 'description': 'Social network referrer'},
        {'id': 'ga:country', 'description': 'Country'},
        {'id': 'ga:dayOfWeekName', 'description': 'Day of week'},
        {'id': 'ga:operatingSystem', 'description': 'Operating system'},
        {'id': ['ga:operatingSystem', 'ga:browser'],
                'description': 'OS and browser'},
        {'id': 'ga:mobileDeviceMarketingName', 'description': 'Mobile name'},
        {'id': 'ga:mobileInputSelector',
         'description': 'Mobile input selector'}
    ]

    # Fetch data for each service.
    d = Dropout()
    all_results = []
    try:
        services = csv.DictReader(open(SERVICES_FILE, 'rU'))
    except:
        print 'Failed to open services file'
        sys.exit()
    for s in services:
        result = {}
        print '================\nGetting data for %s' % s['service_name']
        result['service_id'] = s['service_id']
        result['service_name'] = s['service_name']
        result['goal_id'] = s['goal_id']
        result['dimensions'] = d.get_all_dimensions(s['service_id'],
                                                    s['goal_id'],
                                                    s['service_name'],
                                                    s['goal_has_funnel'],
                                                    SECRETS_PATH,
                                                    dimensions)
        d.print_significant_dimensions(result['dimensions'])
        all_results.append(result)

    # Write results for all services to CSV.
    header = ['aaa_service_name', 'aa_service_id', 'aa_goal_id']
    for r in all_results:
        for d in r['dimensions']:
            for k in d['results']['completed']:
                header.append('abs_%s_%s' % (d['nice_id'], k))
        for d in r['dimensions']:
            for k in d['results']['completed']:
                header.append('cr_%s_%s' % (d['nice_id'], k))
    writer = csv.DictWriter(open('summary.csv', 'w'),
                            fieldnames=sorted(set(header)))
    writer.writeheader()
    for r in all_results:
        row = {'aaa_service_name': r['service_name'],
               'aa_service_id': r['service_id'],
               'aa_goal_id': r['goal_id']}
        for d in r['dimensions']:
            for k in d['results']['completed']:
                key = '%s_%s' % (d['nice_id'], k)
                row['abs_%s' % key] = temp = d['results']['completed'][k] + \
                    d['results']['not_completed'][k]
                row['cr_%s' % key] = float(d['results']['completed'][k]) / \
                    float(temp)
        writer.writerow(row)
