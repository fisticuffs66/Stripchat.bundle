####################################################################################################
#                                                                                                  #
#                                Stripchat/Xhamsterlive Plex Channel                               #
#                                                                                                  #
####################################################################################################
from updater    import Updater
from DumbTools  import DumbKeyboard
from DumbTools  import DumbPrefs

from os.path    import abspath, exists

import json, datetime, time

PREFIX          = '/video/stripchat'
TITLE           = 'Stripchat'
ICON            = 'icon-default.png'
ART             = 'art-default.jpg'

BASE_URL        = 'https://xhamsterlive.com'
API_BASE        = BASE_URL + '/api/front'
API_MODELS      = API_BASE + '/models?limit={limit}&offset={offset}&tagAlias={tagAlias}&sortBy={sortBy}&uniq={uniq}'

PAGESIZE        = 100
DEFAULT_SORT    = 'trending'
DEFAULT_TAG     = 'females'

MAIN_LIST =     [
                    ('Women',       '/tags/females'), 
                    ('Men',         '/tags/men'),
                    ('Couples',     '/tags/couples'), 
                    ('Trans',       '/tags/trans')
                ]

SORT_LIST =     [
                    ('Trending',            'trending'),
                    ('StripScore',          'indexRating'),
                    ('Rating',              'normHistoryRating'),
                    ('New Faces',           'indexRating'),
                    ('Just Came Online',    'startBroadcastTime'),
                ]

####################################################################################################

def Start():
    ObjectContainer.title1      = TITLE
    ObjectContainer.art         = R(ART)

    DirectoryObject.thumb       = R(ICON)
    DirectoryObject.art         = R(ART)

    InputDirectoryObject.art    = R(ART)

    VideoClipObject.thumb       = R(ICON)
    VideoClipObject.art         = R(ART)

    HTTP.CacheTime              = 0

####################################################################################################

@handler(PREFIX, TITLE, thumb=ICON, art=ART)
def MainMenu():
    oc  = ObjectContainer(title2=TITLE, art=R(ART), no_cache=True)

    Updater(PREFIX + '/updater', oc)

    for (title, url) in MAIN_LIST:
        if title == 'Couples':
            oc.add(DirectoryObject(
                key     = Callback(SortList, title=title, url=url), 
                title   = title
            ))
        else:
            oc.add(DirectoryObject(
                key     = Callback(TagList, title=title, url=url), 
                title   = title
            ))

    return oc

####################################################################################################

@route(PREFIX + '/tags')
def TagList(title, url):
    oc          = ObjectContainer(title2=title, art=R(ART), no_cache=True)
    html        = HTML.ElementFromURL(BASE_URL+url)
    titleParent = title
    arrTags     = []

    for node in html.xpath('//div[contains(@class,"tag-group")]//a[@class="model-filter-link"]'):
        try:
            title   = node.xpath("text()")[0]
            href    = node.xpath('@href')[0]
            total   = node.xpath('./following-sibling::span[1]/text()')[0]

            if isinstance(total, int):
                total = int(total)

            if ' tk' not in title:
                arrTags.append((title, href, total))
        except:
            continue

    arrTags = sorted(arrTags, key=lambda x: x[0])
    arrTags.insert(0, ('All', url, 0))

    for data in arrTags:
        title   = data[0]
        url     = data[1]
        total   = data[2]

        titleCrumbs = '{} > {}'.format(titleParent, title)

        if title != 'All':
            title   = '{} ({})'.format(title, total)

        oc.add(DirectoryObject(
            key     = Callback(SortList, title=titleCrumbs, url=url), 
            title   = title
        ))

    return oc

####################################################################################################

@route(PREFIX + '/sort')
def SortList(title, url):
    oc          = ObjectContainer(title2=title, art=R(ART), no_cache=True)
    titleParent = title

    for (title, sort) in SORT_LIST:
        tag         = 'featured' if url == '' else url.split('/tags/')[-1]
        titleCrumbs = '{} > {}'.format(titleParent, title)

        oc.add(DirectoryObject(
            key     = Callback(CamList, title=titleCrumbs, url=url, tagAlias=tag, sort=sort), 
            title   = 'Sort by {}'.format(title)
        ))

    return oc

####################################################################################################

@route(PREFIX + '/cams/{page}', page=int, tagAlias=String, sort=String)
def CamList(title, url, page=1, tagAlias=DEFAULT_TAG, sort=DEFAULT_SORT):
    oc              = ObjectContainer(title2=title, no_cache=True)
    cr              = '\r' if Client.Product == 'Plex Web' else '\n'

    pageOffset      = 0 if page == 1 else (page - 1) * PAGESIZE
     
    countriesJson   = json.loads(
                        Core.storage.load(Core.storage.abs_path(Core.storage.join_path(
                            Core.bundle_path,
                            'Contents',
                            'Data',
                            'countries.json'
                        )))
                      )
    
    apiRequest      = API_MODELS.format(
                        limit       = PAGESIZE,
                        offset      = pageOffset,
                        tagAlias    = tagAlias,
                        sortBy      = sort,
                        uniq        = time.time()
                      )

    Log.Debug('API Request: {}'.format(apiRequest))
    
    metadataJson    = JSON.ObjectFromURL(apiRequest, encoding='utf-8')

    for metadataModel in metadataJson['models']:
        summary         = ''
        summaryStart    = ''
        summaryCountry  = ''
        
        camId           = metadataModel['id']
        camServer       = metadataModel['broadcastServer']
        camThumb        = metadataModel['snapshotUrl']
        camPreview      = metadataModel['previewUrl']
        camName         = metadataModel['username']
        camCountry      = metadataModel['country']
        camStart        = metadataModel['firstBroadcastTS']
        camUrl          = BASE_URL + '/' + camName + '?m=' + str(camId) + '&s=' + camServer

        for metadataCountry in countriesJson['countries']:   
            if metadataCountry['code'] == camCountry:
                summaryCountry = metadataCountry['title']
                break
                
        if isinstance(camStart, (int, long)):
            summaryStart = datetime.datetime.fromtimestamp(int(camStart)).strftime('%m-%d-%Y')
            
        if metadataModel['isNew'] == True:
            summary += 'NEW' + cr

        if len(summaryCountry) > 0:
            summary += summaryCountry + cr
                
        if len(summaryStart) > 0:
            summary += 'Broadcasting since ' + summaryStart + cr
            
        oc.add(VideoClipObject(
            url     = camUrl,
            title   = camName,
            thumb   = Resource.ContentsOfURLWithFallback(camThumb, fallback=camPreview),
            year    = datetime.datetime.now().year,
            summary = summary if len(summary) > 0 else 'No summary',
            tagline = ''
        ))
    
    if len(oc) > 0:
        if len(oc) >= PAGESIZE:
            oc.add(DirectoryObject(
                key     = Callback(CamList, title=title, url=url, page=page+1),
                title   = 'Next Page'
            ))

        return oc

    return MessageContainer(header='Warning', message='Page Empty')
