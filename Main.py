from datetime import datetime
from datetime import timedelta
import enum
import os
import time
import json
from urllib.parse import urlparse
from NPRPageParser import NPRPageParser
from NPRSpotifySearch import NPRSpotifySearch
from NPRPlaylistCreator import NPRPlaylistCreator

# # Create a json file for the year that contains a link for each day (only need to run one time per year)
# NPRPageParser.NPRArticleLinkCacheCreator(2018) # 1996 - 2020

# # Weekend edition shows up 1998 Jan
# # July 25th 2000's seems to be when some morning edition interlude data is being documented
# # Used to create json output for each day with various article and track data
# editionStartYear = 2002
# editionDayData = list()
# projectName = "MoWeEd"
# editionYearLinkCache = NPRPageParser.LoadJSONFile(projectName + " Article Link Cache/" + str(editionStartYear) + " " + projectName + " Article Link Cache.json")
# for month, daylinks in editionYearLinkCache.items():
#     for idx, link in enumerate(daylinks):
#         nprSpotifySearch = NPRSpotifySearch()
#         nprPlaylistCreator = NPRPlaylistCreator()
#         nprPageParser = NPRPageParser()
#         requestedHTML = NPRPageParser.RequestURL(link)
#         selectedHTML = NPRPageParser.SelectStory(requestedHTML.text) # select the returned HTML
#         editionDayData.append(NPRPageParser.GetEditionData(link, selectedHTML)) # get various article data from this day
#         for story in selectedHTML.xpath('.//div[@id="story-list"]/*'):
#             if story.attrib['class'] == 'rundown-segment':
#                 editionDayData.append(NPRPageParser.GetArticleInfo(story))
#             elif story.attrib['class'] == 'music-interlude responsive-rundown':
#                 for songMETA in story.xpath('.//div[@class="song-meta-wrap"]'):
#                     interlude = dict()
#                     interlude["MoWeEd Track"] = NPRPageParser.GetInterludeSongName(songMETA)
#                     interlude["MoWeEd Artists"] = NPRPageParser.GetInterludeArtistNames(songMETA)
#                     editionDayData.append(interlude)
#                     print(json.dumps(interlude, indent=4, sort_keys=True, ensure_ascii=False))
#         editionYear = editionDayData[0]['Date Numbered'][0:4]
#         editionMonth = editionDayData[0]['Date Numbered'].partition("-")[2].partition("-")[0]
#         editionDate = editionDayData[0]['Date Numbered']
#         editionDay = editionDayData[0]['Day']
#         editionEdition = editionDayData[0]["Edition"][0:15]
#         projectName = "MoWeEd"
#         fileType = ".json"
#         fileName = projectName + " " + editionDate + " " + editionDay + " " + editionEdition + fileType
#         directoryPath = "MoWeEd Article Data/{0}/{1}/".format(editionYear, editionMonth)
#         nprPageParser.SaveJSONFile(editionDayData, directoryPath, fileName)
#         print("Finished {0}\n".format(editionDayData[0]['Page Link']))
#         editionDayData.clear()
#         time.sleep(1) # Don't hammer their server

