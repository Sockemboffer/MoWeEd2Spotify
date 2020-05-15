import json
import requests
from exceptions import ResponseException
from secrets import spotify_token, spotify_client_id
from urllib import parse
import re
from string import Template
import datetime
# note: Playlists can have a maximum of 10,000 tracks each.
# note: You can have as many playlists as you want, but only with 10k tracks each. (confusing info on)

# todo: generate playlist title from npr pages
# todo: generate playlist descriptions from npr pages
# todo: upload playlist image from npr pages (credit photographer)
    # todo: watermark images?
# todo: create search types to aid with quicker human verification
# todo: store found uri's into parsed npr json file
# todo: store used uri vs. additional uri's for later human verification
# todo: read/write to json about no track or artist found during search
    # todo: notify when previously not found track is found
    # todo: read/write and store created playlists in json file
# todo: add missing tracks to playlist info, last time checked date, up-coming check date
# todo: handle invalid token check

class CreatePlaylist:
    def __init__(self):
        self.all_song_info = list()
        self.all_uri_info = list()
        self.songLastChecked = ""
        self.playListID = ""
        self.nprPageLink = ""
        self.playListDescription = ""

    def get_json_data(self):
        with open('NPRPageParser.json', "r") as json_file:
            data = json.load(json_file)
            json_file.close()
            return data

    def get_artist_data(self, jsonData):
        for entry in jsonData:
            for value in entry:
                if isinstance(value, dict):
                    self.all_song_info.append(value)
        # print(self.all_song_info)
        return self.all_song_info

    def create_playlist(self):
        jsonData = self.get_json_data()
        for dic in jsonData:
            if "Day" in dic:
                dayText = str(dic.get("Day"))
            if "Date Text" in dic:
                dateText = str(dic.get("Date Text"))
            if "Page Link" in dic:
                self.nprPageLink = str(dic.get("Page Link"))
            if "Edition" in dic:
                editionText = str(dic.get("Edition"))
        # Create A New Playlist that we can fill up with interlude songs
        request_body = json.dumps({
            "name": editionText + " for " + dayText + ", " + dateText,
            "public": False})

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_client_id) 
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)})
        response_json = response.json()
        #print(response_json)

        # playlist id
        #print(response_json["id"])
        self.playListID = response_json["id"]
        return response_json["id"]

    def get_spotify_uri(self, jsonData, artistList):
        # building uri list to use later in playlist fill-up
        foundTracks = list()
        multipleArtists = ""
        query = ""
        for dic in artistList:
            if "Interlude Artist" in dic:
                artists = list()
                artists = str(dic.get("Interlude Artist")).split(" & ")
                #print(len(artists))
            if "Interlude Song" in dic:
                track = dic.get("Interlude Song")
                #print(track)

            # taking only the first result from a track + artist search which is not always a match
            # 1, 2, or 3 common word names will return multiple hits where the 1st match is likely not it
            # Unique names more likely a match but small chance composer broadway/orchistra aren't artist name
            # who performed the version found on npr page
            if len(artists) > 1:
                query = "https://api.spotify.com/v1/search?q={}&type=track%2Cartist&market=US&limit=5".format(
                        parse.quote('track:' + '"' + track + '"' + " " + '"' + '" AND "'.join(artists) + '"'))
                #print(query)
            else:
                query = "https://api.spotify.com/v1/search?q={}&type=track%2Cartist&market=US&limit=5".format(
                        parse.quote('track:' + '"' + track + '"' + ' ' + 'artist:' + '"' + " ".join(artists) + '"'))
                #print(query)
            
            response = requests.get(
                query,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {}".format(spotify_token)})

            response_json = response.json()
            #print(json.dumps(response_json, indent=4))

            if response_json["tracks"]["total"] != 0:
                print(" Track: " + track + ", By: " + ", ".join(artists))
                self.all_uri_info.append(response_json["tracks"]["items"][0]["uri"])
                # insert track uri back into jsonData
                with open('NPRPageParser.json', 'w') as json_file:
                    for entry in jsonData:
                        for value in entry:
                            if isinstance(value, dict):
                                #print(value)
                                for k, v in value.items():
                                    if v == track:
                                        # print(k)
                                        for k, v in value.items():
                                            if k == "Spotify URI":
                                                v = response_json["tracks"]["items"][0]["uri"]
                                                value[k] = v
                                                #print(k)
                                            if k == "Last Checked":
                                                self.songLastChecked = str(datetime.datetime.now().__format__("%Y-%m-%d %H:%M:%S"))
                                                value[k] = self.songLastChecked
                                                #print(k)
                                        
                    #print(jsonData)
                    json.dump(jsonData, json_file, ensure_ascii=False, indent=4)
                    json_file.close()
            else:
                print("!Track: " + track + ", By: " + ", ".join(artists))
                # insert last checked back into json file
                with open('NPRPageParser.json', 'w') as json_file:
                    for entry in jsonData:
                        for value in entry:
                            if isinstance(value, dict):
                                #print(value)
                                for k, v in value.items():
                                    if v == track:
                                        # print(k)
                                        for k, v in value.items():
                                            if k == "Last Checked":
                                                dt = str(datetime.datetime.now().__format__("%Y-%m-%d %H:%M:%S"))
                                                v = dt
                                                value[k] = v
                                                #print(k)
                    request_body = json.dumps({
                        "description": self.nprPageLink + " | " + "Missing Track: '" + track + "' | " + "By: '" + ", ".join(artists) + "' | " + "Last Checked: " + self.songLastChecked,})
                    query = "https://api.spotify.com/v1/playlists/{}".format(self.playListID) 
                    response = requests.put(
                        query,
                        data=request_body,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer {}".format(spotify_token)})
                    print(response)
                    json.dump(jsonData, json_file, ensure_ascii=False, indent=4)
                    json_file.close()
        return self.all_uri_info

    def add_song_to_playlist(self, playListID, uriList):
        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playListID)

        request_data = json.dumps(uriList)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)})

        # check for valid response status
        if response.status_code != 200 or response.status_code != 201:
            myResponse = "<==^_^==>"
            return myResponse
        else:
            raise ResponseException(response.status_code)
            return response_json

        #response_json = response.json()

newPlaylistCreator = CreatePlaylist()
jsonData = newPlaylistCreator.get_json_data()
#print(json.dumps(jsonData, indent=4, sort_keys=False))
dayInterludeList = newPlaylistCreator.get_artist_data(jsonData)
newPlaylist = newPlaylistCreator.create_playlist()
#print(json.dumps(dayInterludeList, indent=4, sort_keys=False))
spotifyURIs = newPlaylistCreator.get_spotify_uri(jsonData, dayInterludeList)
#print(spotifyURIs)
spotifyResponse = newPlaylistCreator.add_song_to_playlist(newPlaylist, spotifyURIs)
print(json.dumps(spotifyResponse, indent=4))