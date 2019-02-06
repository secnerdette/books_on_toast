#!/usr/bin/env python3

import keyring
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pprint
import json
import csv
import datetime

DEVELOPER_KEY = keyring.get_password("goog_api", "goog_api_key")
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
channel_id = 'UCSzPk0ShJD6ygdZw7HqK5QA'
pp = pprint.PrettyPrinter(indent=2)

def get_videos(options, videos, next_page_token=None, date_cursor=None):
    response = youtube.activities().list(
        part = 'snippet,contentDetails',
        channelId = channel_id,
        maxResults = options.mr,
        pageToken = next_page_token,
    ).execute()
    print("Fetched results for next page token: ", next_page_token)

    for result in response.get('items', []):
        if 'upload' in result['contentDetails']:
            vid_info = {}
            vid_info['id'] = result['contentDetails']['upload']['videoId']
            vid_info['title'] = result['snippet']['title']
            vid_info['details'] = result['snippet']['description']
            videos.append(vid_info)
    return response.get('nextPageToken')

def get_booklist(options):
    videos = []
    page = 0
    next_page_token = None

    while page == 0 or next_page_token != None:
        next_page_token = get_videos(options, videos, next_page_token)
        page += 1
        
    f = open("botcast_vids.txt","w")
    for vid in videos:
        f.write(json.dumps(vid) + '\n')
    f.close()

def process_videos():
    videos = []
    with open("botcast_vids.txt", "r") as f:
        for line in f:
            videos.append(json.loads(line))
    print("Loaded videos total: ", len(videos))

    key_words = ['books discussed', 'comics discussed', 'buy:', 'buy this book', 'book recommended', 'book:', 'amzn']
    ids_to_delete = []
    count_start_match = 0
    for vid in videos:
        vid['details_lower'] = vid['details'].lower()
        curr_matched = False
        for kw in key_words:
            if kw in vid['details_lower']:
                count_start_match += 1
                curr_matched = True
                break
        if not curr_matched:
            ids_to_delete.append(vid['id'])
    print("Number of videos with matching start words: ", count_start_match)
    
    good_vids = []
    f2 = open("botcast_vids_good.txt", "w")
    for vid in videos:
        if vid['id'] not in ids_to_delete:
            good_vids.append(vid)
            f2.write(json.dumps(vid) + '\n')
    f2.close()

    book_info = []
    book_words = ['amzn', 'buy', 'bit.ly', 'a.co']
    for gv in good_vids:
        gv['details_lower'] = gv['details'].lower()
        split_by_newline = gv['details_lower'].split('\n')
        books_in_vid = []
        for i in range(len(split_by_newline)):
            if any(bw in split_by_newline[i] for bw in book_words):
                books_in_vid.append(split_by_newline[i-1])

        clean_booklist = []
        for bks in books_in_vid:
            if not any(w in bks for w in book_words) and bks != '':
                clean_booklist.append(bks)
        gv['clean_booklist'] = clean_booklist

        books_by_ep = {}
        books_by_ep['video_title'] = gv['title']
        books_by_ep['book_names'] = gv['clean_booklist']
        book_info.append(books_by_ep)

    f3 = csv.writer(open("botcast_final_list.csv", "r+"))
    f3.writerow(["video title", "books discussed"])
    f4 = open("reviewed_books.txt", "r+")
    for books in book_info:
        if books['video_title'] not in f4.read():
            for bk in books['book_names']:
                f3.writerow([books['video_title'], bk])
                f4.write(json.dumps(books['video_title']) + '\n')
    f4.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mr', help='Max results', default=50)
    parser.add_argument('--fvids', help='Fetch videos info from Youtube', default=False)
    parser.add_argument('--pvids', help='Process videos from file', default=False)
    args = parser.parse_args()

    try:
        if args.fvids:
            get_booklist(args)
            process_videos()
        if args.pvids:
            process_videos()
    except HttpError as e:
        print('An HTTP error %d occurred:\n%s' % (e.resp.status, e.content))