# Used to parse a range of dates, load the json for those days, and make playlists on spotify
startDate = datetime(2002, 1, 16)
projectName = "MoWeEd"
weekendEdition = "Weekend Edition"
morningEdition = "Morning Edition"
nprPlaylistCreator = NPRPlaylistCreator()
nprSpotifySearch = NPRSpotifySearch()
nprPageParser = NPRPageParser()
spotifyTracks = list()
while startDate != datetime(2002, 2, 1):
    projectPath = projectName + " Article Data/{0}/{1}/".format(startDate.year, startDate.strftime("%m"))
    morningEditionFileName = projectName + " {0} {1} {2}".format(startDate.strftime("%Y-%m-%d"), startDate.strftime("%a"), "Morning Edition")
    weekendEditionFileName = projectName + " {0} {1} {2}".format(startDate.strftime("%Y-%m-%d"), startDate.strftime("%a"), "Weekend Edition")
    fileType = ".json"
    # Load article data from disk
    if startDate.weekday() <= 4:
        editionDay = NPRPageParser.LoadJSONFile(projectPath + morningEditionFileName + fileType)
        filename = morningEditionFileName
    else:
        editionDay = NPRPageParser.LoadJSONFile(projectPath + weekendEditionFileName + fileType)
        filename = weekendEditionFileName
    # check if edition data is present
    if editionDay == None:
        print(">> No data for {0} ".format(startDate.date()))
        startDate = startDate + timedelta(days=+1)
    else:
        playlistURI = "Playlist URI"
        searchKey = "MoWeEd Track"
        pageLinkID = "Page Link"
        playlistEntry = False
        trackEntry = False
        if editionDay[0].get(playlistURI) != None:
            playlistEntry = True # would only be in the first entry currently
        for item in editionDay:
            if item.get(searchKey) == None:
                continue
            else:
                trackEntry = True
                break
        # Create a new playlist and search tracks
        if playlistEntry == False and trackEntry == True:
            response = nprPlaylistCreator.CreatePlaylist(filename) # should I deal with passing in my editionDay or manage updates/changes out here?
            editionDay[0]["Playlist URI"] = response["id"]
            editionDay[0]["Playlist Link"] = response["external_urls"]["spotify"]
            editionDay[0]["Snapshot ID"] = response["snapshot_id"]
            editionDay[0]["Playlist Name"] = filename
            nprPlaylistCreator.AddCoverArtToPlaylist(editionDay)
            # Search interlude tracks and add results back into edition data
            for story, entry in enumerate(editionDay):
                if searchKey in entry:
                    track = nprSpotifySearch.SearchSpotify(entry["MoWeEd Track"], entry["MoWeEd Artists"])
                    entry.update(track)
            nprPlaylistCreator.AddTracksToPlaylist(editionDay)
            nprPlaylistCreator.UpdatePlaylistDescription(editionDay)
            nprPageParser.SaveJSONFile(editionDay, projectPath, filename + fileType)
            print("{0} finished {1}".format(startDate.date(), editionDay[0]['Playlist Link']))
            print(editionDay[0]["Page Link"])
            print("\n")
            editionDay.clear()
            startDate = startDate + timedelta(days=+1)
            time.sleep(1) # Don't hammer their server
        # we update information
        elif playlistEntry == True:
            for story, entry in enumerate(editionDay):
                if searchKey in entry:
                    track = nprSpotifySearch.SearchSpotify(entry["MoWeEd Track"], entry["MoWeEd Artists"])
                    entry.update(track)
            editionDay = nprPlaylistCreator.ReplaceTracksInPlaylist(editionDay)
            nprPlaylistCreator.UpdatePlaylistDescription(editionDay)
            nprPageParser.SaveJSONFile(editionDay, projectPath, filename + fileType)
            print("{0} finished updating {1}".format(startDate.date(), editionDay[0]['Playlist Link']))
            print(editionDay[0]["Page Link"])
            print("\n")
            editionDay.clear()
            startDate = startDate + timedelta(days=+1)
            time.sleep(1.5) # Don't hammer their server
        # we create an empty playlist with a description noting tracks are not detailed
        else:
            response = nprPlaylistCreator.CreatePlaylist(filename) # should I deal with passing in my editionDay or manage updates/changes out here?
            editionDay[0]["Playlist URI"] = response["id"]
            editionDay[0]["Playlist Link"] = response["external_urls"]["spotify"]
            editionDay[0]["Snapshot ID"] = response["snapshot_id"]
            editionDay[0]["Playlist Name"] = filename
            nprPlaylistCreator.AddCoverArtToPlaylist(editionDay)
            nprPlaylistCreator.UpdatePlaylistDescription(editionDay)
            nprPageParser.SaveJSONFile(editionDay, projectPath, filename + fileType)
            print(">> No interlude Tracks for {0} ".format(startDate.date()))
            editionDay.clear()
            startDate = startDate + timedelta(days=+1)
            time.sleep(1.5) # Don't hammer their server

