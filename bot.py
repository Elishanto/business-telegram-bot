import os
import feedparser

import pytz
import datetime

from bs4 import BeautifulSoup
from telegram.ext import Updater
from telegram import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton

SOURCES = [
    'https://vkrss.com/{token}/proektoria', 'https://vkrss.com/{token}/vcru',
    'https://vkrss.com/{token}/asi_ru', 'https://vkrss.com/{token}/incrussiamedia',
    'https://vkrss.com/{token}/lift2future', 'https://vkrss.com/{token}/iri.center',
    'https://vkrss.com/{token}/molodost_bz', 'https://vkrss.com/{token}/preactum',
    'https://vkrss.com/{token}/ayazshabutdinov', 'https://vkrss.com/{token}/innovations.itmo',
    'https://vkrss.com/{token}/rusbase_family', 'https://vkrss.com/{token}/imcup',
    'https://vkrss.com/{token}/molpred29', 'https://vkrss.com/{token}/friifond',
    'https://vkrss.com/{token}/rybakovfond', 'https://vkrss.com/{token}/youngbusiness'
]
UTC = pytz.UTC
LAST_TIME = datetime.datetime.now().astimezone(UTC)
TEMPLATE = '<b>{feed_title}</b> on <i>{published}</i>{summary}'


def extract_summary(summary, url):
    soup = BeautifulSoup(summary, 'lxml')

    for br in soup.find_all('br'):
        br.replace_with('\n')
    for a in soup.find_all('a'):
        if a['href'].startswith('https://vk.com/feed') or a['href'] == url:
            a.replace_with('')
        else:
            a.replace_with('<a href="{}">{}</a>'.format(a['href'], a['href']))

    text = soup.text

    return ('\n\n' + text[:3500] + ('...' if len(text) > 3500 else '')) if soup.text else ''


def extract_images(summary):
    soup = BeautifulSoup(summary, 'lxml')

    return [x['src'] for x in soup.find_all('img')]


def format_item(item):
    item['published'] = item['published'].strftime('%d %a at %I:%M %p')
    url = item['url']

    to_return = {
        'text': TEMPLATE.format(**item),
        'url': url
    }

    if item['images']:
        to_return['media'] = [InputMediaPhoto(x) for x in item['images']]

    to_return['disable_web_page_preview'] = bool(item['summary'] == '')

    return to_return if to_return['text'] or to_return['media'] else None


def send_news(bot, job):
    global LAST_TIME
    news = []

    for source in SOURCES:
        feed = feedparser.parse(source.format(token=os.environ.get('VKRSS')))
        entries = [{
            'feed_title': x['title'],
            'summary': extract_summary(x['summary'], x['link']),
            'images': extract_images(x['summary']),
            'url': x['link'],
            'published': datetime.datetime.strptime(x['published'], '%a, %d %b %Y %X %z').astimezone(UTC)
        } for x in feed['entries']]
        entries = [x for x in entries]
        news.extend(entries)

    news = sorted(
        filter(
            lambda x: x['published'] > LAST_TIME,
            news
        ),
        key=lambda x: x['published']
    )
    LAST_TIME = datetime.datetime.now().astimezone(UTC)

    for item in news:
        formatted_item = format_item(item)
        if not formatted_item:
            continue
        bot.send_message(
            chat_id='@businesssubs',
            text=formatted_item['text'], parse_mode='HTML',
            disable_web_page_preview=formatted_item['disable_web_page_preview'],
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('VK', url=formatted_item['url'])]])
        )
        if 'media' in formatted_item:
            bot.send_media_group(
                chat_id='@businesssubs',
                media=formatted_item['media'],
                timeout=60
            )


def main():
    updater = Updater(os.environ.get('TOKEN'))
    job_queue = updater.job_queue
    job_queue.run_repeating(send_news, interval=60 / 7 * 60, first=0)
    job_queue.start()


if __name__ == '__main__':
    main()
