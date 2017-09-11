#!/usr/bin/env python3
"""HackerNews API client library."""

import argparse
import asyncio
import logging

import aiohttp
import async_timeout


FETCH_TIMEOUT = 1000
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/{}.json'
LOGGER = logging.getLogger()
USER_URL = 'https://hacker-news.firebaseio.com/v0/user/{}.json'


async def async_fetch_url(url, session):
    """Download JSON from the url."""
    with async_timeout.timeout(FETCH_TIMEOUT):
        async with session.get(url) as response:
            return await response.json()

async def async_fetch_urls(urls, session, recursive=0):
    """Download (asynchronously) JSON from the urls.

    Params:
        urls : list[string] : list of urls to be fetched
        recursive : int : if positive, dig down to 'recursive' level of 'kids'

    Returns:
        list[dict] : list of dicts with HN posts in question
    """
    LOGGER.debug('fetching %s urls with recursive=%s', len(urls), recursive)
    tasks = [asyncio.ensure_future(async_fetch_url(url, session))
             for url in urls]
    items = await asyncio.gather(*tasks)
    if recursive > 0:
        new_items = []
        for i, item in enumerate(items):
            if item:
                kids = item.get('kids') or item.get('submitted') or []
                urls = [ITEM_URL.format(kid) for kid in kids]
                if urls:
                    LOGGER.debug('[%d/%d/%d] adding %s urls to the queue',
                                 i+1,
                                 len(items),
                                 len(items)+len(new_items),
                                 len(urls))
                    new_items += await async_fetch_urls(
                        urls, session, recursive=recursive-1)
        items += new_items
    return items

def fetch_urls(urls, recursive=0):
    """Download (asynchronously) JSON from the urls.

    Params:
        urls : list[string] : list of urls to be fetched
        recursive : int : if positive, dig down to 'recursive' level of 'kids'

    Returns:
        list[dict] : list of dicts with HN posts in question
    """
    LOGGER.debug('fetching %s urls with recursive=%s', len(urls), recursive)
    loop = asyncio.get_event_loop()
    items = []
    with aiohttp.ClientSession(loop=loop) as session:
        items = loop.run_until_complete(
            async_fetch_urls(urls, session, recursive=recursive)
        )
    loop.close()
    return items

def get_user_items(username, recursive=0):
    """Return all user's items.

    Params:
        username : string : e.g. 'whoishiring'

    Return:
        list[dict] : list of user's posts
    """
    LOGGER.debug('fetching posts of %s', username)
    url = USER_URL.format(username)
    return fetch_urls([url], recursive=recursive)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='[%H:%M:%S]')
    parser = argparse.ArgumentParser(description='Fetch HN posts.')
    parser.add_argument('--author',
                        type=str,
                        help='Name of posts author')
    parser.add_argument('--recursive',
                        type=int,
                        default=0,
                        help='Recursion level (default 0)')
    parser.add_argument('--verbose',
                        action='store_true',
                        help='Detailed output')
    args = parser.parse_args()
    if args.verbose:
        LOGGER.setLevel(logging.DEBUG)
    if args.author:
        data = get_user_items(args.author, args.recursive)
        print('fetched {} posts'.format(len(data)))
