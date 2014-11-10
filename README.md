Dropouts is a script that automatically finds the most significant dimensions that differentiate users who did and did not convert to a particular Google Analytics goal.

### Pre-requisites

To run Dropouts, you need to do the following:

- Set up [goals](https://support.google.com/analytics/answer/1032415?hl=en-GB) on your Google Analytics account for the outcomes you care about.
- Create a row in `goals.csv` for each goal you want to analyse.

Your goals.csv file should contain the following columns:

- service_name: The name of your goal (this can be anything you want)
- service_id: Your Google Analytics ID. Go to Google Analytics, select your property and click Admin. In the third column ("View") there's a link to "View Settings'. In there you'll see a "View ID". This is the number you want.
- goal_id: The ID of your goal.
- goal_has_funnel: TRUE if your goal has a funnel (specified start and end page), FALSE if it does not.

### Run the script

Install the requirements as follows:

    virtualenv ve
    source ve/bin/activate
    pip install -r requirements.txt

Make sure you have downloaded a `client_secrets.json` file as specified by [gapy](https://github.com/alphagov/gapy).

Then run the file:

    python dropout.py -f [GOALS_FILE] -s [PATH_TO_CLIENT_SECRETS]

- `-f` is your goals file
- `-s` is the path to the `client_secrets.json` file that you downloaded when setting up gapy.

### Running tests

There are some rudimentary tests, you can run them with:

`nosetests`

### What Dropouts does

It will automatically segment your users into those that completed the goal and those that did not. It will then identify various dimensions of each segment, such as OS usage, browser usage.

Finally, it will run chi-squared tests to find the most statistically significant characteristics of the users who did not convert. It will print the results in order of significance.

You can then use this information to investigate what might be stopping your users from converting, and take action accordingly.