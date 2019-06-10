#!/usr/bin/env python3

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib import request
from urllib.error import HTTPError


ROOT = 'https://zestedesavoir.com'
FLUX = [
    ('/tutoriels/flux/rss/', 'nouveau tutoriel'),
    ('/articles/flux/rss/', 'nouvel article'),
    ('/billets/flux/rss/', 'nouveau billet'),
    ('/forums/flux/sujets/rss/', 'nouveau sujet')
]
WEBHOOK_URL = open('webhook_url.txt').read()

HORO_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'horodatage.json')


def get_items_from_url(url, force=False):
    print(url)
    page = request.urlopen(url).read()
    root = ET.fromstring(page)

    lastBuildList = {}
    with open(HORO_PATH, 'r') as f:
        lastBuildList = json.load(f)

    date_min = lastBuildList.get(url, 0)
    lastBuildDate = next(root.iter('lastBuildDate')).text
    lastBuildDate = datetime.strptime(lastBuildDate, '%a, %d %b %Y %H:%M:%S %z')
    lastBuildDate = int(lastBuildDate.timestamp())
    if not force:
        if lastBuildDate <= date_min:
            print('RSS is not new')
            return []
    else:
        print('forcing refresh')

    items = []
    for item in root.iter('item'):
        temp = {}
        temp['title'] = item.find('title').text
        temp['link'] = item.find('link').text
        temp['description'] = item.find('description').text
        temp['creator'] = item.find(r'{http://purl.org/dc/elements/1.1/}creator').text
        temp['guid'] = item.find('guid').text
        temp['pubDate'] = datetime.strptime(item.find('pubDate').text, '%a, %d %b %Y %H:%M:%S %z')  # Tue, 15 Jan 2019 00:09:15 +0100
        pubDate = int(temp['pubDate'].timestamp())
        if force or pubDate > date_min:
            items.append(temp)

    with open(HORO_PATH, 'w') as f:
        lastBuildList[url] = lastBuildDate
        json.dump(lastBuildList, f)

    return items


def post_item_to_discord(item, content_type):
    payload = {
        'content': 'Un {} est est ligne !'.format(content_type),
        'embeds': [{
            'title': item['title'],
            'description': item['description'],
            'url': item['link'],
            'timestamp': item['pubDate'].isoformat(),
            'author': {'name': item['creator']},
        }]
    }
    headers = {
        'Content-Type': 'application/json',
        'user-agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
    }
    req = request.Request(url=WEBHOOK_URL,
                          data=json.dumps(payload).encode('utf-8'),
                          headers=headers,
                          method='POST')
    try:
        r = request.urlopen(req)
        print(r.status)
        print(r.reason)
        print(r.headers)
    except HTTPError as e:
        print('ERROR')
        print(e.reason)
        print(e.hdrs)
        print(e.file.read())


if __name__ == '__main__':
    for f in FLUX:
        items = get_items_from_url(ROOT + f[0])
        for item in items:
            post_item_to_discord(item, f[1])
            time.sleep(2)  # Lazy workaround to not break the rate limit
