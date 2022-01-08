import os
import re
import json
import time
import requests
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from parsel import Selector

class NPRPageParser:
    def __init__(self):
        self.nprurl = ""

    # Request the html at link address
    def RequestURL(url):
        request = requests.get(url)
        if request.reason != "OK":
            print("Link: " + url + "\n" + request.reason)
        else:
            print("-- URL Request Successful.")
            return request

    # Grab the HTML Story block
    def SelectStory(html):
        selector = Selector(text=html)
        print("-- NPR Page Selected.")
        return selector

    # Grab various info about the whole NPR article for that date
    def GetEditionData(url, selectedHTML):
        dayDetails = dict()
        dayDetails['Page Link'] = url.partition("?")[0]
        dayDetails['Edition'] = selectedHTML.xpath('//header[@class="contentheader contentheader--one"]//h1/b/text()').get()[0:15]
        dayDetails['Date Numbered'] = selectedHTML.xpath('//div[@id="episode-core"]//nav[@class="program-nav program-nav--one"]//time/@datetime').get()
        dayDetails['Day'] = selectedHTML.xpath('//div[@id="episode-core"]//nav[@class="program-nav program-nav--one"]//time/b[@class="date"]//b[@class="day"]/text()').get()[0:3]
        datetTime = str(datetime.now().__format__("%Y-%m-%d %H:%M:%S"))
        dayDetails['Scanned Date'] = datetTime
        print("-- Edition Data Found.")
        return dayDetails

    # Grab data about each article         
    def GetArticleInfo(articleHTML):
        articleInfo = dict()
        articleTitle = articleHTML.xpath('.//div/h3[@class="rundown-segment__title"]/a/text()').get()
        articleLink = articleHTML.xpath('.//div/h3[@class="rundown-segment__title"]/a/@href').get()
        articleSlug = articleHTML.xpath('.//div/h4[@class="rundown-segment__slug"]/a/text()').get()
        articleBy = articleHTML.xpath('.//span[@class="byline byline--inline"]/text()').get()
        articleInfo['Title'] = articleTitle if type(articleTitle) else None
        articleInfo['Link'] = articleLink if type(articleLink) else None
        articleInfo['Slug'] = articleSlug if type(articleSlug) else None
        articleInfo['By'] = articleBy if type(articleBy) else None
        print("-- Article Info Found.")
        return articleInfo

    # Grab data about each interlude
    def GetInterludeSongName(songHTML):
        if songHTML.xpath('.//span[@class="song-meta-title"]/text()').get() == None:
            return " "
        else:
            return re.sub(" +", " ", re.sub("^\s+|\s+$", "", songHTML.xpath('.//span[@class="song-meta-title"]/text()').get()))

    def GetInterludeArtistNames(songHTML):
        if songHTML.xpath('.//span[@class="song-meta-artist"]/text()').get() == None:
            return " "
        else:
            artists = re.split('[,;&/]', re.sub(" +", " ", re.sub("^\s+|\s+$", "", songHTML.xpath('.//span[@class="song-meta-artist"]/text()').get())))
            artists[:] = [s.strip() for s in artists]
            return artists

    # Load json file data, check to ensure it's valid first
    def LoadJSONFile(filename):
        if os.path.exists(filename) == True:
            with open(filename, "r", encoding='utf-8') as json_file:
                try:
                    loadedJson = json.load(json_file)
                    return loadedJson
                except ValueError as e:
                    print('invalid json: %s' % e)
                    return None # or: raise
        else:
            print("No valid file exists at {0}: ".format(filename))
            return None
    
    def SaveJSONFile(editionData, path, file):
        # playlistPath = os.path.join("MoWeEd Article Data/{0}/{1}/MoWeEd {2} {3} {4}.json".format(editionYear, editionMonth, editionDate, editionDay, editionEdition))
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path + file, 'w', encoding='utf-8') as json_file:
            json.dump(editionData, json_file, ensure_ascii=False, indent=4)

    # request/fetch artist data from json file
    def GetArtistsAndTrack(jsonData):
        interludes = list()
        for entry in jsonData:
            for value in entry:
                if isinstance(value, dict):
                    interludes.append(value)
        return interludes

    # Grab all day links for date range entered save back to json file
    def NPRArticleLinkCacheCreator(leftOffDate: datetime, today: datetime, projectName: str):
        editionYearLinkCache = dict()
        cachePath = projectName + " Article Link Cache/"
        while leftOffDate <= today:
            cacheFileName = str(leftOffDate.year) + " " + projectName + " Article Link Cache.json"
            editionYearLinkCache = NPRPageParser.LoadJSONFile(cachePath + cacheFileName)
            articleDayLinks = list()
            print(leftOffDate.month)
            # Any archive date seems to set us at the last day of the month (handy)
            # Generate archive month link - use the 1st of every month
            # Grab all Sunday Editions for this month
            sunday = "https://www.npr.org/programs/weekend-edition-sunday/archive?date={}-{}-{}".format(str(leftOffDate.month).zfill(2), str(1).zfill(2), leftOffDate.year)
            request = requests.get(sunday).text
            selector = Selector(text=request)
            print("Getting Sundays")
            for item in selector.xpath('.//div[@id="episode-list"]/*'):
                if item.attrib['class'] != 'episode-list__header':
                    articleDayLinks.append(item.xpath('./h2[@class="program-show__title"]/a/@href').get())
            # Grab all Saturday Edition links for this month
            saturday = "https://www.npr.org/programs/weekend-edition-saturday/archive?date={}-{}-{}".format(str(leftOffDate.month).zfill(2), str(1).zfill(2), leftOffDate.year)
            request = requests.get(saturday).text
            selector = Selector(text=request)
            print("Getting Saturdays")
            for item in selector.xpath('.//div[@id="episode-list"]/*'):
                if item.attrib['class'] != 'episode-list__header':
                    articleDayLinks.append(item.xpath('./h2[@class="program-show__title"]/a/@href').get())
            # Grab intial amount of Morning Edition links for this month
            weekday = "https://www.npr.org/programs/morning-edition/archive?date={}-{}-{}".format(str(leftOffDate.month).zfill(2), str(1).zfill(2), leftOffDate.year)
            request = requests.get(weekday).text
            selector = Selector(text=request)
            print("Getting initial weekdays")
            for item in selector.xpath('.//div[@id="episode-list"]/*'):
                if item.attrib['class'] != 'episode-list__header':
                    articleDayLinks.append(item.xpath('./h2[@class="program-show__title"]/a/@href').get())
            # NPR only loads more days once the user scrolls to the bottom of their page,
            # we need to fetch the "scrolllink" link to grab more days untill a new month is found
            nextMonthNotFound = True
            checkMonth = str(leftOffDate.year) + "/" + str(leftOffDate.month).zfill(2) + "/"
            while nextMonthNotFound:
                print("Getting more weekdays")
                loadMoreDaysLink = selector.xpath('//div[@id="scrolllink"]/a/@href').get()
                # Check we have more days to load
                if loadMoreDaysLink == None:
                    break
                moreDaysLink = "https://www.npr.org" + loadMoreDaysLink
                request = requests.get(moreDaysLink).text
                selector = Selector(text=request)
                for item in selector.xpath('.//div[@id="episode-list"]/*'):
                    if item.attrib['class'] != 'episode-list__header':
                        newLink = item.xpath('./h2[@class="program-show__title"]/a/@href').get()
                        if checkMonth in newLink:
                            articleDayLinks.append(newLink)
                        else:
                            nextMonthNotFound = False
                            break
            print("Sorting links")
            # filter out links that aren't the same month
            articleDayLinks = list(filter(lambda x: "/" + str(leftOffDate.month).zfill(2) + "/" in x, articleDayLinks))
            # sort them in decending order
            articleDayLinks = sorted(articleDayLinks, key=lambda x: int(x.partition("/" + str(leftOffDate.month).zfill(2) + "/")[2].partition("/")[0]))
            # create first month of new year if none
            if editionYearLinkCache == None:
                editionYearLinkCache = dict()
                editionYearLinkCache = {"01": articleDayLinks}
            else:
                newDict = {str(leftOffDate.month).zfill(2): articleDayLinks}
                if str(leftOffDate.month).zfill(2) in editionYearLinkCache:
                    editionYearLinkCache.update(newDict)
                else:
                    updatedDict = {**newDict, **editionYearLinkCache}
                    editionYearLinkCache = updatedDict
            leftOffDate = leftOffDate + timedelta(days=+(len(articleDayLinks) - int(leftOffDate.day) + 1))
            NPRPageParser.SaveJSONFile(editionYearLinkCache, cachePath, cacheFileName)
        return