import snoohelper.utils as utils
import snoohelper.utils.exceptions
import snoohelper.utils.slack
import time


class RequestsHandler:
    """
    Handles Slack HTTP requests for buttons and slash commands
    """
    def __init__(self, teams_controller):
        """
        Construct RequestsHandler instance

        :param teams_controller: an instance of SlackTeamsController that contains the SlackTeams
        """
        self.teams_controller = teams_controller
        self.teams = teams_controller.teams

    def handle_command(self, slack_request):
        """
        Process a Slack slash command HTTP request, returns a response

        :param slack_request: SlackRequest object representing the Slack HTTP request
        :return: SlackResponse object representing a JSON-encoded response
        """

        response = utils.slack.SlackResponse("Processing your request... please allow a few seconds.")
        try:
            user = slack_request.command_args[0]
        except IndexError:
            user = None
        team = self.teams_controller.lookup_team_by_id(slack_request.team_id)
        if team is None:
            response = utils.slack.SlackResponse()
            response.add_attachment(text="Error: looks like your team's bot isn't running.", color='danger')
            return response

        if slack_request.command == '/user':
            team.bot.quick_user_summary(user=user, request=slack_request)
        elif slack_request.command == '/botban' and "botbans" in team.modules:
            try:
                response = team.bot.botban(user=user, author=slack_request.user)
            except utils.exceptions.UserAlreadyBotbanned:
                response = utils.slack.SlackResponse()
                response.add_attachment(text="Error: user already botbanned.", color='danger')

        elif slack_request.command == '/modmail' and "sendmodmail" in team.modules:
            team.bot.message_modmail(' '.join(slack_request.command_args), slack_request.user, slack_request)

        elif slack_request.command == '/restartbot':
            response = utils.slack.SlackResponse("Attempting to restart bot.")
            self.teams[team.team_name].bot.halt = True
            self.teams_controller.add_bot(team.team_name)

        elif slack_request.command == '/importbotbans' and "botbans" in team.modules:
            team.bot.import_botbans(slack_request.text, slack_request)
        elif slack_request.command == '/exportbotbans' and "botbans" in team.modules:
            response = team.bot.export_botbans()

        elif slack_request.command == "/filter" and "filters" in team.modules:
            expires = int(slack_request.command_args[0])
            if isinstance(expires, int):
                expires = (expires * 86400) + time.time()
                filter_string = ' '.join(slack_request.command_args[1:])
                team.bot.add_filter(filter_string, expires=expires, use_regex=False)
                response = utils.slack.SlackResponse("Filter created successfully.")
            else:
                response = utils.slack.SlackResponse()
                response.add_attachment(text="Error: first argument must be expiry time in days", color='danger')

        elif slack_request.command == "/regexfilter" and "filters" in team.modules:
            expires = int(slack_request.command_args[0])
            if isinstance(expires, int):
                expires = (expires * 86400) + time.time()
                filter_string = ' '.join(slack_request.command_args[1:])
                team.bot.add_filter(filter_string, expires=expires, use_regex=True)
                response = utils.slack.SlackResponse("Filter created successfully.")
            else:
                response = utils.slack.SlackResponse()
                response.add_attachment(text="Error: first argument must be expiry time in days", color='danger')

        elif slack_request.command == "/lockin":
            hours = int(slack_request.command_args[0])
            submission_id = slack_request.command_args[1]
            team.bot.add_timed_submission(submission_id, "lock", hours)

        elif slack_request.command == "/unlockin":
            hours = int(slack_request.command_args[0])
            submission_id = slack_request.command_args[1]
            team.bot.add_timed_submission(submission_id, "unlock", hours)

        elif slack_request.command == "/approvein":
            hours = int(slack_request.command_args[0])
            submission_id = slack_request.command_args[1]
            team.bot.add_timed_submission(submission_id, "approve", hours)

        elif slack_request.command == "/removereplies":
            comment_id = slack_request.command_args[0]
            team.bot.add_watched_comment(comment_id)

        elif slack_request.command == "/inspectban":
            user = slack_request.command_args[0]
            team.bot.inspect_ban(user, slack_request)

        else:
            response = utils.slack.SlackResponse()
            response.add_attachment(text="Command not available. Module has not been activated for this subreddit",
                                    color='danger')

        return response

    def handle_button(self, slack_request):
        """
        Process a Slack button HTTP request, returns a response

        :param slack_request: SlackRequest object representing the Slack HTTP request
        :return: SlackResponse object representing a JSON-encoded response
        """
        button_pressed = slack_request.actions[0]['value'].split('_')[0]
        args = slack_request.actions[0]['value'].split('_')[1:]
        team = self.teams_controller.lookup_team_by_id(slack_request.team_id)
        if team is None:
            response = utils.slack.SlackResponse()
            response.add_attachment(text="Error: looks like your team's bot isn't running.", color='danger')
            return response

        if button_pressed == "summary":
            limit = int(slack_request.actions[0]['value'].split('_')[1])
            target_user = '_'.join(slack_request.actions[0]['value'].split('_')[2:])
            original_message = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                      footer="Summary (%s) requested." % args[0])
            original_message.set_replace_original(True)
            response = original_message
            team.bot.expanded_user_summary(request=slack_request, limit=limit, username=target_user)
        elif button_pressed == "track":
            target_user = '_'.join(slack_request.actions[0]['value'].split('_')[1:])
            try:
                team.bot.track_user(user=target_user)
                new_button = utils.slack.SlackButton("Untrack", "untrack_" + target_user)
                replace_buttons = {'Track': new_button}

                response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                             footer="Tracking user.",
                                                                             change_buttons=replace_buttons)
            except utils.exceptions.UserAlreadyTracked:
                response = utils.slack.SlackResponse()
                response.add_attachment(text='Error: user is not being tracked', color='danger')

        elif button_pressed == "untrack":
            target_user = '_'.join(slack_request.actions[0]['value'].split('_')[1:])
            try:
                team.bot.untrack_user(user=target_user)
                new_button = utils.slack.SlackButton("Track", "track_" + target_user)
                replace_buttons = {'Untrack': new_button}

                response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                             footer="User untracked.",
                                                                             change_buttons=replace_buttons)
            except utils.exceptions.UserAlreadyUntracked:
                response = utils.slack.SlackResponse()
                response.add_attachment(text='Error: user is not being tracked', color='danger')

        elif button_pressed == "botban":
            target_user = '_'.join(slack_request.actions[0]['value'].split('_')[1:])

            try:
                team.bot.botban(user=target_user, author=slack_request.user)
                new_button = utils.slack.SlackButton("Unbotban", "unbotban_" + target_user, style='danger')
                replace_buttons = {'Botban': new_button}

                response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                             footer="User botbanned.",
                                                                             change_buttons=replace_buttons)
            except utils.exceptions.UserAlreadyBotbanned:
                response = utils.slack.SlackResponse()
                response.add_attachment(text='Error: user is already botbanned.', color='danger')

        elif button_pressed == "unbotban":
            target_user = '_'.join(slack_request.actions[0]['value'].split('_')[1:])

            try:
                team.bot.unbotban(user=target_user, author=slack_request.user)
                new_button = utils.slack.SlackButton("Botban", "botban_" + target_user, style='danger')
                replace_buttons = {'Unbotban': new_button}

                response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                             footer="User unbotbanned.",
                                                                             change_buttons=replace_buttons)
            except utils.exceptions.UserAlreadyUnbotbanned:
                response = utils.slack.SlackResponse()
                response.add_attachment(text='Error: user is not botbanned.', color='danger')

        elif button_pressed == "verify":
            original_message = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                                      delete_buttons=['Verify'],
                                                                      footer="Verified by @" + slack_request.user)
            response = original_message

        elif button_pressed == 'mutewarnings':
            target_user = args[0]
            team.bot.mute_user_warnings(user=target_user)
            new_button = utils.slack.SlackButton("Unmute user's warnings", "unmutewarnings_" + target_user,
                                                 style='danger')
            replace_buttons = {"Mute user's warnings": new_button}

            response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                              footer="User's warnings muted.",
                                                              change_buttons=replace_buttons)

        elif button_pressed == 'unmutewarnings':
            target_user = args[0]
            team.bot.mute_user_warnings(user=target_user)
            new_button = utils.slack.SlackButton("Mute user's warnings", "mutewarnings_" + target_user,
                                                 style='danger')
            replace_buttons = {"Unmute user's warnings": new_button}

            response = utils.slack.slackresponse_from_message(slack_request.original_message,
                                                              footer="User's warnings unmuted.",
                                                              change_buttons=replace_buttons)

        else:
            response = utils.slack.SlackResponse("Button not functional.")

        return response
