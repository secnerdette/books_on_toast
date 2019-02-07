#!/usr/bin/env python3

import keyring
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pprint
import json
import csv
import datetime

DEVELOPER_KEY = keyring.get_password("goog_api", "goog_api_key") #Enter your developer API key here
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)
channel_id = 'UCSzPk0ShJD6ygdZw7HqK5QA' #Id of the Youtube channel you want to get details from
pp = pprint.PrettyPrinter(indent=2)

def get_videos(options, videos, next_page_token=None, date_cursor=None):
    response = YOUTUBE.activities().list(
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
    good_vids = []
    with open("botcast_vids.txt", "r") as f:
        for line in f:
            videos.append(json.loads(line))
    print("Loaded videos total: ", len(videos))

    #extract a list of 'good videos' that have keywords which suggests the video details have book recommendations
    f2 = open("botcast_vids_good.txt", "w")
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
                good_vids.append(vid)
                f2.write(json.dumps(vid) + '\n')
                break
        if not curr_matched:
            ids_to_delete.append(vid['id'])
    print("Number of videos with matching start words: ", count_start_match)
    f2.close()

    #get the book names which usually appear above 'book words'
    book_info = []
    book_words = ['amzn', 'buy', 'bit.ly', 'a.co']
    for gv in good_vids:
        gv['details_lower'] = gv['details'].lower()
        split_by_newline = gv['details_lower'].split('\n')
        books_in_vid = []
        for i in range(len(split_by_newline)):
            if any(bw in split_by_newline[i] for bw in book_words):
                books_in_vid.append(split_by_newline[i-1])

        #clean the booklist and remove any trailing entries with links or empty strings
        clean_booklist = []
        for bks in books_in_vid:
            if not any(w in bks for w in book_words) and bks != '':
                clean_booklist.append(bks)
        gv['clean_booklist'] = clean_booklist

        #get 'episode title's and 'book names' in a dictionary and append all the values in 'book_info' as a list
        books_by_ep = {}
        books_by_ep['video_title'] = gv['title']
        books_by_ep['book_names'] = gv['clean_booklist']
        books_by_ep['vid_id'] = gv['id']
        book_info.append(books_by_ep)

    #write the book titles and book names in a CSV if the video entry doesn't already exist
    f3 = csv.writer(open("/Users/pvirani/books_on_toast/botcast_final_list.csv", "r+")) #add your own filepath here
    f3.writerow(["video title", "books discussed"])

    with open("reviewed_books.txt", "r+") as f4:
        old_title_list = set(f4.read())
        for books in book_info:
            if books['video_title'] not in old_title_list:
                f4.write(json.dumps(books['video_title']) + '\n')
                for bk in books['book_names']:
                    f3.writerow([books['video_title'], bk])
    f4.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mr', help='Max results', default=50)
    parser.add_argument('--fvids', help='Fetch videos info from Youtube', default=True)
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
