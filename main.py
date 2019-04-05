"""
main.py

fetches the most recent video upload for a channel (currently only Dunk Tank)
converts to mp3 and files as a podcast in the appropriate directory. Creates/updates(?)
rss feed for that channel to include this item
"""

import os
import requests
import youtube_dl
import unidecode
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator


def string_cleanup(str):
	return unidecode.unidecode(BeautifulSoup(str, features="lxml").text)


if __name__ == '__main__':
	API_KEY = os.environ['API_KEY']

	chan_id = 'UCGiJeCKTVKIxtaYZOidh19g'  # Dunk Tank
	# chan_id = 'UCbpMy0Fg74eXXkvxJrtEn3w'  # Bon Appetit

	vid_opts = {'key': API_KEY,
				'channelId': chan_id,
				'part': 'snippet,id',
				'order': 'date'}
	chan_opts = {'key': API_KEY,
				 'id': chan_id,
				 'part': 'snippet'}

	vids_info = requests.get('https://www.googleapis.com/youtube/v3/search', params=vid_opts).json()
	chan_info = requests.get('https://www.googleapis.com/youtube/v3/channels', params=chan_opts).json()

	chan_url = 'https://www.youtube.com/channel/' + chan_id

	chan_name = string_cleanup(vids_info['items'][0]['snippet']['channelTitle'])
	chan_desc = string_cleanup(chan_info['items'][0]['snippet']['description'])

	output_folder = os.path.join('/mnt/red/podcasts', chan_name)
	file_ext = 'mp3'

	updated = False

	while True:
		for vid in vids_info['items']:
			temp_name = string_cleanup(vid['snippet']['title'] + '.' + file_ext)
			file_path = os.path.join(output_folder, temp_name)

			if not os.path.exists(output_folder):
				os.makedirs(output_folder)

			if not os.path.isfile(file_path) and 'videoId' in vid['id']:
				updated = True
				vid_url = 'https://www.youtube.com/watch?v={}'.format(vid['id']['videoId'])
				vid_desc = vid['snippet']['description']

				ydl_opts = {'format': 'bestaudio/best',
							'postprocessors': [{
								'key': 'FFmpegExtractAudio',
								'preferredcodec': file_ext,
								'preferredquality': '192',
							}]}

				with youtube_dl.YoutubeDL(ydl_opts) as ydl:
					ydl.download([vid_url])
		if 'nextPageToken' not in vids_info:
			break

		vid_opts['pageToken'] = vids_info['nextPageToken']
		vids_info = requests.get('https://www.googleapis.com/youtube/v3/search', params=vid_opts).json()

	if True:
		external_ip = requests.get('https://api.ipify.org').text
		gen = FeedGenerator()
		gen.load_extension('podcast')
		gen.title(chan_name)
		gen.description(chan_desc)
		gen.link(href=chan_url, rel='alternate')
		gen.link(href=('https://' + external_ip + '/rss?chan=' + chan_name), rel='self')
		gen.logo(chan_info['items'][0]['snippet']['thumbnails']['high']['url'])
		gen.language('en')
		# gen.podcast.itunes_category('Games & Hobbies', 'Video Games')
		# gen.podcast.itunes_explicit('no')
		gen.podcast.itunes_complete('no')
		gen.podcast.itunes_new_feed_url(chan_url)
		# gen.podcast.itunes_owner('videogamedunkey', 'dunkeyscastle@outlook.com')
		gen.podcast.itunes_summary(chan_desc)
		gen.podcast.itunes_author(chan_name)

		for root, dirs, files in os.walk(output_folder):
			for file in files:
				if file_ext in file:
					entry = gen.add_entry()
					entry.id('some link for now')  # TODO What does this need to be for the webserver to find it?
					entry.title(file)
					entry.podcast.itunes_author(chan_name)

		gen.rss_file(os.path.join(output_folder, 'feed.xml'))
