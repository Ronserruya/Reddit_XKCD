import re

import requests
from bs4 import BeautifulSoup as soup
from bs4.element import NavigableString
import praw
from prawcore.exceptions import Forbidden

import config

COMMENT_BODY = "{}  \n" \
               "[Image Link]({})  \n" \
               "Title Text: {}  \n\n" \
               "Transcript:  \n\n" \
               "{}  \n\n" \
               "^[Explanation]({})  \n" \
               "______________________________________\n" \
               "^(I am a bot :D) ^[xkcd](https://xkcd.com)|" \
               "[Code](https://github.com/ronserruya/Reddit_XKCD)|" \
               "[Contact](https://www.reddit.com/message/compose/?to={})"


def bot_login():
    # Login with praw
    print("Logging in...")
    reddit = praw.Reddit(username=config.username,
                    password=config.password,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    user_agent="XKCD Reddit bot")
    print("Logged in!")
    return reddit


def get_HTML(comic_number):
    # Get the html from the explainxkcd page
    response = requests.get('http://www.explainxkcd.com/wiki/index.php/{}'.format(comic_number))
    response.raise_for_status()

    return response.content.decode()


def get_transcript(page):
    transcript_header = page.find(id='Transcript').parent
    next = transcript_header.next_sibling
    transcript = ''

    # Keep going until you are not in the transcript block anymore
    while next.name not in ['h2','h1','span']:
        if isinstance(next, NavigableString):
            transcript += '\n'
        else:
            transcript += next.get_text()
        next = next.next_sibling
    # Fix for reddit markdown
    return transcript.replace('\n', '  \n')


def get_image_link(title):
    # Get image from xkcd.com
    title_text = title.split(': ')[-1]
    return 'https://imgs.xkcd.com/comics/{}.png'.format(title_text.replace(' ', '_').lower())


def get_title(page):
    # Get the number + title of the comic
    return page.find(id='firstHeading').getText()


def get_explanation_url(comic_number):
    # Get a link to the comic explanation
    return 'http://www.explainxkcd.com/wiki/index.php/{}#Explanation'.format(comic_number)


def get_title_text(page):
    title_text_header = page.find(text='Title text:')
    return str(title_text_header.next_element)


def report_exception(reddit, comment, exception):
    # Send a the exception to me in a PM
    try:
        print(exception)
        error_msg = '{} Error report:  \n\n' \
                   'Comment: {}  \n\n' \
                   'Error: {}'.format(config.username,comment.permalink,exception)

        reddit.redditor(config.developer).message('{} Error report'.format(config.username),error_msg)
    except Exception as e:
        print(e)
        quit(1)


def report_shutdown(reddit):
    # Report shutting down
    try:
        error_msg = '{} Error report:  \n\n' \
                   'Shutting down'.format(config.username)

        reddit.redditor(config.developer).message('{} Error report'.format(config.username),error_msg)
    except Exception as e:
        print(e)
        quit(1)


def main():
    current_comment = None
    errors = 0
    reddit = bot_login()
    while True:
        try:
            # Get all comments on /r/all , skipping comments before the bot stated running
            for comment in reddit.subreddit('all').stream.comments(skip_existing=True):
                # Save the comment for the exception scope
                current_comment = comment

                if 'xkcd' in comment.subreddit_name_prefixed:
                    # this subs have their own bots
                    continue
                if 'i am a bot' in comment.body.lower() or "i'm a bot" in comment.body.lower():
                    # Dont reply to self or bots
                    continue
                # Find out if its referencing an xkcd
                comic_number = re.findall('(?<!what-if.)xkcd\.com\/(\d*).*',comment.body)
                if not comic_number or comic_number[0] == '':
                    continue

                html = get_HTML(comic_number[0])
                page = soup(html,'html5lib')
                title = get_title(page)
                image = get_image_link(title)
                transcript = get_transcript(page)
                title_text = get_title_text(page)
                explanation_url = get_explanation_url(comic_number[0])

                reply = COMMENT_BODY.format(title, image, title_text, transcript, explanation_url, config.developer)
                try:
                    comment.reply(reply)
                except Forbidden:
                    # banned :(
                    continue
                print('Replied to comment {}'.format(comment.permalink))
        except Exception as e:
            report_exception(reddit,current_comment,e)
            errors += 1

            # Shut down if i got 10 errors
            if errors >= 10:
                report_shutdown(reddit)
                quit(1)

if __name__ == '__main__':
    main()
