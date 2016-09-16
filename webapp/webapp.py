import os
import requests
from flask import Flask, request, Response, redirect, render_template, make_response
from flask_sslify import SSLify
import utils.utils as utils
from .requests_handler import RequestsHandler
from .form import SubredditSelectForm
import praw

SLACK_APP_ID = utils.get_token("SLACK_APP_ID", "credentials")
SLACK_APP_SECRET = utils.get_token("SLACK_APP_SECRET", "credentials")
SLACK_COMMANDS_TOKEN = utils.get_token("SLACK_COMMANDS_TOKEN", "credentials")
REDDIT_APP_ID = utils.get_token("REDDIT_APP_ID", "credentials")
REDDIT_APP_SECRET = utils.get_token("REDDIT_APP_SECRET", "credentials")
REDDIT_REDIRECT_URI = utils.get_token("REDDIT_REDIRECT_URI", "credentials")
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = '1'
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = '1'

app = Flask(__name__, template_folder='../webapp/templates')
app.config.from_object('config')
sslify = SSLify(app)
slack_teams_config = utils.SlackTeamsConfig('teams.ini')
handler = RequestsHandler(slack_teams_config)
master_r = praw.Reddit("windows:RedditSlacker2 0.1 by /u/santi871", handler=praw.handlers.MultiprocessHandler())
master_r.set_oauth_app_info(client_id=REDDIT_APP_ID, client_secret=REDDIT_APP_SECRET, redirect_uri=REDDIT_REDIRECT_URI)


@app.route("/slack/oauthcallback")
def slack_oauth_callback():
    data = {'client_id': SLACK_APP_ID, 'client_secret': SLACK_APP_SECRET, 'code': request.args.get('code')}
    response = requests.post('https://slack.com/api/oauth.access', params=data)
    response_json = response.json()

    try:
        slack_teams_config.add_team(response_json)
    except utils.TeamAlreadyExists:
        return "Error: Your team has already installed RedditSlacker2."

    url = master_r.get_authorize_url('uniqueKey', ['identity', 'mysubreddits', 'modposts', 'modlog', 'read'],
                                     refreshable=True)
    response = make_response(redirect(url, code=302))
    response.set_cookie('slack_team_name', response_json['team_name'])

    return response


@app.route('/reddit/oauthcallback', methods=['POST', 'GET'])
def reddit_oauth_callback():
    form = SubredditSelectForm()

    if request.method == 'GET':
        code = request.args.get('code', None)
        if code is not None:
            try:
                access_information = master_r.get_access_information(code)
                team_name = request.cookies.get('slack_team_name')
            except (KeyError, praw.errors.OAuthInvalidGrant, praw.errors.OAuthInvalidToken):
                return "There was an error processing your request, please try again."
            utils.set_team_access_credentials(team_name, access_information)
            moderated_subreddits = master_r.get_my_moderation()
            choices = [(subreddit.display_name, subreddit.display_name) for subreddit in moderated_subreddits]
            form.subreddit_select.choices = choices
            return render_template('subreddit_select.html', title='Select Subreddit', form=form)

    elif request.method == 'POST':
        subreddit = form.subreddit_select.data
        team_name = request.cookies.get('slack_team_name', None)

        if team_name is None:
            return "There was an error processing your request, please try again."
        slack_teams_config.set_subreddit(team_name, subreddit)
        master_r.clear_authentication()

        return "Successfully added Slack team and linked to subreddit. Enjoy!"


@app.route('/slack/commands', methods=['POST'])
def command():
    slack_request = utils.SlackRequest(request, SLACK_COMMANDS_TOKEN)
    if slack_request.is_valid:

        response = handler.handle_command(slack_request)

        return Response(response=response.get_json(), mimetype="application/json")

    else:
        return "Invalid request token."

'''

@app.route('/slack/action-endpoint', methods=['POST'])
def button_response():

    slack_request = utils.SlackRequest(request, SLACK_COMMANDS_TOKEN)
    if slack_request.is_valid:

        response = handler.button_response(slack_request)

        if response is None:
            return Response(status=200)

        return Response(response=response.get_json(), mimetype="application/json")

    else:
        return "Invalid request token."


@app.route('/redditslacker/status', methods=['GET'])
def check_status():
    return Response(), 200
'''